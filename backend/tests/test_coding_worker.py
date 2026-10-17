"""Synthetic provider/runner tests; no candidate import, Docker or paid inference."""

from __future__ import annotations

import json

import pytest

from benchproof.coding.contracts import OperatorLimits
from benchproof.coding.engine import CodingEngine, InvoiceExecutor
from benchproof.coding.generation import CodingBrief, CodingPlan
from benchproof.coding.store import CodingStore, CodingStoreError
from benchproof.coding.worker import CodingWorker
from benchproof.constraints import contract_hash
from benchproof.execution.base import ExecutionResult
from benchproof.fixtures import candidate_files, fixture_dir, source_hash_for_dir


class SyntheticProvider:
    def __init__(self, *, edits=None, hook=None, finish_reason="stop"):
        self.edits = edits or ["first", "second"]
        self.hook = hook
        self.finish_reason = finish_reason
        self.calls = []
        self.edit_count = 0

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        payload = json.loads(kwargs["user_prompt"])
        if self.hook:
            self.hook(payload)
        if "brief" in payload:
            result = {
                "source_hash": payload["source_hash"],
                "brief_hash": payload["brief_hash"],
                "steps": ["Repair the approved money implementation"],
                "target_files": payload["brief"]["editable_paths"],
                "check_profile": "invoice-observation-v1",
            }
        else:
            marker = self.edits[self.edit_count]
            self.edit_count += 1
            content = payload["source"]["app/money.py"].replace(
                "Faulty: premature rounding of each line.",
                f"Synthetic candidate {marker}.",
            )
            result = {
                "source_hash": payload["source_hash"],
                "plan_hash": payload["plan_hash"],
                "files": [{"path": "app/money.py", "content": content}],
                "explanation": "Synthetic generated edit for orchestration testing only",
            }
        return {
            "content": json.dumps(result),
            "finish_reason": self.finish_reason,
            "response_id": f"synthetic-response-{len(self.calls)}",
            "response_model": "synthetic/no-model",
            "usage": {"prompt_tokens": 80, "completion_tokens": 40, "total_tokens": 120},
        }


class SyntheticExecutor:
    def __init__(self, verdicts=None, hook=None):
        self.verdicts = verdicts or ["REJECTED", "VERIFIED", "VERIFIED"]
        self.hook = hook
        self.calls = []
        self.cancelled = []

    def run(self, app_dir, *, operation_id, timeout_s, should_cancel=None):
        assert not should_cancel or not should_cancel()
        self.calls.append(
            {
                "source_hash": source_hash_for_dir(app_dir),
                "operation_id": operation_id,
                "timeout_s": timeout_s,
            }
        )
        if self.hook:
            self.hook()
        verdict = self.verdicts[len(self.calls) - 1]
        return {
            "profile": "invoice-observation-v1",
            "source_hash": source_hash_for_dir(app_dir),
            "contract_hash": contract_hash(),
            "verdict": verdict,
            "checks": [
                {
                    "check_id": "amount-boundary",
                    "outcome": "PASS" if verdict == "VERIFIED" else "FAIL",
                    "reason": f"Synthetic observed failure {len(self.calls)}",
                }
            ],
            "execution": {"runner": "synthetic-test-only", "exit_code": 0, "timed_out": False},
        }

    def cancel(self, operation_id):
        self.cancelled.append(operation_id)
        return True


def _setup(tmp_path, *, provider=None, executor=None, clock=None, limits=None):
    store = CodingStore(
        tmp_path / "coding.db",
        limits or OperatorLimits(model_calls_per_day=20, executions_per_day=20),
        **({"clock": clock} if clock else {}),
    )
    app_dir = fixture_dir("MC-01") / "app"
    files = {
        path.relative_to(app_dir.parent).as_posix(): path.read_bytes().decode("utf-8")
        for path in candidate_files(app_dir)
    }
    brief = CodingBrief(
        task="Repair invoice rounding while preserving the contract",
        source_hash=source_hash_for_dir(app_dir),
        editable_paths=["app/money.py"],
    )
    task = store.create_task("owner", "MC-01", brief, files, contract_hash(), "create")
    provider = provider or SyntheticProvider()
    executor = executor or SyntheticExecutor()
    engine = CodingEngine(
        client=provider, model_id="synthetic/no-model", executor=executor, synthetic=True
    )
    worker = CodingWorker(store, engine, worker_id="synthetic-worker")
    store.enqueue("owner", task["task_id"], "plan", phase="plan")
    return store, worker, provider, executor, task["task_id"]


