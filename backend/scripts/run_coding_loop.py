"""CLI demonstration and verification tool for the C-03 coding-task loop.

Demonstrates the complete vertical slice:
Task Intake -> Model Planning -> Plan Approval -> Baseline Execution ->
Model Edit -> Candidate Test -> Final Verification -> Diff Export.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from benchproof.coding.contracts import OperatorLimits
from benchproof.coding.engine import CodingEngine, InvoiceExecutor
from benchproof.coding.generation import CodingBrief, CodingPlan
from benchproof.coding.store import CodingStore
from benchproof.coding.worker import CodingWorker
from benchproof.constraints import contract_hash
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import candidate_files, fixture_dir, source_hash_for_dir
from benchproof.providers import NebiusAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]


class SyntheticCodingClient:
    """Offline synthetic client for deterministic, zero-spend verification."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        payload = json.loads(kwargs["user_prompt"])
        if "brief" in payload:
            result = {
                "source_hash": payload["source_hash"],
                "brief_hash": payload["brief_hash"],
                "steps": [
                    "Inspect compute_total in app/money.py",
                    "Accumulate exact Decimal values without premature line rounding",
                    "Quantize only the final sum to two decimal places",
                ],
                "target_files": payload["brief"]["editable_paths"],
                "check_profile": "invoice-observation-v1",
            }
        else:
            fixed_content = (
                "from decimal import Decimal, ROUND_HALF_UP\n"
                "from typing import List\n\n"
                "def compute_total(lines: List[str]) -> str:\n"
                "    \"\"\"Repaired: accurate total rounding.\"\"\"\n"
                "    if not lines:\n"
                "        return \"0.00\"\n\n"
                "    total = Decimal(\"0\")\n"
                "    for line in lines:\n"
                "        total += Decimal(line)\n\n"
                "    return str(total.quantize(Decimal(\"0.01\"), rounding=ROUND_HALF_UP))\n"
            )
            result = {
                "source_hash": payload["source_hash"],
                "plan_hash": payload["plan_hash"],
                "files": [{"path": "app/money.py", "content": fixed_content}],
                "explanation": "C-03 verification patch: exact Decimal summation with single final total rounding",
            }
        return {
            "content": json.dumps(result),
            "finish_reason": "stop",
            "response_id": f"synthetic-run-{len(self.calls)}",
            "response_model": "synthetic/c03-runner",
            "usage": {"prompt_tokens": 150, "completion_tokens": 85, "total_tokens": 235},
        }


