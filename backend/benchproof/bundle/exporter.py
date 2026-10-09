"""Evidence bundle exporter — canonical manifest, safe archive paths, secret/truth exclusion."""

from __future__ import annotations

import contextlib
import hashlib
import json
import platform
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from benchproof.constraints import list_constraints
from benchproof.domain import Artifact, BundleManifest
from benchproof.fixtures import (
    CANDIDATE_DIR,
    fixture_dir,
    load_manifest,
    source_manifest,
)
from benchproof.graph import build_state_graph
from benchproof.storage import (
    get_audit,
    get_graph_by_audit_id,
    list_actions,
    list_patches,
)
from benchproof.storage.lifecycle import (
    ImmutableRecordError,
    append_event,
    list_check_results,
    list_events,
    record_artifact,
)

# ── Security & Secret Exclusion ──────────────────────────────────────────

SECRET_PATTERNS = [
    re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.IGNORECASE),
]

SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


class SecurityExclusionError(Exception):
    """Raised when a secret or private truth leak is detected."""


class SafeArchivePathError(Exception):
    """Raised when an archive entry path is unsafe or invalid."""


def scan_for_secrets(content: str, filename: str) -> None:
    """Scan content and raise SecurityExclusionError if credentials are found."""
    for pattern in SECRET_PATTERNS:
        match = pattern.search(content)
        if match:
            raise SecurityExclusionError(
                f"Credential or secret pattern matched in {filename}: {match.group(0)[:8]}..."
            )


def assert_safe_archive_name(filename: str) -> None:
    """Ensure path is a simple relative name without traversal or slashes."""
    if not filename or not SAFE_FILENAME_PATTERN.match(filename):
        raise SafeArchivePathError(f"Unsafe archive filename: {filename}")
    if ".." in filename or filename.startswith(("/", "\\")):
        raise SafeArchivePathError(f"Traversal forbidden: {filename}")


# ── Exporter Implementation ──────────────────────────────────────────────