def _approve(store, worker, task_id):
    assert worker.run_once()["state"] == "AWAITING_APPROVAL"
    task = store.get_task("owner", task_id)
    store.approve_plan("owner", task_id, CodingPlan.model_validate(task["plan"]).identity())
    store.enqueue("owner", task_id, "run", phase="run")


def _drain(worker):
    for _ in range(12):
        if worker.run_once() is None:
            return
    raise AssertionError("The bounded synthetic worker did not stop")


def test_plan_requires_exact_owner_approval_before_any_execution_or_edit(tmp_path):
    store, worker, provider, executor, task_id = _setup(tmp_path)
    original = store.get_task("owner", task_id)["source_files"]
    assert worker.run_once()["state"] == "AWAITING_APPROVAL"
    assert worker.run_once() is None
    assert len(provider.calls) == 1
    assert not executor.calls
    task = store.get_task("owner", task_id)
    with pytest.raises(CodingStoreError):
        store.approve_plan("owner", task_id, "0" * 64)
    with pytest.raises(CodingStoreError):
        store.enqueue("owner", task_id, "run-too-soon", phase="run")
    store.approve_plan("owner", task_id, CodingPlan.model_validate(task["plan"]).identity())
    store.enqueue("owner", task_id, "run", phase="run")
    _drain(worker)
    task = store.get_task("owner", task_id)
    assert task["state"] == "REVIEW_READY"
    assert task["result"]["diff"].startswith("--- a/app/money.py")
    assert task["source_files"] == original
    assert task["counters"]["model_calls"] == 2
    assert task["counters"]["executions"] == 3
    assert task["counters"]["patch_attempts"] == 1
    assert task["checkpoint"]["patch"]["author"] == "synthetic-test-coding-agent"
    assert all(
        action["result"]["provider"]["mode"] == "synthetic"
        for action in task["actions"]
        if action["kind"] != "EXECUTION"
    )
    assert executor.calls[1]["source_hash"] == executor.calls[2]["source_hash"]
    assert len({call["operation_id"] for call in executor.calls}) == 3


def test_rejected_candidate_supplies_actual_failure_to_bounded_revision(tmp_path):
    executor = SyntheticExecutor(["REJECTED", "REJECTED", "VERIFIED", "VERIFIED"])
    store, worker, provider, executor, task_id = _setup(tmp_path, executor=executor)
    _approve(store, worker, task_id)
    _drain(worker)
    task = store.get_task("owner", task_id)
    assert task["state"] == "REVIEW_READY"
    assert task["counters"]["model_calls"] == 3
    assert task["counters"]["patch_attempts"] == 2
    assert task["counters"]["executions"] == 4
    observations = json.loads(provider.calls[-1]["user_prompt"])["observations"]
    assert (
        observations["previous_candidate"]["checks"][0]["reason"] == "Synthetic observed failure 2"
    )
    assert "Synthetic candidate first" in observations["previous_patch"]
    assert "Synthetic candidate second" in task["result"]["diff"]
    assert executor.calls[-1]["source_hash"] == task["checkpoint"]["candidate_hash"]


