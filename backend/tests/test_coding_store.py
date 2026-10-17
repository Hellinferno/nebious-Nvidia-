"""Durable coding admission, ownership, action settlement and crash recovery."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from benchproof.coding.contracts import (
    CodingBrief,
    CodingPlan,
    CodingStoreError,
    OperatorLimits,
)
from benchproof.coding.store import CodingStore
from benchproof.fixtures import source_hash_for_dir


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    app = root / "sample" / "app"
    app.mkdir(parents=True)
    (app / "core.py").write_bytes(b"VALUE = 1\r\n")
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(root))
    source = {"app/core.py": "VALUE = 1\r\n"}
    brief = CodingBrief(task="Change VALUE to two", source_hash=source_hash_for_dir(app),
                        editable_paths=["app/core.py"])
    return app, source, brief


@pytest.fixture
def clock():
    return [1_790_000_000.0]


@pytest.fixture
def store(tmp_path, clock):
    return CodingStore(tmp_path / "coding.db", OperatorLimits(100, 100), clock=lambda: clock[0])


def _create(store, prepared, owner="owner-a", key="create-one"):
    _, source, brief = prepared
    return store.create_task(owner, "sample", brief, source, "c" * 64, key)


def _queued(store, prepared, owner="owner-a", key="create-one"):
    task = _create(store, prepared, owner, key)
    return store.enqueue(owner, task["task_id"], f"enqueue-{key}")


def _plan(brief):
    return CodingPlan(source_hash=brief.source_hash, brief_hash=brief.identity(),
                      steps=["Change the constant"], target_files=brief.editable_paths)


def _approved(store, prepared):
    task = _queued(store, prepared)
    lease = store.claim_next("planner")
    action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    plan = _plan(prepared[2])
    task = store.finish_action(lease, action["action_id"], {"plan": plan.model_dump()},
                              usage={"total_tokens": 10}, state="AWAITING_APPROVAL",
                              next_stage="BASELINE", checkpoint={"plan": plan.model_dump()})
    task = store.approve_plan("owner-a", task["task_id"], plan.identity())
    return task, plan


def _running(store, prepared):
    task, plan = _approved(store, prepared)
    task = store.enqueue("owner-a", task["task_id"], "run", phase="run")
    return task, plan, store.claim_next("executor")


def _error(code, function, *args, **kwargs):
    with pytest.raises(CodingStoreError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


def test_original_bytes_owner_scope_and_create_idempotency(store, prepared):
    task = _create(store, prepared)
    assert task["state"] == "DRAFT"
    assert task["source_files"] == {"app/core.py": "VALUE = 1\r\n"}
    assert _create(store, prepared)["task_id"] == task["task_id"]
    assert len(store.list_events("owner-a", task["task_id"])) == 1
    assert store.list_tasks("owner-b") == []
    for function, args in (
        (store.get_task, ("owner-b", task["task_id"])),
        (store.list_events, ("owner-b", task["task_id"])),
        (store.enqueue, ("owner-b", task["task_id"], "foreign")),
        (store.control, ("owner-b", task["task_id"], "cancel")),
    ):
        _error("NOT_FOUND", function, *args)


def test_create_replay_uses_persisted_snapshot_after_fixture_changes(store, prepared):
    task = _create(store, prepared)
    (prepared[0] / "core.py").write_bytes(b"VALUE = 9\n")
    assert _create(store, prepared)["source_files"] == task["source_files"]
    _error("STALE_SOURCE", _create, store, prepared, key="new-create")


def test_create_and_queue_idempotency_conflicts(store, prepared):
    task = _queued(store, prepared)
    other = prepared[2].model_copy(update={"task": "A different task"})
    _error("IDEMPOTENCY_CONFLICT", store.create_task, "owner-a", "sample", other,
           prepared[1], "c" * 64, "create-one")
    assert store.enqueue("owner-a", task["task_id"], "enqueue-create-one")["task_id"] == task["task_id"]
    assert len([event for event in store.list_events("owner-a", task["task_id"])
                if event["event_type"] == "TASK_QUEUED"]) == 1


def test_snapshot_identity_profile_and_global_task_count(tmp_path, prepared):
    store = CodingStore(tmp_path / "small.db", OperatorLimits(1, 1, max_tasks=1))
    _create(store, prepared)
    _error("STORAGE_LIMIT", _create, store, prepared, key="second")
    changed = {"app/core.py": "VALUE = 2\n"}
    _error("STALE_SOURCE", store.create_task, "owner-a", "sample", prepared[2], changed,
           "c" * 64, "changed")
    _error("INVALID_INPUT", store.create_task, "owner-a", "sample", prepared[2],
           {"../secret.py": "secret"}, "c" * 64, "traversal")
    _error("STORAGE_LIMIT", store.create_task, "owner-a", "sample", prepared[2],
           {"app/core.py": "x" * 24_577}, "c" * 64, "large")


def test_single_global_claim_and_concurrent_enqueue(store, prepared):
    task = _create(store, prepared)
    with ThreadPoolExecutor(max_workers=4) as executor:
        queued = list(executor.map(
            lambda _: store.enqueue("owner-a", task["task_id"], "same-enqueue"), range(4),
        ))
    assert all(item["task_id"] == task["task_id"] for item in queued)
    other = _create(store, prepared, owner="owner-b", key="another")
    _error("BUSY", store.enqueue, "owner-b", other["task_id"], "other-enqueue")
    with ThreadPoolExecutor(max_workers=4) as executor:
        leases = list(executor.map(lambda index: store.claim_next(f"worker-{index}"), range(4)))
    assert sum(lease is not None for lease in leases) == 1


def test_live_actions_disabled_by_default(tmp_path, prepared):
    store = CodingStore(tmp_path / "disabled.db")
    task = _queued(store, prepared)
    lease = store.claim_next("worker")
    _error("OPERATOR_LIMIT", store.reserve_action, lease, "PLAN", prepared[2].source_hash)
    persisted = store.get_task("owner-a", task["task_id"])
    assert persisted["counters"]["model_calls"] == 0
    assert persisted["actions"] == []


def test_plan_approval_is_exact_and_start_is_separate(store, prepared):
    task, plan = _approved(store, prepared)
    assert task["state"] == "APPROVED"
    assert store.claim_next("worker") is None
    _error("STALE_PLAN", store.approve_plan, "owner-a", task["task_id"], "a" * 64)
    updated = plan.model_copy(update={"steps": ["A revised implementation step"]})
    task = store.update_plan("owner-a", task["task_id"], updated)
    assert task["state"] == "AWAITING_APPROVAL" and task["approved_plan_hash"] is None
    _error("INVALID_STATE", store.enqueue, "owner-a", task["task_id"], "unapproved", phase="run")
    _error("STALE_PLAN", store.approve_plan, "owner-a", task["task_id"], plan.identity())
    task = store.approve_plan("owner-a", task["task_id"], updated.identity())
    task = store.enqueue("owner-a", task["task_id"], "approved-start", phase="run")
    assert task["next_stage"] == "BASELINE"
    assert task["counters"]["model_calls"] == 1


def test_source_and_approved_plan_pins_enforced_before_reserving(store, prepared):
    task, plan, lease = _running(store, prepared)
    _error("STALE_SOURCE", store.reserve_action, lease, "EXECUTION", "f" * 64, plan.identity())
    _error("PLAN_UNAPPROVED", store.reserve_action, lease, "EXECUTION", prepared[2].source_hash, "e" * 64)
    _error("INVALID_STATE", store.reserve_action, lease, "EDIT", prepared[2].source_hash, plan.identity())
    assert store.get_task("owner-a", task["task_id"])["counters"]["executions"] == 0


def test_action_result_usage_checkpoint_and_next_stage_commit_together(store, prepared):
    task, plan, lease = _running(store, prepared)
    action = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan.identity())
    _error("ACTION_IN_FLIGHT", store.reserve_action, lease, "EXECUTION",
           prepared[2].source_hash, plan.identity())
    result = {"checks": [{"check_id": "example", "outcome": "FAIL"}]}
    task = store.finish_action(lease, action["action_id"], result, usage={"status": "NOT_APPLICABLE"},
                              next_stage="EDIT", checkpoint={"baseline": result}, state="QUEUED")
    assert task["state"] == "QUEUED" and task["next_stage"] == "EDIT"
    assert task["result"] == result and task["checkpoint"] == {"baseline": result}
    assert task["actions"][-1]["status"] == "SUCCEEDED"
    assert task["counters"]["executions"] == 1
    _error("STALE_LEASE", store.finish_action, lease, action["action_id"], {"late": True})
    assert store.claim_next("new-worker").fence > lease.fence


def test_action_failure_retains_model_and_patch_reservations(store, prepared):
    task, plan, lease = _running(store, prepared)
    store.set_checkpoint(lease, "EDIT", {})
    for attempt in range(2):
        action = store.reserve_action(lease, "EDIT", prepared[2].source_hash, plan.identity())
        task = store.finish_action(lease, action["action_id"], {"code": "MODEL_OUTPUT_TRUNCATED"},
                                  status="FAILED", next_stage="EDIT", state="QUEUED")
        assert task["counters"]["patch_attempts"] == attempt + 1
        assert task["actions"][-1]["usage"] == {"status": "UNKNOWN"}
        lease = store.claim_next(f"revise-{attempt}")
    _error("BUDGET_EXHAUSTED", store.reserve_action, lease, "EDIT", prepared[2].source_hash, plan.identity())
    assert store.get_task("owner-a", task["task_id"])["counters"]["model_calls"] == 3


def test_four_model_call_limit_counts_invalid_outputs(store, prepared):
    task = _queued(store, prepared)
    for attempt in range(4):
        lease = store.claim_next(f"planner-{attempt}")
        action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
        store.finish_action(lease, action["action_id"], {"code": "MALFORMED_ACTION"},
                            status="FAILED", next_stage="PLAN", state="QUEUED")
    lease = store.claim_next("fifth")
    _error("BUDGET_EXHAUSTED", store.reserve_action, lease, "PLAN", prepared[2].source_hash)
    assert store.get_task("owner-a", task["task_id"])["counters"]["model_calls"] == 4


def test_four_execution_limit_includes_baseline_and_failed_runs(store, prepared):
    task, plan, lease = _running(store, prepared)
    for attempt in range(4):
        action = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan.identity())
        store.finish_action(lease, action["action_id"], {"exit_code": 1},
                            next_stage="BASELINE", state="QUEUED")
        lease = store.claim_next(f"runner-{attempt}")
    _error("BUDGET_EXHAUSTED", store.reserve_action, lease, "EXECUTION", prepared[2].source_hash, plan.identity())
    assert store.get_task("owner-a", task["task_id"])["counters"]["executions"] == 4


def test_daily_global_call_cap_survives_store_restart(tmp_path, prepared, clock):
    path = tmp_path / "daily.db"
    store = CodingStore(path, OperatorLimits(1, 2), clock=lambda: clock[0])
    _queued(store, prepared)
    lease = store.claim_next("first")
    action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    store.finish_action(lease, action["action_id"], {"failure": "bad output"}, state="BLOCKED")
    restarted = CodingStore(path, OperatorLimits(1, 2), clock=lambda: clock[0])
    _queued(restarted, prepared, owner="another", key="second")
    lease = restarted.claim_next("second")
    _error("OPERATOR_LIMIT", restarted.reserve_action, lease, "PLAN", prepared[2].source_hash)


def test_event_failure_rolls_back_action_counters_and_daily_reservation(store, prepared):
    task = _queued(store, prepared)
    lease = store.claim_next("worker")
    connection = sqlite3.connect(store.db_path)
    connection.execute("""
        CREATE TRIGGER reject_reservation BEFORE INSERT ON coding_events
        WHEN NEW.event_type='ACTION_RESERVED' BEGIN SELECT RAISE(ABORT,'forced event failure'); END
    """)
    connection.commit()
    connection.close()
    with pytest.raises(sqlite3.IntegrityError):
        store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    task = store.get_task("owner-a", task["task_id"])
    assert task["counters"]["model_calls"] == 0 and task["actions"] == []
    connection = sqlite3.connect(store.db_path)
    assert connection.execute("SELECT COUNT(*) FROM coding_daily_usage").fetchone()[0] == 0
    connection.close()


def test_settlement_failure_rolls_back_action_result_and_checkpoint(store, prepared):
    task = _queued(store, prepared)
    lease = store.claim_next("worker")
    action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    _error("STORAGE_LIMIT", store.finish_action, lease, action["action_id"], {"paid": True},
           checkpoint={"overflow": "x" * 262_144}, next_stage="EDIT", state="QUEUED")
    task = store.get_task("owner-a", task["task_id"])
    assert task["actions"][0]["status"] == "RUNNING"
    assert task["actions"][0]["result"] == {} and task["checkpoint"] == {}
    assert task["next_stage"] == "PLAN" and task["state"] == "RUNNING"


def test_expired_provider_call_is_unknown_not_replayed_and_old_worker_fenced(store, prepared, clock):
    task = _queued(store, prepared)
    lease = store.claim_next("crashed", lease_seconds=10)
    action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    clock[0] += 10_000
    assert store.claim_next("replacement") is None
    task = store.get_task("owner-a", task["task_id"])
    assert task["state"] == "INTERRUPTED" and task["actions"][0]["status"] == "UNKNOWN"
    assert task["counters"]["model_calls"] == 1
    assert task["counters"]["active_seconds"] == 10
    _error("STALE_LEASE", store.finish_action, lease, action["action_id"], {"late": True})
    _error("RECONCILIATION_REQUIRED", store.control, "owner-a", task["task_id"], "resume")
    store.control("owner-a", task["task_id"], "retry")
    replacement = store.claim_next("replacement")
    assert replacement.fence > lease.fence
    reserved = store.reserve_action(replacement, "PLAN", prepared[2].source_hash)
    assert reserved["action_id"] != action["action_id"]
    assert store.get_task("owner-a", task["task_id"])["counters"]["model_calls"] == 2


def test_pause_is_at_boundary_and_resume_preserves_paid_progress(store, prepared, clock):
    task = _queued(store, prepared)
    lease = store.claim_next("planner")
    action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    clock[0] += 12
    task = store.control("owner-a", task["task_id"], "pause")
    assert task["pause_requested"] and task["state"] == "RUNNING"
    task = store.finish_action(lease, action["action_id"], {"saved": True},
                              checkpoint={"saved": True}, state="QUEUED")
    assert task["state"] == "PAUSED"
    clock[0] += 999
    task = store.control("owner-a", task["task_id"], "resume")
    assert task["counters"]["model_calls"] == 1
    assert task["counters"]["active_seconds"] == 12 and task["checkpoint"] == {"saved": True}


def test_cancel_provider_keeps_unknown_usage_and_discards_late_mutation(store, prepared):
    task = _queued(store, prepared)
    lease = store.claim_next("planner")
    action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    task = store.control("owner-a", task["task_id"], "cancel")
    assert task["state"] == "CANCELLED"
    assert task["actions"][0]["status"] == "UNKNOWN"
    assert task["actions"][0]["usage"] == {"status": "UNKNOWN"}
    _error("STALE_LEASE", store.finish_action, lease, action["action_id"], {"late": "paid"})
    assert store.get_task("owner-a", task["task_id"])["result"] == {}


def test_execution_cancel_stays_pending_until_container_stop_confirmed(store, prepared):
    task, plan, lease = _running(store, prepared)
    action = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan.identity(),
                                  details={"operation_id": "bp-coding-test"})
    task = store.control("owner-a", task["task_id"], "cancel")
    assert task["state"] == "CANCEL_PENDING"
    assert store.claim_next("second") is None
    assert store.reconcile_execution(task["task_id"], "bp-coding-test", stopped=False)["state"] == "CANCEL_PENDING"
    _error("STALE_LEASE", store.finish_action, lease, action["action_id"], {"late": True})
    task = store.reconcile_execution(task["task_id"], "bp-coding-test", stopped=True)
    assert task["state"] == "CANCELLED"
    assert task["counters"]["executions"] == 1


def test_expired_execution_blocks_every_task_until_stop_then_explicit_retry(store, prepared, clock):
    task, plan, lease = _running(store, prepared)
    store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan.identity(),
                         details={"operation_id": "bp-coding-crashed"})
    other = _create(store, prepared, owner="owner-b", key="other")
    clock[0] += 61
    assert store.claim_next("new") is None
    _error("RECONCILIATION_REQUIRED", store.control, "owner-a", task["task_id"], "retry")
    store.reconcile_execution(task["task_id"], "bp-coding-crashed", stopped=True)
    _error("RECONCILIATION_REQUIRED", store.control, "owner-a", task["task_id"], "resume")
    store.enqueue("owner-b", other["task_id"], "other-enqueue")
    other_lease = store.claim_next("other-worker")
    assert other_lease.task_id == other["task_id"]
    _error("BUSY", store.control, "owner-a", task["task_id"], "retry")
    store.finish_task(other_lease, "BLOCKED", {"reason": "test finished"})
    task = store.control("owner-a", task["task_id"], "retry")
    assert task["counters"]["executions"] == 1
    assert task["actions"][-1]["status"] == "RETRY_ACKNOWLEDGED"


def test_active_budget_does_not_reset_across_pause_or_renew(store, prepared, clock):
    task = _queued(store, prepared)
    lease = store.claim_next("worker", lease_seconds=300)
    clock[0] += 250
    store.renew(lease, lease_seconds=300)
    store.control("owner-a", task["task_id"], "pause")
    _error("PAUSED", store.guard, lease)
    clock[0] += 1_000
    store.control("owner-a", task["task_id"], "resume")
    lease = store.claim_next("resumed", lease_seconds=300)
    clock[0] += 50
    _error("BUDGET_EXHAUSTED", store.guard, lease)
    task = store.get_task("owner-a", task["task_id"])
    assert task["state"] == "BUDGET_EXHAUSTED"
    assert task["counters"]["active_seconds"] == 300


def test_event_cursor_is_monotonic_and_owner_scoped(store, prepared):
    task = _queued(store, prepared)
    events = store.list_events("owner-a", task["task_id"])
    assert [event["sequence"] for event in events] == [1, 2]
    assert store.list_events("owner-a", task["task_id"], after_sequence=1) == events[1:]
    _error("INVALID_INPUT", store.list_events, "owner-a", task["task_id"], -1)


def test_operator_limits_do_not_claim_a_hard_token_budget():
    assert OperatorLimits().model_calls_per_day == 0
    assert OperatorLimits().executions_per_day == 0
    with pytest.raises(ValueError):
        OperatorLimits(model_calls_per_day=-1)
    with pytest.raises(ValueError):
        OperatorLimits(max_tasks=101)


def test_runtime_identity_is_persisted_and_bound_to_create_replay(store, prepared):
    runtime = {"model_id": "nvidia/test", "max_output_tokens": 2048, "engine_version": "v1"}
    task = store.create_task("owner-a", "sample", prepared[2], prepared[1], "c" * 64,
                             "configured", runtime_config=runtime)
    assert task["runtime_config"] == runtime
    assert task["schema_version"] == "coding-task-v1"
    assert task["source_profile"] == "prepared-fixture-v1"
    changed = {**runtime, "model_id": "nvidia/other"}
    _error("IDEMPOTENCY_CONFLICT", store.create_task, "owner-a", "sample", prepared[2],
           prepared[1], "c" * 64, "configured", runtime_config=changed)
    restarted = CodingStore(store.db_path, store.operator_limits)
    assert restarted.get_task("owner-a", task["task_id"])["runtime_config"] == runtime


def test_active_task_slot_survives_between_action_handoffs(store, prepared):
    task, plan, lease = _running(store, prepared)
    other = _create(store, prepared, owner="owner-b", key="waiting")
    action = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan.identity())
    store.finish_action(lease, action["action_id"], {"verdict": "REJECTED"},
                        next_stage="EDIT", state="QUEUED")
    _error("BUSY", store.enqueue, "owner-b", other["task_id"], "waiting-plan")
    store.control("owner-a", task["task_id"], "pause")
    store.enqueue("owner-b", other["task_id"], "waiting-plan")
    _error("BUSY", store.control, "owner-a", task["task_id"], "resume")


def test_internal_execution_recovery_never_returns_a_live_action(store, prepared, clock):
    task, plan, lease = _running(store, prepared)
    action = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan.identity(),
                                  details={"operation_id": "bp-coding-recover"})
    assert store.pending_executions() == []
    clock[0] += 61
    assert store.pending_executions() == [{"task_id": task["task_id"],
                                           "action_id": action["action_id"],
                                           "operation_id": "bp-coding-recover"}]
    store.reconcile_execution(task["task_id"], "bp-coding-recover", stopped=True)
    assert store.pending_executions() == []
    assert store.get_task("owner-a", task["task_id"])["state"] == "INTERRUPTED"
