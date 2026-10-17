"""End-to-end task loop and revision verification (C-03).

Exercises the complete vertical slice:
Task -> Model plan -> Plan approval -> Baseline execution -> Model edit ->
Candidate execution -> Revision with real failure feedback -> Fresh final verification ->
Reviewable diff and execution log.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from benchproof.api import main as api_main
from benchproof.coding.contracts import OperatorLimits
from benchproof.coding.engine import CodingEngine
from benchproof.coding.generation import CodingBrief, CodingPlan
from benchproof.coding.store import CodingStore
from benchproof.coding.worker import CodingWorker
from benchproof.constraints import contract_hash
from benchproof.fixtures import candidate_files, fixture_dir, source_hash_for_dir


class MultiTurnSyntheticProvider:
    """Simulates multi-turn model interactions for planning and successive edits."""

    def __init__(self, *, plan_steps: list[str] | None = None, edits: list[str] | None = None):
        self.plan_steps = plan_steps or ["Analyze rounding in app/money.py", "Apply exact Decimal quantization"]
        self.edits = edits or ["first-attempt", "second-attempt"]
        self.edit_idx = 0
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        payload = json.loads(kwargs["user_prompt"])
        if "brief" in payload:
            result = {
                "source_hash": payload["source_hash"],
                "brief_hash": payload["brief_hash"],
                "steps": self.plan_steps,
                "target_files": payload["brief"]["editable_paths"],
                "check_profile": "invoice-observation-v1",
            }
        else:
            marker = self.edits[self.edit_idx] if self.edit_idx < len(self.edits) else "fallback"
            self.edit_idx += 1
            content = payload["source"]["app/money.py"].replace(
                "Faulty: premature rounding of each line.",
                f"Candidate edit ({marker}).",
            )
            result = {
                "source_hash": payload["source_hash"],
                "plan_hash": payload["plan_hash"],
                "files": [{"path": "app/money.py", "content": content}],
                "explanation": f"Generated edit for attempt {self.edit_idx}: {marker}",
            }
        return {
            "content": json.dumps(result),
            "finish_reason": "stop",
            "response_id": f"resp-{len(self.calls)}",
            "response_model": "synthetic/c03-tester",
            "usage": {"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180},
        }


class MultiTurnSyntheticExecutor:
    """Simulates isolated test container executions across baseline and candidates."""

    def __init__(self, outcomes: list[str]):
        self.outcomes = list(outcomes)
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
        call_idx = len(self.calls)
        self.calls.append({"operation_id": operation_id, "source_hash": shash, "timeout_s": timeout_s})
        verdict = self.outcomes[call_idx] if call_idx < len(self.outcomes) else "VERIFIED"
        passed = verdict == "VERIFIED"
        return {
            "profile": "invoice-observation-v1",
            "source_hash": shash,
            "contract_hash": contract_hash(),
            "evaluator_hash": "eval-hash-synthetic",
            "required_check_ids": ["amount-boundary"],
            "verdict": verdict,
            "checks": [
                {
                    "check_id": "amount-boundary",
                    "outcome": "PASS" if passed else "FAIL",
                    "reason": "Quantization matches specification" if passed else f"Boundary rounding defect in call {call_idx + 1}",
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


def _setup_task(tmp_path: Path, *, provider: Any, executor: Any) -> tuple[CodingStore, CodingWorker, str]:
    store = CodingStore(
        tmp_path / "coding_c03.db",
        OperatorLimits(model_calls_per_day=50, executions_per_day=50),
    )
    app_dir = fixture_dir("MC-01") / "app"
    files = {
        path.relative_to(app_dir.parent).as_posix(): path.read_bytes().decode("utf-8")
        for path in candidate_files(app_dir)
    }
    brief = CodingBrief(
        task="Repair invoice line rounding so only the total is rounded to two decimal places",
        source_hash=source_hash_for_dir(app_dir),
        editable_paths=["app/money.py"],
    )
    task = store.create_task("c03-tester", "MC-01", brief, files, contract_hash(), "task-create")
    engine = CodingEngine(
        client=provider,
        model_id="synthetic/c03-tester",
        executor=executor,
        synthetic=True,
    )
    worker = CodingWorker(store, engine, worker_id="c03-worker")
    return store, worker, task["task_id"]


def test_c03_direct_first_attempt_pass(tmp_path: Path) -> None:
    """Baseline fails -> Attempt 1 passes -> Fresh final check passes -> REVIEW_READY."""
    provider = MultiTurnSyntheticProvider(edits=["pass-first-try"])
    # 1. Baseline: REJECTED, 2. Candidate: VERIFIED, 3. Final: VERIFIED
    executor = MultiTurnSyntheticExecutor(["REJECTED", "VERIFIED", "VERIFIED"])
    store, worker, task_id = _setup_task(tmp_path, provider=provider, executor=executor)

    # Step 1: Enqueue planning
    store.enqueue("c03-tester", task_id, "plan-step", phase="plan")
    res1 = worker.run_once()
    assert res1 is not None and res1["state"] == "AWAITING_APPROVAL"

    task = store.get_task("c03-tester", task_id)
    plan_hash = CodingPlan.model_validate(task["plan"]).identity()

    # Step 2: Approve plan and enqueue execution
    store.approve_plan("c03-tester", task_id, plan_hash)
    store.enqueue("c03-tester", task_id, "start-step", phase="run")

    # Step 3: Run baseline check (fails as expected)
    res_base = worker.run_once()
    assert res_base is not None and res_base["stage"] == "EDIT"
    assert len(executor.calls) == 1

    # Step 4: Generate candidate patch
    res_edit = worker.run_once()
    assert res_edit is not None and res_edit["stage"] == "CANDIDATE"
    assert len(provider.calls) == 2  # 1 plan + 1 edit

    # Step 5: Test candidate (passes) -> transitions to FINAL
    res_cand = worker.run_once()
    assert res_cand is not None and res_cand["stage"] == "FINAL"
    assert len(executor.calls) == 2

    # Step 6: Fresh final verification
    res_final = worker.run_once()
    assert res_final is not None and res_final["state"] == "REVIEW_READY"
    assert len(executor.calls) == 3

    # Verify task result
    final_task = store.get_task("c03-tester", task_id)
    assert final_task["state"] == "REVIEW_READY"
    assert "Candidate edit (pass-first-try)" in final_task["result"]["diff"]
    assert final_task["counters"]["model_calls"] == 2
    assert final_task["counters"]["patch_attempts"] == 1
    assert final_task["counters"]["executions"] == 3


def test_c03_multiturn_revision_loop_feeds_real_observations(tmp_path: Path) -> None:
    """Baseline fails -> Attempt 1 fails -> Observations feed into Attempt 2 -> Passes -> REVIEW_READY."""
    provider = MultiTurnSyntheticProvider(edits=["flawed-attempt-1", "repaired-attempt-2"])
    # 1. Baseline: REJECTED, 2. Candidate 1: REJECTED, 3. Candidate 2: VERIFIED, 4. Final: VERIFIED
    executor = MultiTurnSyntheticExecutor(["REJECTED", "REJECTED", "VERIFIED", "VERIFIED"])
    store, worker, task_id = _setup_task(tmp_path, provider=provider, executor=executor)

    # 1. Plan & approve
    store.enqueue("c03-tester", task_id, "plan-step", phase="plan")
    worker.run_once()
    plan_hash = CodingPlan.model_validate(store.get_task("c03-tester", task_id)["plan"]).identity()
    store.approve_plan("c03-tester", task_id, plan_hash)
    store.enqueue("c03-tester", task_id, "run-step", phase="run")

    # 2. Baseline check (REJECTED)
    worker.run_once()

    # 3. Model generates Attempt 1
    worker.run_once()
    assert store.get_task("c03-tester", task_id)["next_stage"] == "CANDIDATE"

    # 4. Candidate 1 executed and fails (REJECTED) -> loops back to EDIT
    worker.run_once()
    task_after_fail = store.get_task("c03-tester", task_id)
    assert task_after_fail["next_stage"] == "EDIT"
    assert task_after_fail["counters"]["patch_attempts"] == 1
    assert task_after_fail["checkpoint"]["last_candidate"]["verdict"] == "REJECTED"

    # 5. Model generates Attempt 2
    worker.run_once()
    # Verify that the model received the failure feedback from Attempt 1!
    last_prompt = json.loads(provider.calls[-1]["user_prompt"])
    assert "observations" in last_prompt
    observations = last_prompt["observations"]
    assert observations["previous_candidate"]["verdict"] == "REJECTED"
    assert "Boundary rounding defect in call 2" in observations["previous_candidate"]["checks"][0]["reason"]
    assert "Candidate edit (flawed-attempt-1)" in observations["previous_patch"]

    # 6. Candidate 2 executed and passes (VERIFIED) -> transitions to FINAL
    worker.run_once()
    assert store.get_task("c03-tester", task_id)["next_stage"] == "FINAL"

    # 7. Final independent check passes -> REVIEW_READY
    worker.run_once()
    final_task = store.get_task("c03-tester", task_id)
    assert final_task["state"] == "REVIEW_READY"
    assert final_task["counters"]["model_calls"] == 3  # 1 plan + 2 edits
    assert final_task["counters"]["patch_attempts"] == 2
    assert final_task["counters"]["executions"] == 4  # baseline + cand 1 + cand 2 + final
    assert "Candidate edit (repaired-attempt-2)" in final_task["result"]["diff"]


def test_c03_repeated_candidate_circuit_breaker(tmp_path: Path) -> None:
    """If the model generates the identical candidate twice after a rejection, the engine stalls."""
    provider = MultiTurnSyntheticProvider(edits=["same-edit", "same-edit"])
    executor = MultiTurnSyntheticExecutor(["REJECTED", "REJECTED"])
    store, worker, task_id = _setup_task(tmp_path, provider=provider, executor=executor)

    # Plan, approve, baseline
    store.enqueue("c03-tester", task_id, "plan", phase="plan")
    worker.run_once()
    plan_hash = CodingPlan.model_validate(store.get_task("c03-tester", task_id)["plan"]).identity()
    store.approve_plan("c03-tester", task_id, plan_hash)
    store.enqueue("c03-tester", task_id, "start", phase="run")
    worker.run_once()  # Baseline

    # Attempt 1
    worker.run_once()  # Edit 1 (same-edit)
    worker.run_once()  # Candidate 1 executes and fails

    # Attempt 2 produces identical code
    worker.run_once()  # Edit 2 (same-edit) -> detects repeated candidate!
    task = store.get_task("c03-tester", task_id)
    assert task["state"] == "STALLED"
    assert task["result"]["code"] == "REPEATED_CANDIDATE"
    # No execution was wasted on the repeated candidate!
    assert len(executor.calls) == 2


def test_c03_full_api_and_worker_integration(client: TestClient, tmp_path: Path, monkeypatch: Any) -> None:
    """Full end-to-end flow driven entirely via FastAPI HTTP endpoints + background worker."""
    db_path = tmp_path / "api_worker_c03.db"
    settings = api_main.settings
    for name, value in {
        "benchproof_coding_enabled": True,
        "benchproof_coding_model_calls_per_day": 20,
        "benchproof_coding_executions_per_day": 20,
        "benchproof_coding_deadline_epoch": 9999999999.0,
        "database_path": str(db_path),
        "nebius_api_key": "synthetic-key",
        "nebius_model_id": "synthetic/c03-tester",
    }.items():
        monkeypatch.setattr(settings, name, value)

    monkeypatch.setattr(api_main.app.state, "runner", {
        "mode": "docker", "isolated_execution_available": True, "detail": "synthetic test runner",
    })

    provider = MultiTurnSyntheticProvider(edits=["api-candidate-edit"])
    executor = MultiTurnSyntheticExecutor(["REJECTED", "VERIFIED", "VERIFIED"])
    engine = CodingEngine(
        client=provider, model_id="synthetic/c03-tester", executor=executor, synthetic=True,
    )
    store = CodingStore(db_path, OperatorLimits(model_calls_per_day=20, executions_per_day=20))
    worker = CodingWorker(store, engine, worker_id="api-worker-1")

    # 1. API: Create task
    app_dir = fixture_dir("MC-01") / "app"
    create_resp = client.post(
        "/api/v1/coding-tasks",
        json={
            "fixture_id": "MC-01",
            "task": "Fix compute_total to accumulate Decimal instances",
            "source_hash": source_hash_for_dir(app_dir),
            "editable_paths": ["app/money.py"],
        },
        headers={"Idempotency-Key": "api-create-c03"},
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["task_id"]

    # 2. API: Request planning
    plan_req = client.post(f"/api/v1/coding-tasks/{task_id}/plan", headers={"Idempotency-Key": "api-plan-c03"})
    assert plan_req.status_code == 202

    # Worker generates plan
    worker.run_once()
    task_plan_resp = client.get(f"/api/v1/coding-tasks/{task_id}/plan")
    assert task_plan_resp.status_code == 200
    plan_data = task_plan_resp.json()
    assert plan_data["state"] == "AWAITING_APPROVAL"
    plan_hash = plan_data["plan_hash"]

    # 3. API: Approve plan
    approve_resp = client.post(
        f"/api/v1/coding-tasks/{task_id}/approve",
        json={"plan_hash": plan_hash},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["state"] == "APPROVED"

    # 4. API: Start execution
    start_resp = client.post(f"/api/v1/coding-tasks/{task_id}/start", headers={"Idempotency-Key": "api-start-c03"})
    assert start_resp.status_code == 202

    # 5. Worker processes until completion
    # Baseline -> Edit -> Candidate -> Final
    for _ in range(6):
        status = worker.run_once()
        if status is None or status.get("state") in {"REVIEW_READY", "BLOCKED", "STALLED"}:
            break

    # 6. Verify via API endpoints
    task_get = client.get(f"/api/v1/coding-tasks/{task_id}").json()
    assert task_get["state"] == "REVIEW_READY"

    changes = client.get(f"/api/v1/coding-tasks/{task_id}/changes").json()
    assert changes["tested_final"] is True
    assert "Candidate edit (api-candidate-edit)" in changes["diff"]

    executions = client.get(f"/api/v1/coding-tasks/{task_id}/executions").json()
    assert len(executions) == 3  # baseline, candidate, final
    stages = [e["stage"] for e in executions]
    assert stages == ["BASELINE", "CANDIDATE", "FINAL"]

    usage = client.get(f"/api/v1/coding-tasks/{task_id}/usage").json()
    assert usage["counters"]["model_calls"] == 2
    assert usage["counters"]["executions"] == 3
    assert usage["recorded_tokens"] == 360  # 180 tokens * 2 calls

    events = client.get(f"/api/v1/coding-tasks/{task_id}/events").json()
    event_types = [ev["event_type"] for ev in events]
    assert "TASK_CREATED" in event_types
    assert "PLAN_APPROVED" in event_types
    assert "ACTION_FINISHED" in event_types