def test_repeated_failed_candidate_stalls_without_an_extra_execution(tmp_path):
    provider = SyntheticProvider(edits=["same", "same"])
    executor = SyntheticExecutor(["REJECTED", "REJECTED"])
    store, worker, provider, executor, task_id = _setup(
        tmp_path, provider=provider, executor=executor
    )
    _approve(store, worker, task_id)
    _drain(worker)
    task = store.get_task("owner", task_id)
    assert task["state"] == "STALLED"
    assert task["result"]["code"] == "REPEATED_CANDIDATE"
    assert len(executor.calls) == 2
    assert len(provider.calls) == 3


def test_distinct_second_failure_stops_at_patch_limit(tmp_path):
    executor = SyntheticExecutor(["REJECTED", "REJECTED", "REJECTED"])
    store, worker, provider, executor, task_id = _setup(tmp_path, executor=executor)
    _approve(store, worker, task_id)
    _drain(worker)
    task = store.get_task("owner", task_id)
    assert task["state"] == "BLOCKED"
    assert task["result"]["code"] == "PATCH_ATTEMPT_LIMIT"
    assert len(provider.calls) == 3
    assert len(executor.calls) == 3


def test_fresh_final_check_failure_never_reports_review_ready(tmp_path):
    executor = SyntheticExecutor(["REJECTED", "VERIFIED", "REJECTED"])
    store, worker, provider, executor, task_id = _setup(tmp_path, executor=executor)
    _approve(store, worker, task_id)
    _drain(worker)
    task = store.get_task("owner", task_id)
    assert task["state"] == "BLOCKED"
    assert task["result"]["code"] == "FRESH_CHECK_FAILED"
    assert len(provider.calls) == 2


def test_pausing_inside_model_call_settles_usage_and_resumes_without_repeating_it(tmp_path):
    store, worker, provider, _executor, task_id = _setup(tmp_path)
    _approve(store, worker, task_id)
    assert worker.run_once()["stage"] == "EDIT"
    provider.hook = lambda payload: store.control("owner", task_id, "pause")
    assert worker.run_once()["state"] == "PAUSED"
    task = store.get_task("owner", task_id)
    assert task["next_stage"] == "CANDIDATE"
    assert task["actions"][-1]["usage"]["usage"]["total_tokens"] == 120
    provider.hook = None
    store.control("owner", task_id, "resume")
    _drain(worker)
    assert len(provider.calls) == 2
    assert store.get_task("owner", task_id)["state"] == "REVIEW_READY"


def test_cancel_inside_model_call_discards_late_patch_and_keeps_unknown_reservation(tmp_path):
    store, worker, provider, executor, task_id = _setup(tmp_path)
    _approve(store, worker, task_id)
    worker.run_once()
    provider.hook = lambda payload: store.control("owner", task_id, "cancel")
    assert worker.run_once()["code"] == "STALE_LEASE"
    task = store.get_task("owner", task_id)
    assert task["state"] == "CANCELLED"
    assert "patch" not in task["checkpoint"]
    assert task["actions"][-1]["status"] == "UNKNOWN"
    assert task["counters"]["model_calls"] == 2
    assert len(executor.calls) == 1


def test_cancel_inside_execution_requires_stopped_operation_before_cancelled(tmp_path):
    store, worker, _provider, executor, task_id = _setup(tmp_path)
    _approve(store, worker, task_id)
    observed = []

    def cancel():
        observed.append(store.control("owner", task_id, "cancel")["state"])

    executor.hook = cancel
    assert worker.run_once()["code"] == "STALE_LEASE"
    assert observed == ["CANCEL_PENDING"]
    task = store.get_task("owner", task_id)
    assert task["state"] == "CANCELLED"
    assert "baseline" not in task["checkpoint"]
    assert set(executor.cancelled) == {executor.calls[0]["operation_id"]}


