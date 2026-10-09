"""Independent bundle replay engine — executes fresh isolated verification and checks against manifest."""

from __future__ import annotations

import json
import platform
import shutil
import sys
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchproof.bundle.validator import validate_bundle_nonexecuting
from benchproof.domain import ReplayRecord
from benchproof.fixtures import CANDIDATE_DIR, fixture_dir
from benchproof.gate import verify_candidate_app
from benchproof.patch import PatchProposal, apply_patch_to_dir


def replay_bundle(
    bundle_zip_path: Path,
    work_dir: Path | None = None,
) -> ReplayRecord:
    """Perform independent isolated replay of an exported evidence bundle.

    1. Non-executing cryptographic validation.
    2. Fresh candidate snapshot setup.
    3. Patch application in isolation.
    4. Deterministic evaluator oracle execution.
    5. Comparison of replayed check outcomes with recorded bundle outcomes.
    """
    # Step 1: Non-executing validation
    val = validate_bundle_nonexecuting(bundle_zip_path)
    if not val["valid"]:
        return ReplayRecord(
            replay_id=f"rep-{uuid.uuid4().hex[:12]}",
            original_audit_id=val.get("audit_id", "unknown"),
            bundle_sha256="",
            replayed_verdict="BLOCKED",
            original_verdict=val.get("gate_verdict", "UNKNOWN"),
            verdict_matches=False,
            checks_matched=False,
            tampered=True,
            tamper_details=val["discrepancies"],
            environment={
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
            },
        )

    # Step 2: Read contents from ZIP
    with zipfile.ZipFile(bundle_zip_path, "r") as zf:
        manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
        candidate_diff = zf.read("candidate.diff").decode("utf-8")
        checks_data = json.loads(zf.read("checks.json").decode("utf-8"))

    audit_id = manifest_data["audit_id"]
    fixture_id = manifest_data["fixture_id"]
    original_verdict = manifest_data["gate_verdict"]

    import hashlib
    bundle_sha256 = hashlib.sha256(bundle_zip_path.read_bytes()).hexdigest()

    # Step 3: Fresh temporary isolated workspace
    base_fixture = fixture_dir(fixture_id) / CANDIDATE_DIR
    if not base_fixture.exists():
        raise FileNotFoundError(f"Base fixture directory not found for {fixture_id}: {base_fixture}")

    temp_dir_ctx = (
        tempfile.TemporaryDirectory(prefix=f"bp-replay-{fixture_id}-")
        if work_dir is None
        else None
    )
    isolated_dir = Path(temp_dir_ctx.name) if temp_dir_ctx else work_dir / f"bp-replay-{uuid.uuid4().hex[:8]}"
    isolated_dir.mkdir(parents=True, exist_ok=True)

    try:
        candidate_app = isolated_dir / "app"
        # Step 4: Apply candidate diff if present
        if candidate_diff.strip():
            proposal = PatchProposal(
                patch_id=f"rep-patch-{audit_id}",
                audit_id=audit_id,
                base_source_hash=manifest_data.get("base_source_hash", ""),
                diff=candidate_diff,
            )
            apply_patch_to_dir(base_fixture, proposal, candidate_app)
        else:
            shutil.copytree(base_fixture, candidate_app)

        # Step 5 & 6 & 7: Fresh isolated candidate execution & external evaluator
        verif = verify_candidate_app(candidate_app)
        replayed_verdict = verif["verdict"]
        replayed_checks_data = verif["checks"]

        # Step 8: Compare replayed results with bundle recorded results
        original_checks_map = {
            c["check_id"]: c.get("outcome") for c in checks_data.get("checks", [])
        }
        replayed_checks_map = {
            c["check_id"]: c.get("outcome") for c in replayed_checks_data
        }

        check_comparisons: list[dict[str, Any]] = []
        all_checks_matched = True

        for cid in sorted(set(original_checks_map.keys()) | set(replayed_checks_map.keys())):
            orig_raw = original_checks_map.get(cid, "MISSING")
            orig_out = orig_raw.value if hasattr(orig_raw, "value") else str(orig_raw)

            repl_raw = replayed_checks_map.get(cid, "MISSING")
            repl_out = repl_raw.value if hasattr(repl_raw, "value") else str(repl_raw)

            matched = (orig_out == repl_out)
            if not matched:
                all_checks_matched = False
            check_comparisons.append({
                "check_id": cid,
                "original_outcome": orig_out,
                "replayed_outcome": repl_out,
                "match": matched,
            })

        verdict_str = replayed_verdict.value if hasattr(replayed_verdict, "value") else str(replayed_verdict)
        verdict_matches = (verdict_str == original_verdict)

        return ReplayRecord(
            replay_id=f"rep-{uuid.uuid4().hex[:12]}",
            original_audit_id=audit_id,
            bundle_sha256=bundle_sha256,
            replayed_verdict=verdict_str,
            original_verdict=original_verdict,
            verdict_matches=verdict_matches,
            checks_matched=all_checks_matched,
            check_comparisons=check_comparisons,
            tampered=False,
            tamper_details=[],
            environment={
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
                "runner": "local_isolated_runner",
            },
            created_at=datetime.now(UTC).isoformat(),
        )

    finally:
        if temp_dir_ctx:
            temp_dir_ctx.cleanup()
        elif work_dir:
            shutil.rmtree(isolated_dir, ignore_errors=True)
