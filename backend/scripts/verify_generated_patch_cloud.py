"""Verify an already generated MC-01 patch through the existing public isolated gate."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from benchproof.coding.generation import CodingBrief, CodingPlan, EditProposal
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.patch import PatchProposal, apply_patch_to_file, compute_diff_hash, validate_patch
from benchproof.providers.structured import validate_completion
from scripts.check_coding_generation import _write_new

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_URL = "https://benchproof.vercel.app"


def validate_artifact(output: Path) -> tuple[CodingBrief, EditProposal, str]:
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    task = json.loads((output / "approved-task.json").read_text(encoding="utf-8"))
    response = json.loads((output / "provider-response.json").read_text(encoding="utf-8"))
    brief = CodingBrief.model_validate(task["brief"])
    plan = CodingPlan.model_validate(task["plan"])
    edits = validate_completion(response, EditProposal)
    diff = (output / "candidate.diff").read_text(encoding="utf-8")
    app = fixture_dir("MC-01") / "app"
    if (
        report["status"] != "GENERATED_POLICY_VALIDATED" or report["model_calls"] != 1
        or plan.identity() != task["plan_hash"] or plan.brief_hash != brief.identity()
        or report["source_hash"] != brief.source_hash or plan.source_hash != brief.source_hash
        or report["plan_hash"] != plan.identity() or edits.plan_hash != plan.identity()
        or edits.source_hash != brief.source_hash or source_hash_for_dir(app) != brief.source_hash
        or response["response_id"] != report["provider"]["response_id"]
        or brief.editable_paths != ["app/money.py"] or plan.target_files != ["app/money.py"]
        or len(edits.files) != 1 or edits.files[0].path != "app/money.py"
    ):
        raise ValueError("Artifact identities or approved scope do not match")
    original = (app / "money.py").read_text(encoding="utf-8")
    if apply_patch_to_file(original, diff) != edits.files[0].content.replace("\r\n", "\n"):
        raise ValueError("The patch is not the saved model's exact file edit")
    validate_patch(PatchProposal(
        patch_id="cloud-import", audit_id="", base_source_hash=brief.source_hash,
        target_files=["app/money.py"], diff=diff,
    ), brief.source_hash)
    return brief, edits, diff


def verify_cloud(output: Path, client: httpx.Client) -> dict[str, Any]:
    brief, edits, diff = validate_artifact(output)
    owner = f"coding-check-{uuid.uuid4().hex[:20]}"
    _write_new(output / "cloud-reservation.json", {
        "owner_capability": owner, "status": "IN_FLIGHT", "max_mutations": 4,
        "automatic_retries": 0, "additional_model_calls": 0,
    })
    evidence: dict[str, Any] = {
        "schema": "benchproof/generated-cloud-check-v1", "url": PUBLIC_URL,
        "status": "FAILED", "additional_model_calls": 0, "diff_hash": compute_diff_hash(diff),
        "source_hash": brief.source_hash, "scope": "CLI-generated patch imported into the existing audit API",
    }
    phase = "readiness"

    def request(path: str, body: dict[str, Any] | None = None) -> Any:
        if not path.startswith("/api/v1/") or any(name in path for name in ("diagnose", "recover")):
            raise ValueError("Only non-inference audit routes are allowed")
        response = client.request(
            "GET" if body is None else "POST", path,
            headers={"X-BenchProof-Owner": owner, "Idempotency-Key": owner},
            **({"json": body} if body is not None else {}),
        )
        response.raise_for_status()
        return response.json()

    try:
        ready = request("/api/v1/ready")
        if not ready["runner"]["isolated_execution_available"]:
            raise ValueError("The cloud isolated runner is unavailable")
        phase = "create"
        audit = request("/api/v1/audits", {
            "fixture_id": "MC-01", "mode": "live", "source_hash": brief.source_hash,
            "contract_hash": ready["contract_hash"],
        })
        evidence["audit_id"] = audit["audit_id"]
        prefix = f"/api/v1/audits/{audit['audit_id']}"
        phase = "baseline"
        baseline = request(f"{prefix}/verify", {"use_docker": True})
        evidence["baseline"] = baseline
        if baseline["verdict"] != "REJECTED" or "amount-boundary" not in baseline["failing_checks"]:
            raise ValueError("The cloud sample did not reproduce its baseline fault")
        phase = "import-generated-patch"
        patch = request(f"{prefix}/patch", {
            "diff": diff, "base_source_hash": brief.source_hash, "target_files": ["app/money.py"],
            "explanation": edits.explanation, "author": "nebius-coding-agent-v1",
        })
        evidence["patch_id"] = patch["patch_id"]
        if patch["diff_hash"] != evidence["diff_hash"] or patch["policy_result"] != "PENDING":
            raise ValueError("Imported patch differs from the saved model edit")
        phase = "candidate"
        candidate = request(f"{prefix}/verify", {"patch_id": patch["patch_id"], "use_docker": True})
        evidence["candidate"] = candidate
        if (
            candidate["verdict"] != "VERIFIED" or candidate["failing_checks"] or candidate["unknown_checks"]
            or candidate["patch_hash"] != evidence["diff_hash"]
            or not candidate["isolation"]["enforced"] or candidate["isolation"]["network"] != "none"
            or candidate["image_hash"] != baseline["image_hash"]
        ):
            raise ValueError("The generated patch did not pass the protected isolated checks")
        evidence["status"] = "PASSED"
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        evidence.update(failed_phase=phase, error_type=type(exc).__name__)
        if isinstance(exc, httpx.HTTPStatusError):
            evidence["http_status"] = exc.response.status_code
    finally:
        _write_new(output / "cloud-report.json", evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id):
        parser.error("run-id must be a plain portable token")
    output = REPO_ROOT / "artifacts" / "coding" / args.run_id
    with httpx.Client(base_url=PUBLIC_URL, timeout=240, follow_redirects=False, transport=httpx.HTTPTransport(retries=0)) as client:
        evidence = verify_cloud(output, client)
    print(json.dumps({key: evidence.get(key) for key in ("status", "failed_phase", "http_status", "audit_id", "patch_id")}))
    return 0 if evidence["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