def test_provider_crash_is_unknown_after_lease_expiry_and_never_automatically_retried(tmp_path):
    now = [1_800_000_000.0]
    store, worker, provider, _executor, task_id = _setup(tmp_path, clock=lambda: now[0])

    def crash(payload):
        raise RuntimeError("Synthetic abrupt provider-process failure")

    provider.hook = crash
    with pytest.raises(RuntimeError, match="Synthetic abrupt"):
        worker.run_once()
    assert store.get_task("owner", task_id)["actions"][-1]["status"] == "RUNNING"
    now[0] += 121
    assert worker.run_once() is None
    task = store.get_task("owner", task_id)
    assert task["state"] == "INTERRUPTED"
    assert task["actions"][-1]["status"] == "UNKNOWN"
    assert task["counters"]["model_calls"] == 1
    assert len(provider.calls) == 1
    with pytest.raises(CodingStoreError) as error:
        store.control("owner", task_id, "resume")
    assert error.value.code == "RECONCILIATION_REQUIRED"


def test_stale_fence_cannot_publish_a_completed_plan(tmp_path):
    now = [1_800_000_000.0]
    store, worker, provider, _executor, task_id = _setup(tmp_path, clock=lambda: now[0])
    provider.hook = lambda payload: now.__setitem__(0, now[0] + 121)
    assert worker.run_once()["code"] == "STALE_LEASE"
    task = store.get_task("owner", task_id)
    assert task["state"] == "INTERRUPTED"
    assert task["plan"] is None
    assert task["actions"][-1]["status"] == "UNKNOWN"


def test_truncated_plan_is_not_repaired_retried_or_executed(tmp_path):
    provider = SyntheticProvider(finish_reason="length")
    store, worker, provider, executor, task_id = _setup(tmp_path, provider=provider)
    assert worker.run_once()["code"] == "MODEL_OUTPUT_TRUNCATED"
    task = store.get_task("owner", task_id)
    assert task["state"] == "BLOCKED"
    assert task["plan"] is None
    assert task["actions"][-1]["usage"]["usage"]["total_tokens"] == 120
    assert len(provider.calls) == 1
    assert not executor.calls


def test_daily_operator_limit_blocks_without_provider_call_or_dangling_lease(tmp_path):
    store, worker, provider, _executor, task_id = _setup(tmp_path, limits=OperatorLimits())
    assert worker.run_once()["code"] == "OPERATOR_LIMIT"
    task = store.get_task("owner", task_id)
    assert task["state"] == "BLOCKED"
    assert task["lease_worker"] is None
    assert not provider.calls


def test_live_worker_disabled_by_default_and_refuses_short_session_window(tmp_path):
    store, worker, provider, _executor, task_id = _setup(tmp_path)
    worker.engine.synthetic = False
    assert worker.run_once() == {"code": "LIVE_DISABLED"}
    worker.live_enabled = True
    assert worker.run_once() == {"code": "SESSION_WINDOW_INSUFFICIENT"}
    assert store.get_task("owner", task_id)["state"] == "QUEUED"
    assert not provider.calls


def test_runtime_identity_change_blocks_before_model_reservation(tmp_path):
    store, worker, provider, _executor, task_id = _setup(tmp_path)
    worker.engine.synthetic = False
    worker.live_enabled = True
    worker.session_seconds_remaining = lambda: 600
    assert worker.run_once()["code"] == "STALE_RUNTIME"
    task = store.get_task("owner", task_id)
    assert task["state"] == "BLOCKED"
    assert not task["actions"]
    assert not provider.calls


def test_restarted_worker_reconciles_orphan_execution_without_automatic_retry(tmp_path):
    now = [1_800_000_000.0]
    store, worker, provider, executor, task_id = _setup(tmp_path, clock=lambda: now[0])
    _approve(store, worker, task_id)

    def crash():
        raise RuntimeError("Synthetic execution worker disappeared")

    executor.hook = crash
    with pytest.raises(RuntimeError, match="disappeared"):
        worker.run_once()
    operation_id = store.get_task("owner", task_id)["actions"][-1]["details"]["operation_id"]
    now[0] += 121
    restarted = CodingWorker(store, worker.engine, worker_id="restarted-synthetic-worker")
    assert restarted.run_once()["code"] == "OPERATION_STOPPED"
    task = store.get_task("owner", task_id)
    assert task["state"] == "INTERRUPTED"
    assert task["actions"][-1]["status"] == "INTERRUPTED_STOPPED"
    assert executor.cancelled == [operation_id]
    assert task["counters"]["executions"] == 1
    assert len(provider.calls) == 1
    assert restarted.run_once() is None
    assert len(executor.calls) == 1


