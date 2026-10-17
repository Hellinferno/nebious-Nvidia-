"""Tests for checkpoints, checkpoint restore, bundle export, and durability controls (C-06).

Acceptance gates verified:
1. Checkpoint history is immutable and append-only across task lifecycle stages.
2. Checkpoint restore rolls back task state and checkpoint via CAS check without budget reset.
3. Restored task in PAUSED state can be safely resumed and continued by the worker.
4. Export bundle provides complete sanitized JSON and ZIP archives without credentials or internal secrets.
5. In-flight and active-running guards prevent restore during concurrent execution.
6. Worker crash / interruption preserves monotonic usage and requires explicit retry for uncertain actions.
7. Cancelled container termination reconciles cleanly through reconcile_execution.
"""

from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from benchproof.api import coding as coding_api
from benchproof.api import main as api_main
from benchproof.coding.contracts import (
    CodingBrief,
    CodingPlan,
    CodingStoreError,
    OperatorLimits,
)
from benchproof.coding.store import CodingStore
from benchproof.fixtures import source_hash, source_hash_for_dir
from benchproof.providers import NebiusAdapter


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    app = root / "sample" / "app"
    app.mkdir(parents=True)
    (app / "core.py").write_bytes(b"VALUE = 1\r\n")
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(root))
    source = {"app/core.py": "VALUE = 1\r\n"}
    brief = CodingBrief(
        task="Change VALUE to two",
        source_hash=source_hash_for_dir(app),
        editable_paths=["app/core.py"],
    )
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
    return CodingPlan(
        source_hash=brief.source_hash,
        brief_hash=brief.identity(),
        steps=["Change the constant"],
        target_files=brief.editable_paths,
    )


def _approved(store, prepared):
    task = _queued(store, prepared)
    lease = store.claim_next("planner")
    action = store.reserve_action(lease, "PLAN", prepared[2].source_hash)
    plan = _plan(prepared[2])
    task = store.finish_action(
        lease,
        action["action_id"],
        {"plan": plan.model_dump()},
        usage={"total_tokens": 10},
        state="AWAITING_APPROVAL",
        next_stage="BASELINE",
        checkpoint={"plan": plan.model_dump()},
    )
    task = store.approve_plan("owner-a", task["task_id"], plan.identity())
    return task, plan


# ==============================================================================
# 1. Store-level Checkpoint History & Restore
# ==============================================================================


def test_checkpoints_created_during_task_lifecycle(store, prepared, clock):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]

    # 1. Approval created the initial baseline checkpoint (seq 1)
    chks = store.list_checkpoints("owner-a", task_id)
    assert len(chks) == 1
    assert chks[0]["sequence"] == 1
    assert chks[0]["stage"] == "BASELINE"
    assert chks[0]["state"] == "APPROVED"
    assert chks[0]["checkpoint"] == {}

    # 2. Worker runs BASELINE
    task = store.enqueue("owner-a", task_id, "run", phase="run")
    lease = store.claim_next("worker-1")
    action_base = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan_hash=plan.identity())
    clock[0] += 2.0
    task = store.finish_action(
        lease,
        action_base["action_id"],
        {"report": {"verdict": "REJECTED", "failures": ["AssertionError: VALUE != 2"]}},
        next_stage="EDIT",
        checkpoint={"baseline": {"verdict": "REJECTED"}},
    )

    chks = store.list_checkpoints("owner-a", task_id)
    assert len(chks) == 2
    assert chks[1]["sequence"] == 2
    assert chks[1]["stage"] == "EDIT"
    assert chks[1]["checkpoint"]["baseline"]["verdict"] == "REJECTED"

    # 3. Worker runs EDIT (lease is retained across sequential actions within the job)
    action_edit = store.reserve_action(lease, "EDIT", prepared[2].source_hash, plan_hash=plan.identity())
    clock[0] += 3.0
    fake_patch = {
        "diff": "--- a/app/core.py\n+++ b/app/core.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n",
        "author": "synthetic-model",
        "target_files": ["app/core.py"],
    }
    candidate_hash = "f" * 64
    task = store.finish_action(
        lease,
        action_edit["action_id"],
        {"patch": fake_patch, "candidate_hash": candidate_hash},
        next_stage="CANDIDATE",
        checkpoint={
            "baseline": {"verdict": "REJECTED"},
            "patch": fake_patch,
            "candidate_hash": candidate_hash,
            "candidate_hashes": [candidate_hash],
        },
    )

    chks = store.list_checkpoints("owner-a", task_id)
    assert len(chks) == 3
    assert chks[2]["sequence"] == 3
    assert chks[2]["stage"] == "CANDIDATE"
    assert chks[2]["checkpoint"]["candidate_hash"] == candidate_hash

    # Single checkpoint lookup
    single = store.get_checkpoint("owner-a", task_id, chks[2]["checkpoint_id"])
    assert single["checkpoint_id"] == chks[2]["checkpoint_id"]
    assert single["sequence"] == 3

    # Unknown checkpoint raises NOT_FOUND
    with pytest.raises(CodingStoreError) as exc:
        store.get_checkpoint("owner-a", task_id, "chk-nonexistent")
    assert exc.value.code == "NOT_FOUND"

    # Owner isolation
    with pytest.raises(CodingStoreError) as exc:
        store.list_checkpoints("other-owner", task_id)
    assert exc.value.code == "NOT_FOUND"


