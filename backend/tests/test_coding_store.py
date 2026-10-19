"""Durable coding admission, ownership, action settlement and crash recovery."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from benchproof.coding.contracts import (
    CodingBrief,
    CodingPlan,
    CodingPreferences,
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


def test_legacy_create_fingerprint_and_approved_plan_survive_store_restart(store, prepared):
    task, plan = _approved(store, prepared)
    brief = prepared[2]
    legacy = {
        "schema_version": "coding-brief-v1", "task": brief.task,
        "source_hash": brief.source_hash, "editable_paths": brief.editable_paths,
    }
    request = {
        "fixture_id": "sample", "brief": legacy, "source": prepared[1],
        "contract_hash": "c" * 64, "runtime_config": {},
    }
    expected = hashlib.sha256(json.dumps(
        request, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    with sqlite3.connect(store.db_path) as connection:
        fingerprint = connection.execute(
            "SELECT request_hash FROM coding_requests WHERE operation='create'",
        ).fetchone()[0]
    assert fingerprint == expected
    assert task["brief"] == legacy
    restarted = CodingStore(store.db_path, store.operator_limits, clock=store.clock)
    replay = _create(restarted, prepared)
    assert replay["task_id"] == task["task_id"]
    assert replay["approved_plan_hash"] == plan.identity()
    assert CodingBrief.model_validate(replay["brief"]).identity() == plan.brief_hash


def test_preferences_persist_export_and_bind_create_idempotency(store, prepared):
    preferences = CodingPreferences(workflow="feature", instructions="Preserve the existing public API")
    brief = prepared[2].model_copy(update={"preferences": preferences})
    task = store.create_task("owner-a", "sample", brief, prepared[1], "c" * 64, "custom")
    restarted = CodingStore(store.db_path, store.operator_limits, clock=store.clock)
    replay = restarted.create_task("owner-a", "sample", brief, prepared[1], "c" * 64, "custom")
    assert replay["task_id"] == task["task_id"]
    assert replay["brief"]["preferences"] == preferences.canonical_payload()
    assert restarted.export_bundle("owner-a", task["task_id"])["brief"] == brief.canonical_payload()
    changed = brief.model_copy(update={"preferences": CodingPreferences(workflow="bugfix")})
    _error("IDEMPOTENCY_CONFLICT", restarted.create_task, "owner-a", "sample", changed,
           prepared[1], "c" * 64, "custom")


def test_lowered_task_limits_are_durable_and_bound_to_create_and_plan(store, prepared):
    preferences = CodingPreferences.model_validate({"limits": {"model_calls": 2, "active_seconds": 30}})
    brief = prepared[2].model_copy(update={"preferences": preferences})
    task = store.create_task("owner-a", "sample", brief, prepared[1], "c" * 64, "limited")
    assert task["limits"] == {"model_calls": 2, "patch_attempts": 2, "executions": 4, "active_seconds": 30}
    restarted = CodingStore(store.db_path, store.operator_limits, clock=store.clock)
    replay = restarted.create_task("owner-a", "sample", brief, prepared[1], "c" * 64, "limited")
    assert replay["limits"] == task["limits"]
    assert replay["brief"]["preferences"]["limits"] == {"model_calls": 2, "active_seconds": 30}
    assert restarted.export_bundle("owner-a", task["task_id"])["brief"] == brief.canonical_payload()
    changed = brief.model_copy(update={"preferences": CodingPreferences(limits={"model_calls": 3})})
    _error("IDEMPOTENCY_CONFLICT", restarted.create_task, "owner-a", "sample", changed,
           prepared[1], "c" * 64, "limited")


def test_default_control_fields_replay_previous_preferences_without_identity_conflict(store, prepared):
    preferences = CodingPreferences(workflow="refactor", instructions="Keep the public API")
    brief = prepared[2].model_copy(update={"preferences": preferences})
    task = store.create_task("owner-a", "sample", brief, prepared[1], "c" * 64, "defaults")
    explicit = brief.model_copy(update={"preferences": CodingPreferences(
        workflow="refactor", instructions="Keep the public API", mode="implement", limits={},
    )})
    replay = store.create_task("owner-a", "sample", explicit, prepared[1], "c" * 64, "defaults")
    assert replay["task_id"] == task["task_id"]
    assert replay["brief"] == task["brief"]


@pytest.mark.parametrize("limit,kind,stage", [
    ("model_calls", "PLAN", "PLAN"), ("patch_attempts", "EDIT", "EDIT"),
    ("executions", "EXECUTION", "BASELINE"),
])
def test_lowered_action_allowance_blocks_the_next_reservation(store, prepared, limit, kind, stage):
    brief = prepared[2].model_copy(update={"preferences": CodingPreferences(limits={limit: 1})})
    customized = (prepared[0], prepared[1], brief)
    if kind == "PLAN":
        task = _queued(store, customized)
        plan_hash = None
        lease = store.claim_next("first")
    else:
        task, plan, lease = _running(store, customized)
        plan_hash = plan.identity()
        store.set_checkpoint(lease, stage, {})
    action = store.reserve_action(lease, kind, brief.source_hash, plan_hash)
    store.finish_action(lease, action["action_id"], {}, next_stage=stage, state="QUEUED")
    lease = store.claim_next("second")
    _error("BUDGET_EXHAUSTED", store.reserve_action, lease, kind, brief.source_hash, plan_hash)
    assert store.get_task("owner-a", task["task_id"])["counters"][limit] == 1


def test_lowered_active_time_applies_across_restart_and_resume(store, prepared, clock):
    brief = prepared[2].model_copy(update={"preferences": CodingPreferences(limits={"active_seconds": 30})})
    task = _queued(store, (prepared[0], prepared[1], brief))
    lease = store.claim_next("first")
    clock[0] += 12
    store.control("owner-a", task["task_id"], "pause")
    _error("PAUSED", store.guard, lease)
    restarted = CodingStore(store.db_path, store.operator_limits, clock=store.clock)
    restarted.control("owner-a", task["task_id"], "resume")
    lease = restarted.claim_next("second")
    clock[0] += 18
    _error("BUDGET_EXHAUSTED", restarted.guard, lease)
    task = restarted.get_task("owner-a", task["task_id"])
    assert task["limits"]["active_seconds"] == task["counters"]["active_seconds"] == 30


def test_user_allowance_does_not_override_the_operator_daily_cap(tmp_path, prepared, clock):
    store = CodingStore(tmp_path / "operator.db", OperatorLimits(1, 1), clock=lambda: clock[0])
    brief = prepared[2].model_copy(update={"preferences": CodingPreferences(limits={"model_calls": 2})})
    task = _queued(store, (prepared[0], prepared[1], brief))
    lease = store.claim_next("first")
    action = store.reserve_action(lease, "PLAN", brief.source_hash)
    store.finish_action(lease, action["action_id"], {}, next_stage="PLAN", state="QUEUED")
    lease = store.claim_next("second")
    _error("OPERATOR_LIMIT", store.reserve_action, lease, "PLAN", brief.source_hash)
    assert store.get_task("owner-a", task["task_id"])["counters"]["model_calls"] == 1


def test_plan_only_can_save_a_reviewed_plan_but_cannot_start_resume_or_restore_execution(store, prepared):
    brief = prepared[2].model_copy(update={"preferences": CodingPreferences(mode="plan_only")})
    task, plan = _approved(store, (prepared[0], prepared[1], brief))
    assert task["state"] == "APPROVED"
    assert task["approved_plan_hash"] == plan.identity()
    _error("PLAN_ONLY", store.enqueue, "owner-a", task["task_id"], "blocked-start", phase="run")
    for command in ("resume", "retry"):
        _error("PLAN_ONLY", store.control, "owner-a", task["task_id"], command)
    checkpoint = store.list_checkpoints("owner-a", task["task_id"])[-1]
    _error("PLAN_ONLY", store.restore_checkpoint, "owner-a", task["task_id"], checkpoint["checkpoint_id"])
    assert store.get_task("owner-a", task["task_id"])["counters"] == {
        "model_calls": 1, "patch_attempts": 0, "executions": 0, "active_seconds": 0,
    }


@pytest.mark.parametrize("stage,kind", [("BASELINE", "EXECUTION"), ("EDIT", "EDIT")])
def test_plan_only_store_rejects_action_even_if_an_execution_stage_is_queued(store, prepared, stage, kind):
    brief = prepared[2].model_copy(update={"preferences": CodingPreferences(mode="plan_only")})
    task, plan = _approved(store, (prepared[0], prepared[1], brief))
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("UPDATE coding_tasks SET state='QUEUED',next_stage=? WHERE task_id=?",
                           (stage, task["task_id"]))
    lease = store.claim_next("defense-test")
    _error("PLAN_ONLY", store.reserve_action, lease, kind, brief.source_hash, plan.identity())
    task = store.get_task("owner-a", task["task_id"])
    assert task["counters"]["patch_attempts"] == task["counters"]["executions"] == 0


def test_plan_only_can_pause_and_resume_planning_before_any_implementation(store, prepared):
    brief = prepared[2].model_copy(update={"preferences": CodingPreferences(mode="plan_only")})
    task = _queued(store, (prepared[0], prepared[1], brief))
    store.control("owner-a", task["task_id"], "pause")
    assert store.control("owner-a", task["task_id"], "resume")["next_stage"] == "PLAN"
    lease = store.claim_next("planner")
    assert store.reserve_action(lease, "PLAN", brief.source_hash)["kind"] == "PLAN"


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