def test_oversized_known_result_settles_compact_failure_without_replaying_execution(tmp_path):
    class OversizedSyntheticExecutor(SyntheticExecutor):
        def run(self, *args, **kwargs):
            report = super().run(*args, **kwargs)
            report["execution"]["stdout"] = "x" * 140_000
            return report

    executor = OversizedSyntheticExecutor()
    store, worker, provider, executor, task_id = _setup(tmp_path, executor=executor)
    _approve(store, worker, task_id)
    assert worker.run_once()["code"] == "STORAGE_LIMIT"
    task = store.get_task("owner", task_id)
    assert task["state"] == "BLOCKED"
    assert task["actions"][-1]["status"] == "FAILED"
    assert task["result"]["code"] == "RESULT_LIMIT"
    assert task["lease_worker"] is None
    assert len(executor.calls) == 1
    assert len(provider.calls) == 1


def test_remaining_active_allowance_bounds_subsequent_request_and_execution_timeouts(tmp_path):
    now = [1_800_000_000.0]
    executor = SyntheticExecutor(["REJECTED", "REJECTED", "VERIFIED", "VERIFIED"])
    store, worker, provider, executor, task_id = _setup(
        tmp_path, clock=lambda: now[0], executor=executor
    )

    def consume_model_time(payload):
        if "brief" in payload:
            now[0] += 99
        elif provider.edit_count == 0:
            now[0] += 100

    def consume_baseline_time():
        if len(executor.calls) == 1:
            now[0] += 100

    provider.hook = consume_model_time
    executor.hook = consume_baseline_time
    _approve(store, worker, task_id)
    _drain(worker)
    assert provider.calls[0]["timeout_s"] == 30
    assert provider.calls[-1]["timeout_s"] == 1
    assert executor.calls[0]["timeout_s"] == 30
    assert all(call["timeout_s"] == 1 for call in executor.calls[1:])


@pytest.mark.parametrize("stage", ["PLAN", "BASELINE"])
def test_cancel_after_reservation_prevents_any_new_external_dispatch(tmp_path, stage, monkeypatch):
    store, worker, provider, executor, task_id = _setup(tmp_path)
    if stage == "BASELINE":
        _approve(store, worker, task_id)
    original_reserve = store.reserve_action

    def reserve_then_cancel(*args, **kwargs):
        action = original_reserve(*args, **kwargs)
        store.control("owner", task_id, "cancel")
        return action

    monkeypatch.setattr(store, "reserve_action", reserve_then_cancel)
    assert worker.run_once()["code"] == "STALE_LEASE"
    task = store.get_task("owner", task_id)
    assert task["state"] == "CANCELLED"
    assert len(provider.calls) == int(stage == "BASELINE")
    assert not executor.calls


def test_invoice_executor_never_uses_host_collector_and_requires_isolation(tmp_path):
    class SyntheticDocker:
        def run_observation(self, snapshot, **kwargs):
            assert kwargs["operation_id"] == "bp-coding-" + "a" * 32
            assert callable(kwargs["should_cancel"])
            return ExecutionResult(
                "synthetic-test-only",
                snapshot.run_id,
                0,
                False,
                1,
                "",
                "",
                None,
                isolation={"enforced": False},
            )

        def cancel_operation(self, operation_id):
            return True

    from benchproof.coding.generation import GenerationError

    with pytest.raises(GenerationError) as error:
        InvoiceExecutor(SyntheticDocker()).run(
            fixture_dir("MC-01") / "app", operation_id="bp-coding-" + "a" * 32, timeout_s=30
        )
    assert error.value.code == "RUNNER_UNAVAILABLE"