def test_checkpoint_restore_rolls_back_state_and_preserves_budgets(store, prepared, clock):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]

    # Run baseline
    task = store.enqueue("owner-a", task_id, "run", phase="run")
    lease = store.claim_next("worker-1")
    action_base = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan_hash=plan.identity())
    clock[0] += 2.0
    store.finish_action(
        lease,
        action_base["action_id"],
        {"report": {"verdict": "REJECTED"}},
        next_stage="EDIT",
        checkpoint={"baseline": {"verdict": "REJECTED"}},
    )

    # Run edit
    action_edit = store.reserve_action(lease, "EDIT", prepared[2].source_hash, plan_hash=plan.identity())
    clock[0] += 3.0
    fake_patch = {"diff": "+VALUE=2", "author": "model", "target_files": ["app/core.py"]}
    store.finish_action(
        lease,
        action_edit["action_id"],
        {"patch": fake_patch},
        next_stage="CANDIDATE",
        checkpoint={"baseline": {"verdict": "REJECTED"}, "patch": fake_patch, "candidate_hash": "a" * 64},
        state="PAUSED",  # Task paused after edit
    )

    task = store.get_task("owner-a", task_id)
    assert task["counters"]["model_calls"] == 2  # 1 PLAN + 1 EDIT
    assert task["counters"]["patch_attempts"] == 1
    assert task["counters"]["executions"] == 1
    assert task["counters"]["active_seconds"] == 5.0
    assert task["next_stage"] == "CANDIDATE"

    chks = store.list_checkpoints("owner-a", task_id)
    assert len(chks) == 3
    chk_after_baseline = chks[1]  # sequence 2: stage EDIT, baseline only

    # Restore to checkpoint 2 (after baseline, before edit)
    restored = store.restore_checkpoint("owner-a", task_id, chk_after_baseline["checkpoint_id"])

    assert restored["state"] == "PAUSED"
    assert restored["next_stage"] == "EDIT"
    assert "patch" not in (restored["checkpoint"] or {})
    assert restored["checkpoint"]["baseline"]["verdict"] == "REJECTED"

    # CRITICAL: Monotonic counters must NOT be reset on restore
    assert restored["counters"]["model_calls"] == 2  # preserved monotonically!
    assert restored["counters"]["patch_attempts"] == 1
    assert restored["counters"]["executions"] == 1
    assert restored["counters"]["active_seconds"] == 5.0

    # New checkpoint was appended recording the restore (seq 4)
    all_chks = store.list_checkpoints("owner-a", task_id)
    assert len(all_chks) == 4
    assert all_chks[3]["sequence"] == 4
    assert all_chks[3]["stage"] == "EDIT"
    assert all_chks[3]["state"] == "PAUSED"

    # Event logged
    events = store.list_events("owner-a", task_id)
    restore_events = [e for e in events if e["event_type"] == "CHECKPOINT_RESTORED"]
    assert len(restore_events) == 1
    assert restore_events[0]["payload"]["restored_from"] == chk_after_baseline["checkpoint_id"]