class SyntheticCheckExecutor:
    """Offline executor producing realistic baseline failure and candidate pass."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(
        self,
        app_dir: Path,
        *,
        operation_id: str,
        timeout_s: int,
        should_cancel: Any = None,
    ) -> dict[str, Any]:
        assert not should_cancel or not should_cancel()
        shash = source_hash_for_dir(app_dir)
        is_baseline = len(self.calls) == 0
        self.calls.append({"operation_id": operation_id, "source_hash": shash, "timeout_s": timeout_s})
        verdict = "REJECTED" if is_baseline else "VERIFIED"
        passed = verdict == "VERIFIED"
        return {
            "profile": "invoice-observation-v1",
            "source_hash": shash,
            "contract_hash": contract_hash(),
            "evaluator_hash": "eval-synthetic-c03",
            "required_check_ids": ["amount-boundary"],
            "verdict": verdict,
            "checks": [
                {
                    "check_id": "amount-boundary",
                    "outcome": "PASS" if passed else "FAIL",
                    "reason": "Decimal quantization matches contract" if passed else "Fault: premature line rounding defect",
                }
            ],
            "execution": {
                "runner": "synthetic-isolated-runner",
                "exit_code": 0,
                "timed_out": False,
                "error": None,
                "isolation": {"enforced": True},
            },
        }

    def cancel(self, operation_id: str) -> bool:
        return True


def execute_c03_loop(
    output_dir: Path,
    *,
    live: bool = False,
    model_id: str = "synthetic/c03-runner",
) -> dict[str, Any]:
    app_dir = fixture_dir("MC-01") / "app"
    files = {
        path.relative_to(app_dir.parent).as_posix(): path.read_bytes().decode("utf-8")
        for path in candidate_files(app_dir)
    }
    base_hash = source_hash_for_dir(app_dir)
    brief = CodingBrief(
        task="Repair invoice rounding in app/money.py so Decimal lines are accumulated before final rounding",
        source_hash=base_hash,
        editable_paths=["app/money.py"],
    )

    db_path = output_dir / "coding_task.db"
    store = CodingStore(db_path, OperatorLimits(model_calls_per_day=20, executions_per_day=20))

    if live:
        load_dotenv(REPO_ROOT / ".env")
        nebius_key = os.getenv("NEBIUS_API_KEY", "")
        if not nebius_key or nebius_key in {"your_api_key_here", ""}:
            raise RuntimeError("NEBIUS_API_KEY required for live execution")
        client: Any = NebiusAdapter(api_key=nebius_key, timeout_s=45)
        runner = DockerRunner()
        ready, detail = runner.available()
        if not ready:
            raise RuntimeError(f"Docker runner unavailable for live execution: {detail}")
        executor: Any = InvoiceExecutor(runner)
        synthetic_flag = False
    else:
        client = SyntheticCodingClient()
        executor = SyntheticCheckExecutor()
        synthetic_flag = True

    engine = CodingEngine(
        client=client,
        model_id=model_id,
        executor=executor,
        synthetic=synthetic_flag,
    )
    worker = CodingWorker(store, engine, worker_id="c03-cli-worker", live_enabled=live)

    # 1. Create Task
    task = store.create_task(
        "operator",
        "MC-01",
        brief,
        files,
        contract_hash(),
        "c03-cli-create",
        runtime_config={"model_id": model_id, "max_output_tokens": 2048, "engine_version": "coding-engine-v1"},
    )
    task_id = task["task_id"]

    # 2. Plan step
    store.enqueue("operator", task_id, "c03-plan", phase="plan")
    res_plan = worker.run_once()
    assert res_plan is not None and res_plan["state"] == "AWAITING_APPROVAL"

    task = store.get_task("operator", task_id)
    plan_obj = CodingPlan.model_validate(task["plan"])
    plan_hash = plan_obj.identity()

    # 3. Approve plan and start
    store.approve_plan("operator", task_id, plan_hash)
    store.enqueue("operator", task_id, "c03-run", phase="run")

    # 4. Drain worker through Baseline -> Edit -> Candidate -> Final
    stages_seen: list[str] = []
    for _ in range(8):
        step_res = worker.run_once()
        if step_res is None:
            break
        stage = step_res.get("stage") or step_res.get("state")
        if stage:
            stages_seen.append(stage)
        if step_res.get("state") in {"REVIEW_READY", "BLOCKED", "STALLED"}:
            break

    final_task = store.get_task("operator", task_id)
    events = store.list_events("operator", task_id)

    # Save artifact pack
    (output_dir / "task.json").write_text(json.dumps(final_task, indent=2), encoding="utf-8")
    (output_dir / "plan.json").write_text(json.dumps(plan_obj.model_dump(), indent=2), encoding="utf-8")
    diff = (final_task.get("result") or {}).get("diff", "")
    (output_dir / "candidate.diff").write_text(diff, encoding="utf-8")
    (output_dir / "events.json").write_text(json.dumps(events, indent=2), encoding="utf-8")

    report = {
        "schema_version": "benchproof/c03-loop-verification-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "task_id": task_id,
        "mode": "live" if live else "synthetic",
        "state": final_task["state"],
        "stages_traversed": stages_seen,
        "plan_hash": plan_hash,
        "candidate_hash": (final_task.get("checkpoint") or {}).get("candidate_hash"),
        "counters": final_task["counters"],
        "has_diff": bool(diff.strip()),
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Unique identifier for this verification run")
    parser.add_argument("--live", action="store_true", help="Run with active Nebius model and Docker runner")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id):
        parser.error("run-id must be alphanumeric with hyphens/underscores")

    output_dir = REPO_ROOT / "artifacts" / "coding" / args.run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    try:
        report = execute_c03_loop(output_dir, live=args.live)
        print(json.dumps(report, indent=2))
        return 0 if report["state"] == "REVIEW_READY" else 1
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        err = {"status": "FAILED", "error": str(exc), "type": type(exc).__name__}
        print(json.dumps(err, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