def export_bundle(
    audit_id: str,
    output_path: Path | None = None,
    db_path: Path | None = None,
    actor: str = "trusted-evaluator",
) -> tuple[Path, BundleManifest]:
    """Export complete canonical evidence bundle as a ZIP archive.

    Returns the path to the written zip file and the validated BundleManifest.
    """
    audit = get_audit(audit_id, db_path=db_path)
    if not audit:
        raise ValueError(f"Audit {audit_id} not found")

    fixture_id = audit["fixture_id"]
    fmanifest = load_manifest(fixture_id)

    # 1. constraints.json
    constraints_data = {
        "schema_version": "benchproof/v2",
        "fixture_id": fixture_id,
        "approved_constraints": [c.model_dump() for c in list_constraints()],
        "required_check_ids": sorted(
            cid for c in list_constraints() for cid in c.protected_check_ids
        ),
    }
    constraints_json = json.dumps(constraints_data, indent=2, sort_keys=True)

    # 2. state.json & coverage.json (Engineering-State Graph)
    graph_row = get_graph_by_audit_id(audit_id, db_path=db_path)
    if graph_row:
        state_data = graph_row.get("graph", {})
        coverage_data = graph_row.get("coverage", {})
    else:
        app_dir = fixture_dir(fixture_id) / CANDIDATE_DIR
        graph_snap = build_state_graph(app_dir, audit["contract_hash"])
        state_data = graph_snap.model_dump()
        coverage_data = graph_snap.coverage

    state_json = json.dumps(state_data, indent=2, sort_keys=True)
    coverage_json = json.dumps(coverage_data, indent=2, sort_keys=True)

    # 3. decisions.json (P1 decision ledger placeholder)
    decisions_data = {
        "schema_version": "benchproof/v2",
        "status": "NOT_RUN",
        "omission_note": "P1 decision ledger scheduled for Day 10 (Ticket B-14)",
        "decisions": [],
    }
    decisions_json = json.dumps(decisions_data, indent=2, sort_keys=True)

    # 4. trajectory.jsonl (Actions and events in chronological sequence)
    actions = list_actions(audit_id, db_path=db_path)
    events = list_events(audit_id, db_path=db_path)
    trajectory_lines: list[str] = []
    for evt in events:
        trajectory_lines.append(json.dumps({"type": "event", **evt}, sort_keys=True))
    for act in actions:
        trajectory_lines.append(json.dumps({"type": "action", **act}, sort_keys=True))
    trajectory_content = "\n".join(trajectory_lines) + ("\n" if trajectory_lines else "")

    # 5. candidate.diff (Accepted or latest proposed repair diff)
    patches = list_patches(audit_id, db_path=db_path)
    diff_text = ""
    if patches:
        approved_patches = [p for p in patches if p.get("policy_result") == "APPROVED"]
        diff_text = (approved_patches[-1] if approved_patches else patches[-1]).get("diff_text", "")

    # 6. source-manifest.json (Pristine base source files and hashes)
    app_dir = fixture_dir(fixture_id) / CANDIDATE_DIR
    base_files = source_manifest(app_dir)
    source_manifest_data = {
        "schema_version": "benchproof/v2",
        "fixture_id": fixture_id,
        "base_source_hash": audit["source_hash"],
        "files": base_files,
    }
    source_manifest_json = json.dumps(source_manifest_data, indent=2, sort_keys=True)

    # 7. checks.json (Actual evaluator check results)
    check_results = list_check_results(audit_id, db_path=db_path)
    checks_data = {
        "schema_version": "benchproof/v2",
        "audit_id": audit_id,
        "fixture_id": fixture_id,
        "gate_verdict": audit["gate_verdict"],
        "total_checks": len(check_results),
        "passing_checks": sum(1 for c in check_results if c.get("outcome") == "PASS"),
        "failing_checks": sum(1 for c in check_results if c.get("outcome") == "FAIL"),
        "unknown_checks": sum(1 for c in check_results if c.get("outcome") == "UNKNOWN"),
        "checks": check_results,
    }
    checks_json = json.dumps(checks_data, indent=2, sort_keys=True)

    # 8. mutations.json (P1 mutation suite placeholder)
    mutations_data = {
        "schema_version": "benchproof/v2",
        "status": "NOT_RUN",
        "omission_note": "P1 mutation suite scheduled for Day 12 (Ticket B-16)",
        "mutants": [],
    }
    mutations_json = json.dumps(mutations_data, indent=2, sort_keys=True)

    # 9. environment.json (Image/runner/model metadata)
    env_data = {
        "schema_version": "benchproof/v2",
        "runner_mode": audit.get("mode", "live"),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "model_id": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        "evaluator_version": "benchproof/v2",
        "created_at": audit["created_at"],
    }
    environment_json = json.dumps(env_data, indent=2, sort_keys=True)

    # 10. usage.json (Action counts, limits, timing)
    usage_data = {
        "schema_version": "benchproof/v2",
        "audit_id": audit_id,
        "actions_count": len(actions),
        "patches_count": len(patches),
        "limits": json.loads(audit.get("limits_json", "{}")),
    }
    usage_json = json.dumps(usage_data, indent=2, sort_keys=True)

    # 11. report.md (Human-readable markdown summary)
    checks_table_rows = "\n".join(
        f"| `{c.get('check_id')}` | **{c.get('outcome')}** | `{c.get('oracle_kind')}` | {c.get('reason')} | {c.get('duration_ms')} ms |"
        for c in check_results
    )
    report_md = f"""# BenchProof Evidence Report

- **Audit ID:** `{audit_id}`
- **Fixture:** `{fixture_id}` (`{fmanifest.get('family', 'unknown')}`)
- **Run State:** `{audit['run_state']}`
- **Gate Verdict:** **`{audit['gate_verdict']}`**
- **Created At:** `{audit['created_at']}`
- **Mode:** `{audit['mode']}`

## Evaluated Checks

| Check ID | Outcome | Oracle Kind | Reason | Duration |
| --- | --- | --- | --- | --- |
{checks_table_rows if check_results else "| *None* | - | - | No checks recorded | - |"}

## Candidate Patch Summary

```diff
{diff_text.strip() if diff_text.strip() else "# No diff applied (clean untouched run)"}
```

## Assurance Guarantee
This evidence bundle was produced by the BenchProof v2 Agentic Engineering Assurance Runtime.
Check outcomes are computed solely by the external, independent evaluator oracle.
Candidate outputs and self-asserted verdicts are strictly non-authoritative.
"""

    # 12. REPLAY.md (Independent isolated replay instructions)
    replay_md = f"""# BenchProof Independent Replay Guide

This evidence bundle allows any reviewer or judge to independently verify and replay audit `{audit_id}` without trust in previously generated outputs.

## Step 1: Non-Executing Hash Verification
Verify all artifact hashes and schema integrity without executing any candidate code:

```bash
python scripts/replay_bundle.py --bundle benchproof-audit-{audit_id}.zip --verify-only
```

This verifies that every bundled artifact matches the canonical SHA-256 in `manifest.json`.

## Step 2: Fresh Isolated Replay
Re-execute the candidate verification in a fresh isolated temporary environment using the independent evaluator oracle:

```bash
python scripts/replay_bundle.py --bundle benchproof-audit-{audit_id}.zip
```

### What Happens During Replay:
1. Manifest integrity is validated.
2. Candidate source files are extracted and verified against base source hashes.
3. The recorded `candidate.diff` is applied to the isolated candidate snapshot.
4. The trusted evaluator executes the candidate in isolation.
5. All checks are recomputed from scratch using the deterministic oracle.
6. The replayed gate verdict is asserted against the original recorded verdict (`{audit['gate_verdict']}`).

## Security & Privacy Notes
- No private API keys or credentials are included in this bundle.
- Tampering with any file in this bundle will cause verification to fail immediately.
"""

    # Assemble file map
    files_to_bundle: dict[str, str] = {
        "constraints.json": constraints_json,
        "state.json": state_json,
        "coverage.json": coverage_json,
        "decisions.json": decisions_json,
        "trajectory.jsonl": trajectory_content,
        "candidate.diff": diff_text,
        "source-manifest.json": source_manifest_json,
        "checks.json": checks_json,
        "mutations.json": mutations_json,
        "environment.json": environment_json,
        "usage.json": usage_json,
        "report.md": report_md,
        "REPLAY.md": replay_md,
    }

    # Security check: scan all contents for secrets and validate names
    for name, content in files_to_bundle.items():
        assert_safe_archive_name(name)
        scan_for_secrets(content, name)

    # Compute SHA-256 for all bundle contents
    artifact_hashes: dict[str, str] = {}
    for name, content in sorted(files_to_bundle.items()):
        raw_bytes = content.encode("utf-8")
        artifact_hashes[name] = hashlib.sha256(raw_bytes).hexdigest()

    # 13. manifest.json
    manifest = BundleManifest(
        schema_version="benchproof/v2",
        audit_id=audit_id,
        fixture_id=fixture_id,
        run_state=audit["run_state"],
        gate_verdict=audit["gate_verdict"],
        created_at=audit["created_at"],
        exported_at=datetime.now(UTC).isoformat(),
        omissions=["P1-decisions", "P1-mutations"],
        artifact_hashes=artifact_hashes,
    )
    manifest.compute_hash()
    manifest_json = manifest.model_dump_json(indent=2)
    scan_for_secrets(manifest_json, "manifest.json")

    # Determine destination ZIP path
    if output_path is None:
        bundles_dir = Path("artifacts") / "bundles"
        bundles_dir.mkdir(parents=True, exist_ok=True)
        output_path = bundles_dir / f"benchproof-audit-{audit_id}.zip"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write ZIP archive atomically via temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Write manifest first
            zf.writestr("manifest.json", manifest_json)
            # Write all other files
            for name, content in sorted(files_to_bundle.items()):
                zf.writestr(name, content.encode("utf-8"))

        # Compute ZIP file sha256 & byte size
        zip_bytes = tmp_path.read_bytes()
        zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
        zip_size = len(zip_bytes)

        # Move to target
        if output_path.exists():
            output_path.unlink()
        shutil.move(str(tmp_path), str(output_path))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # Record artifact in database (immutable; one record per distinct bundle content)
    art = Artifact(
        artifact_id=f"art-bundle-{audit_id}-{zip_sha256[:12]}",
        owner=audit.get("owner_ref", "owner"),
        audit_id=audit_id,
        relative_name=output_path.name,
        mime_type="application/zip",
        byte_size=zip_size,
        sha256=zip_sha256,
        visibility="public",
    )
    with contextlib.suppress(ImmutableRecordError):
        # Identical bundle bytes were already recorded; the existing record stands.
        record_artifact(art, db_path=db_path)

    # Emit bundle_ready event
    append_event(
        audit_id,
        "bundle_ready",
        {
            "bundle_name": output_path.name,
            "sha256": zip_sha256,
            "manifest_hash": manifest.manifest_hash,
            "total_files": len(artifact_hashes) + 1,
        },
        db_path=db_path,
    )

    return output_path, manifest