def test_checkpoint_restore_cas_conflict(store, prepared):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]

    chks = store.list_checkpoints("owner-a", task_id)
    target_chk = chks[0]["checkpoint_id"]

    # Fails when expected_checkpoint_id does not match latest
    with pytest.raises(CodingStoreError) as exc:
        store.restore_checkpoint(
            "owner-a", task_id, target_chk, expected_checkpoint_id="chk-wrong-latest"
        )
    assert exc.value.code == "CONFLICT"

    # Succeeds with matching expected_checkpoint_id
    restored = store.restore_checkpoint(
        "owner-a", task_id, target_chk, expected_checkpoint_id=target_chk
    )
    assert restored["state"] == "PAUSED"


def test_checkpoint_restore_rejected_when_running_or_in_flight(store, prepared):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]
    task = store.enqueue("owner-a", task_id, "run", phase="run")
    lease = store.claim_next("worker-1")

    chks = store.list_checkpoints("owner-a", task_id)
    target_chk = chks[0]["checkpoint_id"]

    # 1. Rejected while task is actively leased & running
    with pytest.raises(CodingStoreError) as exc:
        store.restore_checkpoint("owner-a", task_id, target_chk)
    assert exc.value.code == "INVALID_STATE"

    # 2. Rejected when an action is reserved & in-flight
    store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan_hash=plan.identity())
    with pytest.raises(CodingStoreError) as exc:
        store.restore_checkpoint("owner-a", task_id, target_chk)
    assert exc.value.code in {"INVALID_STATE", "ACTION_IN_FLIGHT"}


def test_resume_after_restore_continues_execution(store, prepared):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]

    # Run baseline and edit
    task = store.enqueue("owner-a", task_id, "run", phase="run")
    lease = store.claim_next("worker-1")
    action_base = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan_hash=plan.identity())
    store.finish_action(
        lease, action_base["action_id"], {"report": {"verdict": "REJECTED"}},
        next_stage="EDIT", checkpoint={"baseline": {"verdict": "REJECTED"}},
    )

    action_edit = store.reserve_action(lease, "EDIT", prepared[2].source_hash, plan_hash=plan.identity())
    store.finish_action(
        lease, action_edit["action_id"], {"patch": {"diff": "+v1"}},
        next_stage="CANDIDATE", checkpoint={"patch": {"diff": "+v1"}}, state="PAUSED",
    )

    chks = store.list_checkpoints("owner-a", task_id)
    # Restore to baseline
    store.restore_checkpoint("owner-a", task_id, chks[1]["checkpoint_id"])

    # Resume the task
    resumed = store.control("owner-a", task_id, "resume")
    assert resumed["state"] == "QUEUED"
    assert resumed["next_stage"] == "EDIT"

    # Worker claims task and continues EDIT
    lease2 = store.claim_next("worker-2")
    assert lease2 is not None
    action_edit2 = store.reserve_action(lease2, "EDIT", prepared[2].source_hash, plan_hash=plan.identity())
    assert action_edit2["stage"] == "EDIT"


# ==============================================================================
# 2. Sanitized Task Export Bundle (JSON & ZIP)
# ==============================================================================


def test_export_bundle_json_and_zip(store, prepared):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]

    # Run baseline and edit
    task = store.enqueue("owner-a", task_id, "run", phase="run")
    lease = store.claim_next("worker-1")
    action_base = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan_hash=plan.identity())
    store.finish_action(
        lease, action_base["action_id"], {"report": {"verdict": "REJECTED"}},
        next_stage="EDIT", checkpoint={"baseline": {"verdict": "REJECTED"}},
    )

    fake_diff = "--- a/app/core.py\n+++ b/app/core.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n"
    action_edit = store.reserve_action(lease, "EDIT", prepared[2].source_hash, plan_hash=plan.identity())
    store.finish_action(
        lease, action_edit["action_id"],
        {"patch": {"diff": fake_diff, "author": "model", "target_files": ["app/core.py"]}},
        next_stage="CANDIDATE",
        checkpoint={
            "baseline": {"verdict": "REJECTED"},
            "patch": {"diff": fake_diff, "author": "model", "target_files": ["app/core.py"]},
            "candidate_hash": "c" * 64,
        },
        state="REVIEW_READY",
    )

    # 1. JSON Bundle
    bundle = store.export_bundle("owner-a", task_id)
    assert bundle["schema_version"] == "coding-bundle-v1"
    assert bundle["task_id"] == task_id
    assert bundle["fixture_id"] == "sample"
    assert bundle["state"] == "REVIEW_READY"
    assert bundle["brief"]["task"] == "Change VALUE to two"
    assert bundle["plan"]["steps"] == ["Change the constant"]
    assert bundle["patch"]["diff"] == fake_diff
    assert bundle["patch"]["author"] == "model"
    assert bundle["test_reports"]["baseline"]["verdict"] == "REJECTED"
    assert bundle["counters"]["model_calls"] == 2  # 1 PLAN + 1 EDIT
    assert bundle["counters"]["executions"] == 1
    assert bundle["source_manifest"]["file_count"] == 1
    assert len(bundle["events"]) > 0

    # Ensure no secrets in bundle
    bundle_str = json.dumps(bundle)
    assert "BENCHPROOF_FIXTURES_DIR" not in bundle_str
    assert "token" not in bundle_str.lower() or "total_tokens" in bundle_str
    assert "api_key" not in bundle_str

    # 2. ZIP Bundle
    zip_bytes = store.export_bundle_zip("owner-a", task_id)
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "patch.diff" in names
        assert "plan.json" in names
        assert "test_reports.json" in names
        assert "events.json" in names
        assert "summary.md" in names

        diff_content = zf.read("patch.diff").decode("utf-8")
        assert diff_content == fake_diff

        summary_md = zf.read("summary.md").decode("utf-8")
        assert f"# Task Export: {task_id}" in summary_md
        assert "Change VALUE to two" in summary_md


