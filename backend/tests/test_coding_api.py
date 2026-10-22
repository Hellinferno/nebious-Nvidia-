"""Coding-task HTTP controls stay owner-scoped, bounded and inference-free."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from benchproof.api import coding as coding_api
from benchproof.api import main as api_main
from benchproof.coding.generation import CodingBrief, CodingPlan
from benchproof.coding.prompts import coding_runtime_identity, generation_policy
from benchproof.coding.store import CodingStore
from benchproof.fixtures import source_hash
from benchproof.providers import NebiusAdapter

BASE = "/api/v1/coding-tasks"


@pytest.fixture
def coding_client(client, monkeypatch):
    settings = api_main.settings
    for name, value in {
        "benchproof_coding_enabled": False,
        "benchproof_coding_model_calls_per_day": 0,
        "benchproof_coding_executions_per_day": 0,
        "benchproof_coding_max_tasks": 100,
        "benchproof_coding_deadline_epoch": 0,
        "benchproof_coding_output_tokens": 2_048,
    }.items():
        monkeypatch.setattr(settings, name, value)

    def forbidden_provider(*args, **kwargs):
        raise AssertionError("HTTP coding handlers must not construct a provider")

    monkeypatch.setattr(NebiusAdapter, "__init__", forbidden_provider)
    return client


@pytest.fixture
def enabled_client(coding_client, monkeypatch):
    settings = api_main.settings
    for name, value in {
        "benchproof_coding_enabled": True,
        "benchproof_coding_model_calls_per_day": 20,
        "benchproof_coding_executions_per_day": 20,
        "benchproof_coding_deadline_epoch": time.time() + 3_600,
        "nebius_api_key": "synthetic-test-key-not-real",
        "nebius_model_id": "synthetic/test-model",
    }.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(api_main.app.state, "runner", {
        "mode": "docker", "isolated_execution_available": True,
        "detail": "synthetic cached readiness; no Docker operation",
    })
    return coding_client


def payload(**updates):
    value = {
        "fixture_id": "MC-01", "task": "Repair invoice rounding without changing its contract",
        "source_hash": source_hash("MC-01"), "editable_paths": ["app/money.py"],
    }
    value.update(updates)
    return value


def create(client, key="create-one", **updates):
    response = client.post(BASE, json=payload(**updates), headers={"Idempotency-Key": key})
    assert response.status_code == 201, response.text
    return response.json()


def records():
    return CodingStore(
        Path(api_main.settings.database_path), api_main.coding_runtime_config().operator_limits(),
    )


def await_plan(client, task):
    task_id = task["task_id"]
    response = client.post(f"{BASE}/{task_id}/plan", json={}, headers={"Idempotency-Key": "plan-one"})
    assert response.status_code == 202, response.text
    store = records()
    lease = store.claim_next("synthetic-api-planner")
    brief = CodingBrief.model_validate(task["brief"])
    action = store.reserve_action(lease, "PLAN", brief.source_hash)
    plan = CodingPlan(
        source_hash=brief.source_hash, brief_hash=brief.identity(),
        target_files=brief.editable_paths, steps=["Make the scoped rounding repair"],
    )
    store.finish_action(
        lease, action["action_id"], {"plan": plan.model_dump(), "mode": "synthetic-test-only"},
        usage={"mode": "synthetic-test-only", "usage": {"total_tokens": 17}},
        next_stage="BASELINE", checkpoint={}, state="AWAITING_APPROVAL",
    )
    return plan


def approve(client, task, plan):
    response = client.post(f"{BASE}/{task['task_id']}/approve", json={"plan_hash": plan.identity()})
    assert response.status_code == 200, response.text
    return response.json()


def test_disabled_default_cannot_create_or_infer(coding_client):
    response = coding_client.post(BASE, json=payload(), headers={"Idempotency-Key": "disabled"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "CODING_DISABLED"
    assert coding_client.get(BASE).json() == []
    coding = coding_client.get("/api/v1/ready").json()["coding"]
    assert coding["enabled"] is False
    assert coding["admission_configured"] is False
    assert coding["worker_alive"] is False


def test_owner_header_is_required_and_validated(coding_client):
    coding_client.headers.pop("X-BenchProof-Owner")
    response = coding_client.get(BASE)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "OWNER_REQUIRED"
    assert coding_client.get(BASE, headers={"X-BenchProof-Owner": "invalid/owner"}).status_code == 400


def test_create_replay_conflict_and_server_runtime_pin(enabled_client):
    task = create(enabled_client)
    replay = create(enabled_client)
    assert replay["task_id"] == task["task_id"]
    assert task["state"] == "DRAFT"
    assert task["counters"]["model_calls"] == task["counters"]["executions"] == 0
    assert task["runtime_config"]["model_id"] == "synthetic/test-model"
    assert task["runtime_config"]["max_output_tokens"] == 2_048
    assert task["runtime_config"]["generation_policy"] == generation_policy()
    conflict = enabled_client.post(
        BASE, json=payload(task="A different request"), headers={"Idempotency-Key": "create-one"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert len(enabled_client.get(BASE).json()) == 1


def test_task_preferences_roundtrip_without_changing_runtime_or_limits(enabled_client):
    legacy = create(enabled_client, key="legacy-preferences")
    assert "preferences" not in legacy["brief"]
    assert create(enabled_client, key="legacy-preferences", preferences=None)["task_id"] == legacy["task_id"]
    preferences = {"workflow": "refactor", "instructions": "Preserve the public API"}
    task = create(enabled_client, key="preferences", preferences=preferences)
    assert task["brief"]["preferences"] == preferences
    assert task["runtime_config"] == legacy["runtime_config"]
    assert task["limits"] == legacy["limits"]
    assert create(enabled_client, key="preferences", preferences=preferences)["task_id"] == task["task_id"]
    exported = enabled_client.get(f"{BASE}/{task['task_id']}/bundle").json()
    assert exported["brief"]["preferences"] == preferences
    conflict = enabled_client.post(BASE, json=payload(
        preferences={**preferences, "instructions": "Use a different style"},
    ), headers={"Idempotency-Key": "preferences"})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_custom_task_budget_roundtrip_and_default_controls_remain_idempotent(enabled_client):
    legacy = create(enabled_client, key="previous-controls", preferences={"workflow": "feature"})
    replay = create(enabled_client, key="previous-controls", preferences={
        "workflow": "feature", "mode": "implement", "limits": {
            "model_calls": 4, "patch_attempts": 2, "executions": 4, "active_seconds": 300,
        },
    })
    assert replay["task_id"] == legacy["task_id"]
    custom = create(enabled_client, key="lowered-controls", preferences={
        "workflow": "bugfix", "limits": {"model_calls": 2, "active_seconds": 60},
    })
    assert custom["limits"] == {"model_calls": 2, "patch_attempts": 2, "executions": 4, "active_seconds": 60}
    assert custom["runtime_config"] == legacy["runtime_config"]
    assert custom["brief"]["preferences"]["limits"] == {"model_calls": 2, "active_seconds": 60}


def test_plan_only_api_allows_review_but_rejects_start_resume_and_execution_restore(enabled_client):
    task = create(enabled_client, key="plan-only", preferences={"mode": "plan_only"})
    plan = await_plan(enabled_client, task)
    reviewed = approve(enabled_client, task, plan)
    assert reviewed["state"] == "APPROVED"
    task_id = task["task_id"]
    for operation in ("start", "resume"):
        response = enabled_client.post(
            f"{BASE}/{task_id}/{operation}", json={}, headers={"Idempotency-Key": f"deny-{operation}"},
        )
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "PLAN_ONLY"
    checkpoint = records().list_checkpoints("test-owner", task_id)[-1]
    response = enabled_client.post(f"{BASE}/{task_id}/restore", json={
        "checkpoint_id": checkpoint["checkpoint_id"],
    })
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "PLAN_ONLY"
    current = enabled_client.get(f"{BASE}/{task_id}").json()
    assert current["counters"]["executions"] == current["counters"]["patch_attempts"] == 0


@pytest.mark.parametrize("preferences", [
    "bugfix", {"workflow": "invalid"}, {"instructions": 4},
    {"instructions": "x" * 2_001}, {"workflow": "custom", "max_tokens": 8_192},
    {"workflow": "feature", "allow_shell": True},
    {"mode": "run_anything"}, {"limits": {"model_calls": 5}},
    {"limits": {"model_calls": True}}, {"limits": {"patch_attempts": 3}},
    {"limits": {"executions": 5}}, {"limits": {"active_seconds": 29}},
    {"limits": {"active_seconds": 301}}, {"limits": {"allow_network": True}},
])
def test_task_preferences_are_strict_bounded_and_cannot_change_controls(enabled_client, preferences):
    response = enabled_client.post(
        BASE, json=payload(preferences=preferences), headers={"Idempotency-Key": "invalid-preferences"},
    )
    assert response.status_code == 422
    assert enabled_client.get(BASE).json() == []


@pytest.mark.parametrize("key", [None, "invalid key", "x" * 129])
def test_creation_requires_a_bounded_idempotency_key(enabled_client, key):
    headers = {} if key is None else {"Idempotency-Key": key}
    response = enabled_client.post(BASE, json=payload(), headers=headers)
    assert response.status_code == 400
    assert enabled_client.get(BASE).json() == []


@pytest.mark.parametrize("updates", [
    {"api_key": "not-accepted"}, {"model_id": "not-client-selected"},
    {"fixture_id": "../private"}, {"editable_paths": "app/money.py"},
    {"editable_paths": ["app/../private.py"]},
    {"editable_paths": ["app/tests/test_money.py"]},
    {"task": 5}, {"source_hash": "invalid"},
])
def test_create_strict_schema_and_protected_scope(enabled_client, updates):
    response = enabled_client.post(BASE, json=payload(**updates), headers={"Idempotency-Key": "invalid"})
    assert response.status_code == 422
    assert enabled_client.get(BASE).json() == []


def test_unknown_fixture_and_stale_source_are_rejected(enabled_client):
    missing = enabled_client.post(
        BASE, json=payload(fixture_id="missing-example"), headers={"Idempotency-Key": "missing"},
    )
    assert missing.status_code == 404
    stale = enabled_client.post(
        BASE, json=payload(source_hash="0" * 64), headers={"Idempotency-Key": "stale"},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "STALE_SOURCE"
    assert enabled_client.get(BASE).json() == []


@pytest.mark.parametrize("setting,value,code", [
    ("benchproof_coding_model_calls_per_day", 0, "OPERATOR_LIMIT"),
    ("benchproof_coding_executions_per_day", 0, "OPERATOR_LIMIT"),
    ("benchproof_coding_deadline_epoch", 1, "SESSION_WINDOW_INSUFFICIENT"),
    ("nebius_api_key", "", "PROVIDER_UNAVAILABLE"),
])
def test_live_admission_fails_closed_without_spending(enabled_client, monkeypatch, setting, value, code):
    monkeypatch.setattr(api_main.settings, setting, value)
    response = enabled_client.post(BASE, json=payload(), headers={"Idempotency-Key": "blocked"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == code
    assert enabled_client.get(BASE).json() == []


def test_runner_admission_uses_cached_readiness_and_refuses_unavailable(enabled_client, monkeypatch):
    monkeypatch.setattr(api_main.app.state, "runner", {"isolated_execution_available": False})
    response = enabled_client.post(BASE, json=payload(), headers={"Idempotency-Key": "runner"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RUNNER_UNAVAILABLE"


def test_plan_enqueue_replay_is_short_and_does_not_reserve_a_paid_call(enabled_client):
    task = create(enabled_client)
    route = f"{BASE}/{task['task_id']}/plan"
    first = enabled_client.post(route, json={}, headers={"Idempotency-Key": "plan"})
    second = enabled_client.post(route, json={}, headers={"Idempotency-Key": "plan"})
    assert first.status_code == second.status_code == 202
    assert first.json()["task_id"] == second.json()["task_id"]
    persisted = records().get_task("test-owner", task["task_id"])
    assert persisted["state"] == "QUEUED"
    assert persisted["actions"] == []
    assert persisted["counters"]["model_calls"] == 0
    events = enabled_client.get(f"{BASE}/{task['task_id']}/events").json()
    assert sum(event["event_type"] == "TASK_QUEUED" for event in events) == 1


def test_another_task_cannot_enter_the_single_active_slot(enabled_client):
    first = create(enabled_client)
    second = create(enabled_client, key="create-two")
    assert enabled_client.post(
        f"{BASE}/{first['task_id']}/plan", headers={"Idempotency-Key": "first-plan"},
    ).status_code == 202
    busy = enabled_client.post(
        f"{BASE}/{second['task_id']}/plan", headers={"Idempotency-Key": "second-plan"},
    )
    assert busy.status_code == 429
    assert busy.json()["detail"]["code"] == "BUSY"
    assert records().get_task("test-owner", second["task_id"])["actions"] == []


@pytest.mark.parametrize("operation", ["plan", "start", "pause", "resume", "cancel"])
def test_control_bodies_do_not_accept_hidden_tool_or_budget_arguments(enabled_client, operation):
    task = create(enabled_client)
    response = enabled_client.post(
        f"{BASE}/{task['task_id']}/{operation}", json={"command": "unapproved", "max_calls": 999},
        headers={"Idempotency-Key": "invalid-control"},
    )
    assert response.status_code == 422
    assert records().get_task("test-owner", task["task_id"])["state"] == "DRAFT"


def test_draft_cannot_start_approve_or_install_an_unreviewed_plan(enabled_client):
    task = create(enabled_client)
    task_id = task["task_id"]
    brief = CodingBrief.model_validate(task["brief"])
    plan = CodingPlan(source_hash=brief.source_hash, brief_hash=brief.identity(),
                      target_files=brief.editable_paths, steps=["A proposed change"])
    assert enabled_client.post(
        f"{BASE}/{task_id}/start", headers={"Idempotency-Key": "early-start"},
    ).status_code == 409
    assert enabled_client.post(f"{BASE}/{task_id}/approve", json={"plan_hash": plan.identity()}).status_code == 409
    assert enabled_client.post(f"{BASE}/{task_id}/plan/edit", json=plan.model_dump()).status_code == 409


def test_exact_plan_approval_and_edits_invalidate_previous_approval(enabled_client):
    task = create(enabled_client)
    plan = await_plan(enabled_client, task)
    task_id = task["task_id"]
    described = enabled_client.get(f"{BASE}/{task_id}/plan").json()
    assert described["plan_hash"] == plan.identity()
    assert described["approved_plan_hash"] is None
    stale = enabled_client.post(f"{BASE}/{task_id}/approve", json={"plan_hash": "0" * 64})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "STALE_PLAN"
    assert approve(enabled_client, task, plan)["state"] == "APPROVED"
    revised = plan.model_copy(update={"steps": ["A reviewed alternative step"]})
    response = enabled_client.post(f"{BASE}/{task_id}/plan/edit", json=revised.model_dump())
    assert response.status_code == 200
    assert response.json()["approved_plan_hash"] is None
    assert enabled_client.post(
        f"{BASE}/{task_id}/start", headers={"Idempotency-Key": "stale-start"},
    ).status_code == 409
    assert enabled_client.post(f"{BASE}/{task_id}/approve", json={"plan_hash": plan.identity()}).status_code == 409
    assert approve(enabled_client, task, revised)["approved_plan_hash"] == revised.identity()


@pytest.mark.parametrize("update", [
    {"source_hash": "0" * 64}, {"brief_hash": "0" * 64}, {"target_files": ["app/worker.py"]},
])
def test_owner_plan_edit_cannot_escape_pinned_source_brief_or_scope(enabled_client, update):
    task = create(enabled_client)
    plan = await_plan(enabled_client, task)
    proposed = plan.model_dump()
    proposed.update(update)
    response = enabled_client.post(f"{BASE}/{task['task_id']}/plan/edit", json=proposed)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PLAN_UNAPPROVED"
    assert enabled_client.get(f"{BASE}/{task['task_id']}/plan").json()["plan_hash"] == plan.identity()


def test_start_replay_does_not_duplicate_execution_or_reset_counters(enabled_client):
    task = create(enabled_client)
    plan = await_plan(enabled_client, task)
    approve(enabled_client, task, plan)
    route = f"{BASE}/{task['task_id']}/start"
    first = enabled_client.post(route, json={}, headers={"Idempotency-Key": "start"})
    second = enabled_client.post(route, json={}, headers={"Idempotency-Key": "start"})
    assert first.status_code == second.status_code == 202
    persisted = records().get_task("test-owner", task["task_id"])
    assert persisted["next_stage"] == "BASELINE"
    assert persisted["counters"]["model_calls"] == 1
    assert persisted["counters"]["executions"] == 0
    assert len(persisted["actions"]) == 1


@pytest.mark.parametrize("phase", ["plan", "start"])
@pytest.mark.parametrize("setting,value", [
    ("nebius_model_id", "synthetic/changed-model"),
    ("benchproof_coding_output_tokens", 4_096),
])
def test_changed_runtime_pin_refuses_enqueue_without_new_spend(
    enabled_client, monkeypatch, phase, setting, value,
):
    task = create(enabled_client)
    if phase == "start":
        plan = await_plan(enabled_client, task)
        approve(enabled_client, task, plan)
    before = records().get_task("test-owner", task["task_id"])
    monkeypatch.setattr(api_main.settings, setting, value)
    response = enabled_client.post(
        f"{BASE}/{task['task_id']}/{phase}", headers={"Idempotency-Key": "changed-runtime"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STALE_RUNTIME"
    after = records().get_task("test-owner", task["task_id"])
    assert after["state"] == before["state"]
    assert after["runtime_config"] == before["runtime_config"]
    assert after["counters"] == before["counters"]
    assert after["actions"] == before["actions"]


@pytest.mark.parametrize("phase", ["plan", "start"])
def test_changed_prompt_policy_refuses_enqueue_without_new_spend(enabled_client, monkeypatch, phase):
    from benchproof.coding import prompts

    task = create(enabled_client)
    if phase == "start":
        plan = await_plan(enabled_client, task)
        approve(enabled_client, task, plan)
    before = records().get_task("test-owner", task["task_id"])
    monkeypatch.setattr(prompts, "EDIT_SYSTEM_PROMPT", prompts.EDIT_SYSTEM_PROMPT + "\nChanged policy.")
    response = enabled_client.post(
        f"{BASE}/{task['task_id']}/{phase}", headers={"Idempotency-Key": "changed-policy"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STALE_RUNTIME"
    after = records().get_task("test-owner", task["task_id"])
    assert after["runtime_config"] == before["runtime_config"]
    assert after["counters"] == before["counters"]
    assert after["actions"] == before["actions"]


def test_bundle_exports_the_task_policy_not_the_current_policy(enabled_client, monkeypatch):
    from benchproof.coding import prompts

    task = create(enabled_client)
    expected = coding_runtime_identity("synthetic/test-model", 2_048)
    monkeypatch.setattr(prompts, "EDIT_SYSTEM_PROMPT", prompts.EDIT_SYSTEM_PROMPT + "\nChanged policy.")
    bundle = enabled_client.get(f"{BASE}/{task['task_id']}/bundle").json()
    assert bundle["runtime_config"] == expected == task["runtime_config"]
    assert bundle["runtime_config"]["generation_policy"] != generation_policy()
    assert bundle["counters"]["model_calls"] == bundle["counters"]["executions"] == 0


def test_bundle_excludes_unrelated_private_runtime_fields(enabled_client):
    task = create(enabled_client)
    runtime = task["runtime_config"]
    runtime["private_config"] = "private-runtime-value"
    runtime["generation_policy"]["private_config"] = "private-policy-value"
    with records()._transaction() as connection:
        connection.execute(
            "UPDATE coding_tasks SET runtime_config_json=? WHERE task_id=?",
            (json.dumps(runtime), task["task_id"]),
        )
    response = enabled_client.get(f"{BASE}/{task['task_id']}/bundle")
    assert response.status_code == 200
    assert response.json()["runtime_config"] == coding_runtime_identity("synthetic/test-model", 2_048)
    assert "private-runtime-value" not in response.text
    assert "private-policy-value" not in response.text


def test_events_source_changes_and_usage_reads_are_non_billing(enabled_client):
    task = create(enabled_client)
    plan = await_plan(enabled_client, task)
    approve(enabled_client, task, plan)
    task_id = task["task_id"]
    before = records().get_task("test-owner", task_id)
    source = enabled_client.get(f"{BASE}/{task_id}/source").json()
    assert source["source_hash"] == task["brief"]["source_hash"]
    assert "app/money.py" in source["files"]
    assert all(path.startswith("app/") for path in source["files"])
    changes = enabled_client.get(f"{BASE}/{task_id}/changes").json()
    assert changes["diff"] == ""
    assert changes["tested_final"] is False
    assert enabled_client.get(f"{BASE}/{task_id}/executions").json() == []
    usage = enabled_client.get(f"{BASE}/{task_id}/usage").json()
    assert usage["recorded_tokens"] == 17
    assert usage["unknown_model_actions"] == 0
    assert usage["monetary_cost"] == "UNKNOWN"
    assert usage["hard_token_cap"] is False
    events = enabled_client.get(f"{BASE}/{task_id}/events").json()
    sequences = [event["sequence"] for event in events]
    assert sequences == sorted(set(sequences))
    cursor = sequences[-2]
    later = enabled_client.get(f"{BASE}/{task_id}/events", params={"after": cursor}).json()
    assert [event["sequence"] for event in later] == [sequence for sequence in sequences if sequence > cursor]
    assert enabled_client.get(f"{BASE}/{task_id}/events", params={"after": sequences[-1]}).json() == []
    assert enabled_client.get(f"{BASE}/{task_id}/events", params={"after": -1}).status_code == 422
    after = records().get_task("test-owner", task_id)
    assert after["counters"] == before["counters"]
    assert after["actions"] == before["actions"]


def test_all_task_routes_reject_another_owner_without_leaking_source(enabled_client):
    task = create(enabled_client)
    plan = await_plan(enabled_client, task)
    task_id = task["task_id"]
    headers = {"X-BenchProof-Owner": "other-owner", "Idempotency-Key": "foreign"}
    assert enabled_client.get(BASE, headers=headers).json() == []
    for suffix in ("", "/source", "/plan", "/events", "/changes", "/executions", "/usage"):
        response = enabled_client.get(f"{BASE}/{task_id}{suffix}", headers=headers)
        assert response.status_code == 404
        assert "compute_total" not in response.text
    for suffix, body in (
        ("plan", {}), ("start", {}), ("approve", {"plan_hash": plan.identity()}),
        ("plan/edit", plan.model_dump()), ("pause", {}), ("resume", {}), ("cancel", {}),
    ):
        response = enabled_client.post(f"{BASE}/{task_id}/{suffix}", json=body, headers=headers)
        assert response.status_code == 404
    assert records().get_task("test-owner", task_id)["state"] == "AWAITING_APPROVAL"


def test_pause_resume_and_cancel_preserve_usage_and_work_without_paid_handlers(enabled_client, monkeypatch):
    task = create(enabled_client)
    plan = await_plan(enabled_client, task)
    approve(enabled_client, task, plan)
    task_id = task["task_id"]
    assert enabled_client.post(
        f"{BASE}/{task_id}/start", headers={"Idempotency-Key": "start"},
    ).status_code == 202
    assert enabled_client.post(f"{BASE}/{task_id}/pause").json()["state"] == "PAUSED"
    assert enabled_client.post(f"{BASE}/{task_id}/pause").status_code == 200
    assert enabled_client.post(f"{BASE}/{task_id}/resume").json()["state"] == "QUEUED"
    monkeypatch.setattr(api_main.settings, "benchproof_coding_enabled", False)
    assert enabled_client.post(f"{BASE}/{task_id}/cancel").json()["state"] == "CANCELLED"
    assert enabled_client.post(f"{BASE}/{task_id}/cancel").status_code == 200
    usage = enabled_client.get(f"{BASE}/{task_id}/usage").json()
    assert usage["counters"]["model_calls"] == 1
    assert usage["recorded_tokens"] == 17
    assert enabled_client.post(f"{BASE}/{task_id}/resume").status_code == 503


def test_cancelled_inflight_model_reservation_remains_unknown_and_charged(enabled_client):
    task = create(enabled_client)
    task_id = task["task_id"]
    assert enabled_client.post(
        f"{BASE}/{task_id}/plan", headers={"Idempotency-Key": "plan"},
    ).status_code == 202
    store = records()
    lease = store.claim_next("synthetic-interrupted-api-planner")
    store.reserve_action(lease, "PLAN", task["brief"]["source_hash"])
    cancelled = enabled_client.post(f"{BASE}/{task_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "CANCELLED"
    usage = enabled_client.get(f"{BASE}/{task_id}/usage").json()
    assert usage["unknown_model_actions"] == 1
    assert usage["recorded_tokens"] == 0
    assert usage["counters"]["model_calls"] == 1
    assert store.get_task("test-owner", task_id)["actions"][-1]["status"] == "UNKNOWN"


def test_body_limit_runs_before_store_and_accepts_exact_limit_json(enabled_client, monkeypatch):
    body = json.dumps(payload()).encode("utf-8")
    exact = body + b" " * (65_536 - len(body))
    response = enabled_client.post(
        BASE, content=exact, headers={"Idempotency-Key": "exact", "Content-Type": "application/json"},
    )
    assert response.status_code == 201, response.text

    def forbidden_store(*args, **kwargs):
        raise AssertionError("Oversized requests must not instantiate the coding store")

    monkeypatch.setattr(coding_api, "CodingStore", forbidden_store)
    rejected = enabled_client.post(
        BASE, content=exact + b" ",
        headers={"Idempotency-Key": "oversized", "Content-Type": "application/json"},
    )
    assert rejected.status_code == 413
    assert rejected.json()["detail"]["code"] == "SOURCE_LIMIT"
    assert "Repair invoice" not in rejected.text
