"""Fresh independent acceptance gate (B-10).

Executes approved candidate fresh in isolated runner:
- Trusted evaluator computes expected behavior externally
- Evaluator-only verdict writes (candidate cannot write verdicts or forge PASS)
- Requires ALL approved contract checks to pass
- Rejects shallow/inadequate candidates that fail boundary or caller constraints
- Detects missing required checks and enforces budget limits
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from benchproof.constraints import contract_hash
from benchproof.domain import CheckOutcome, GateVerdict, PatchPolicyResult, RunState
from benchproof.evaluator import run_gate
from benchproof.evaluator.harness import (
    assert_no_trusted_assets,
    collect_observations_in_process,
    evaluator_hash,
    required_check_ids,
)
from benchproof.evaluator.observations import evaluate_observations
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.patch import (
    PatchProposal,
    apply_patch_to_dir,
    validate_patch,
)
from benchproof.storage import get_audit, get_patch, list_patches, save_patch
from benchproof.storage.lifecycle import TRUSTED_EVALUATOR, append_event, record_check_result


class GateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def verify_candidate_app(
    candidate_app_dir: Path,
    patch_hash: str | None = None,
    use_docker: bool = False,
) -> dict[str, Any]:
    """Execute candidate app fresh and evaluate with trusted external oracle."""
    candidate_app_dir = Path(candidate_app_dir)
    assert_no_trusted_assets(candidate_app_dir)

    src_hash = source_hash_for_dir(candidate_app_dir)
    chash = contract_hash()
    ehash = evaluator_hash()
    image_hash = "local-in-process"

    # 1. Collect Observations in isolated runner
    obs: dict[str, Any]
    if use_docker:
        runner = DockerRunner()
        avail, _ = runner.available()
        if avail:
            res = runner.run_candidate(candidate_app_dir, timeout_s=30)
            obs = res.observations or {"error": res.logs, "route": {}, "worker": {}}
            image_hash = res.image_digest
        else:
            obs = collect_observations_in_process(candidate_app_dir)
    else:
        obs = collect_observations_in_process(candidate_app_dir)

    # 2. Trusted external evaluation (computed outside candidate)
    worker_file = candidate_app_dir / "worker.py"
    worker_src = worker_file.read_text(encoding="utf-8") if worker_file.exists() else None
    check_results = evaluate_observations(obs, worker_src)

    # Stamp check results with verified hashes
    for cr in check_results:
        cr.source_hash = src_hash
        cr.contract_hash = chash
        cr.evaluator_hash = ehash
        cr.image_hash = image_hash
        cr.patch_hash = patch_hash

    # 3. Deterministic Gate Computation
    req_ids = required_check_ids()
    gate_verdict = run_gate(check_results, req_ids)

    passing = sorted(cr.check_id for cr in check_results if cr.outcome == CheckOutcome.PASS_)
    failing = sorted(cr.check_id for cr in check_results if cr.outcome == CheckOutcome.FAIL)
    unknown = sorted(cr.check_id for cr in check_results if cr.outcome == CheckOutcome.UNKNOWN)

    # 4. Check for attempted forgery in candidate logs/observations
    forged_pass_prevented = False
    raw_error_or_output = str(obs.get("error", "")) + str(obs.get("route", ""))
    if ("VERIFIED" in raw_error_or_output or "PASS" in raw_error_or_output) and gate_verdict != "VERIFIED":
        forged_pass_prevented = True

    return {
        "candidate_source_hash": src_hash,
        "contract_hash": chash,
        "evaluator_hash": ehash,
        "image_hash": image_hash,
        "patch_hash": patch_hash or "",
        "verdict": gate_verdict,
        "required_check_ids": sorted(req_ids),
        "passing_checks": passing,
        "failing_checks": failing,
        "unknown_checks": unknown,
        "checks": [cr.model_dump() for cr in check_results],
        "forged_pass_prevented": forged_pass_prevented,
    }


def execute_acceptance_gate(
    audit_id: str,
    patch_id: str | None = None,
    use_docker: bool = False,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Execute complete acceptance gate for an audit and record lifecycle outcomes."""
    audit = get_audit(audit_id, db_path=db_path)
    if not audit:
        raise GateError("AUDIT_NOT_FOUND", f"Audit {audit_id} not found in database")

    fixture_id = audit["fixture_id"]
    fdir = fixture_dir(fixture_id)
    base_app_dir = fdir / "app"
    current_shash = source_hash_for_dir(base_app_dir)

    # Check budget limits
    existing_patches = list_patches(audit_id, db_path=db_path)
    import json
    limits_raw = audit.get("limits_json", "{}")
    limits = json.loads(limits_raw) if isinstance(limits_raw, str) else (audit.get("limits") or {})
    max_patches = limits.get("max_patches", 5)
    if len(existing_patches) > max_patches:
        raise GateError(
            "BUDGET_EXHAUSTED",
            f"Exceeded maximum allowed repair patches ({max_patches}) for audit {audit_id}",
        )

    patch_dict = None
    patch_hash = None

    with tempfile.TemporaryDirectory(prefix="bp-gate-candidate-") as tmp:
        candidate_dir = Path(tmp) / "app"
        
        if patch_id:
            patch_dict = get_patch(patch_id, db_path=db_path)
            if not patch_dict:
                raise GateError("PATCH_NOT_FOUND", f"Patch {patch_id} not found")

            # Validate patch proposal
            proposal = PatchProposal(
                patch_id=patch_id,
                audit_id=audit_id,
                base_source_hash=patch_dict["base_hash"],
                target_files=patch_dict["approved_paths"],
                diff=patch_dict["diff_text"],
                author=patch_dict.get("author", "nemotron-repair"),
            )
            validate_patch(proposal, current_shash)
            
            # Apply patch cleanly into temporary candidate directory
            apply_patch_to_dir(base_app_dir, proposal, candidate_dir)
            patch_hash = patch_dict.get("diff_hash") or ""
        else:
            # Clean control or unpatched candidate
            import shutil
            shutil.copytree(base_app_dir, candidate_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


        # Execute candidate verification
        result = verify_candidate_app(candidate_dir, patch_hash=patch_hash, use_docker=use_docker)

    # Record check results in database
    for cr_data in result["checks"]:
        from benchproof.domain import CheckResult
        cr = CheckResult.model_validate(cr_data)
        record_check_result(
            audit_id=audit_id,
            result=cr,
            author=TRUSTED_EVALUATOR,
            db_path=db_path,
        )


    # Determine verdict and update audit state
    verdict = result["verdict"]
    is_verified = (verdict == "VERIFIED")

    append_event(
        audit_id=audit_id,
        event_type="candidate_verified" if is_verified else "candidate_rejected",
        payload={
            "verdict": verdict,
            "patch_id": patch_id,
            "candidate_source_hash": result["candidate_source_hash"],
            "failing_checks": result["failing_checks"],
            "passing_checks": result["passing_checks"],
        },
        db_path=db_path,
    )

    # Update patch policy result if patch was evaluated
    if patch_id and patch_dict:
        policy_res = PatchPolicyResult.APPROVED.value if is_verified else PatchPolicyResult.REJECTED.value
        save_patch(
            patch_id=patch_id,
            audit_id=audit_id,
            base_hash=patch_dict["base_hash"],
            diff_hash=patch_dict["diff_hash"],
            diff_text=patch_dict["diff_text"],
            approved_paths=patch_dict["approved_paths"],
            changed_lines=patch_dict["changed_lines"],
            policy_result=policy_res,
            author=patch_dict.get("author", "nemotron-repair"),
            provider_meta=patch_dict.get("provider_meta"),
            db_path=db_path,
        )

    # Update audit record
    from benchproof.storage import update_audit_state
    new_state = RunState.COMPLETED if is_verified else RunState.INVESTIGATING
    update_audit_state(audit_id, new_state, GateVerdict(verdict), db_path=db_path)

    return result