# ==============================================================================
# 3. HTTP API Endpoints for Checkpoints, Restore, and Bundle
# ==============================================================================


@pytest.fixture
def enabled_client(client, monkeypatch):
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
    monkeypatch.setattr(
        api_main.app.state,
        "runner",
        {
            "mode": "docker",
            "isolated_execution_available": True,
            "detail": "synthetic cached readiness; no Docker operation",
        },
    )

    def forbidden_provider(*args, **kwargs):
        raise AssertionError("HTTP coding handlers must not construct a provider")

    monkeypatch.setattr(NebiusAdapter, "__init__", forbidden_provider)
    return client


def test_api_checkpoints_restore_and_bundle(enabled_client):
    base_url = "/api/v1/coding-tasks"

    # Create task (client sends X-BenchProof-Owner: test-owner)
    payload = {
        "fixture_id": "MC-01",
        "task": "Fix money rounding",
        "source_hash": source_hash("MC-01"),
        "editable_paths": ["app/money.py"],
    }
    resp = enabled_client.post(base_url, json=payload, headers={"Idempotency-Key": "c06-create"})
    assert resp.status_code == 201
    task = resp.json()
    task_id = task["task_id"]

    # Plan and approve
    resp = enabled_client.post(f"{base_url}/{task_id}/plan", json={}, headers={"Idempotency-Key": "c06-plan"})
    assert resp.status_code == 202

    db_store = CodingStore(
        Path(api_main.settings.database_path), api_main.coding_runtime_config().operator_limits()
    )
    lease = db_store.claim_next("synthetic-planner")
    brief = CodingBrief.model_validate(task["brief"])
    action = db_store.reserve_action(lease, "PLAN", brief.source_hash)
    plan = CodingPlan(
        source_hash=brief.source_hash,
        brief_hash=brief.identity(),
        target_files=brief.editable_paths,
        steps=["Step 1"],
    )
    db_store.finish_action(
        lease,
        action["action_id"],
        {"plan": plan.model_dump()},
        next_stage="BASELINE",
        state="AWAITING_APPROVAL",
    )

    resp = enabled_client.post(f"{base_url}/{task_id}/approve", json={"plan_hash": plan.identity()})
    assert resp.status_code == 200

    # 1. GET /checkpoints
    resp = enabled_client.get(f"{base_url}/{task_id}/checkpoints")
    assert resp.status_code == 200
    chks = resp.json()
    assert len(chks) == 1
    assert chks[0]["stage"] == "BASELINE"
    chk1_id = chks[0]["checkpoint_id"]

    # Simulate baseline execution finished
    task_rec = db_store.enqueue("test-owner", task_id, "run", phase="run")
    lease = db_store.claim_next("worker-exec")
    action_exec = db_store.reserve_action(lease, "EXECUTION", brief.source_hash, plan_hash=plan.identity())
    db_store.finish_action(
        lease,
        action_exec["action_id"],
        {"report": {"verdict": "REJECTED"}},
        next_stage="EDIT",
        checkpoint={"baseline": {"verdict": "REJECTED"}},
        state="PAUSED",
    )

    resp = enabled_client.get(f"{base_url}/{task_id}/checkpoints")
    assert resp.status_code == 200
    chks = resp.json()
    assert len(chks) == 2
    chk2_id = chks[1]["checkpoint_id"]

    # 2. POST /restore with conflict
    resp = enabled_client.post(
        f"{base_url}/{task_id}/restore",
        json={"checkpoint_id": chk1_id, "expected_checkpoint_id": "chk-mismatched"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CONFLICT"

    # POST /restore with matching CAS
    resp = enabled_client.post(
        f"{base_url}/{task_id}/restore",
        json={"checkpoint_id": chk1_id, "expected_checkpoint_id": chk2_id},
    )
    assert resp.status_code == 200
    restored = resp.json()
    assert restored["state"] == "PAUSED"
    assert restored["next_stage"] == "BASELINE"

    # 3. GET /bundle (JSON)
    resp = enabled_client.get(f"{base_url}/{task_id}/bundle")
    assert resp.status_code == 200
    bundle_data = resp.json()
    assert bundle_data["schema_version"] == "coding-bundle-v1"
    assert bundle_data["task_id"] == task_id

    # 4. GET /bundle?format=zip (ZIP file download)
    resp = enabled_client.get(f"{base_url}/{task_id}/bundle?format=zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment;" in resp.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        assert "manifest.json" in zf.namelist()
        assert "summary.md" in zf.namelist()


# ==============================================================================
# 4. Durability Controls: Interruption, Uncertain Actions, and Container Reconciliation
# ==============================================================================


def test_interrupted_model_action_requires_explicit_retry(store, prepared, clock):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]

    task = store.enqueue("owner-a", task_id, "run", phase="run")
    lease = store.claim_next("worker-1", lease_seconds=10.0)

    # BASELINE action runs and finishes to reach EDIT stage
    action_base = store.reserve_action(lease, "EXECUTION", prepared[2].source_hash, plan_hash=plan.identity())
    store.finish_action(
        lease, action_base["action_id"], {"report": {"verdict": "REJECTED"}},
        next_stage="EDIT", checkpoint={"baseline": {"verdict": "REJECTED"}},
    )

    # Model EDIT action reserved
    action = store.reserve_action(lease, "EDIT", prepared[2].source_hash, plan_hash=plan.identity())

    # Worker crashes: lease expires
    clock[0] += 20.0
    store.reconcile()

    task = store.get_task("owner-a", task_id)
    assert task["state"] == "INTERRUPTED"
    actions = task["actions"]
    assert actions[-1]["status"] == "UNKNOWN"

    # Normal resume fails because uncertain action requires confirmation
    with pytest.raises(CodingStoreError) as exc:
        store.control("owner-a", task_id, "resume")
    assert exc.value.code == "RECONCILIATION_REQUIRED"

    # Explicit retry acknowledges uncertain action and safely returns task to QUEUED
    resumed = store.control("owner-a", task_id, "retry")
    assert resumed["state"] == "QUEUED"

    # Action status updated
    task = store.get_task("owner-a", task_id)
    assert task["actions"][-1]["status"] == "RETRY_ACKNOWLEDGED"

    # Monotonic counters not reset
    assert task["counters"]["model_calls"] == 2  # 1 PLAN + 1 EDIT


def test_cancelled_container_reconciles_via_reconcile_execution(store, prepared):
    task, plan = _approved(store, prepared)
    task_id = task["task_id"]

    task = store.enqueue("owner-a", task_id, "run", phase="run")
    lease = store.claim_next("worker-1")

    # Reserve EXECUTION with container operation ID
    op_id = "docker-run-12345"
    action = store.reserve_action(
        lease,
        "EXECUTION",
        prepared[2].source_hash,
        plan_hash=plan.identity(),
        details={"operation_id": op_id},
    )

    # User requests cancel while container is running
    task = store.control("owner-a", task_id, "cancel")
    assert task["state"] == "CANCEL_PENDING"

    # Pending executions list contains the container operation
    pending = store.pending_executions()
    assert len(pending) == 1
    assert pending[0]["operation_id"] == op_id

    # Container stops: runner reconciles execution
    reconciled = store.reconcile_execution(task_id, op_id, stopped=True)
    assert reconciled["state"] == "CANCELLED"

    # Pending list now empty
    assert len(store.pending_executions()) == 0
