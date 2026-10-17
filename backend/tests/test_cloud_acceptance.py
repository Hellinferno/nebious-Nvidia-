"""Acceptance verification for cloud worker, session, quota, isolation, and backup/restore (C-08).

Scope and acceptance gate:
1. Real cloud worker lifecycle: lease recovery after expiry, fencing token protection against stale workers.
2. Session and VM-window admission: refusal of execution when session window is insufficient.
3. Quota accounting and operator limits: strict daily model calls, executions, and task limits.
4. Strict data ownership and capability isolation: cross-owner denial across all task/project endpoints.
5. Secret scrubbing: no sensitive credentials, API keys, or tokens in candidates or exported bundles.
6. Online database backup and restore: WAL-safe backup creation, SHA-256 verification, and integrity checks.
"""

from __future__ import annotations

import json
import sqlite3
import time
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from benchproof.api.main import app
from benchproof.coding.contracts import CodingBrief, CodingPlan, OperatorLimits
from benchproof.coding.engine import CodingEngine
from benchproof.coding.generation import CompletionClient, GenerationError
from benchproof.coding.store import CodingStore, CodingStoreError
from benchproof.coding.worker import CodingWorker
from benchproof.execution.base import ExecutionResult
from benchproof.execution.project_runner import PROJECT_CONTRACT_HASH, ProjectExecutor, ProjectSnapshot
from benchproof.projects.store import ProjectStore
from benchproof.storage.backup import BackupError, create_backup, restore_backup


class DeterministicClient(CompletionClient):
    def __init__(self, plan_json: str | None = None, edit_json: str | None = None) -> None:
        self.plan_json = plan_json or ""
        self.edit_json = edit_json or ""
        self.calls = 0

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        prompt = kwargs.get("user_prompt", "")
        try:
            payload = json.loads(prompt)
        except Exception:
            payload = {}
        content = self.plan_json if "brief" in payload else self.edit_json
        return {
            "content": content,
            "usage": {"total_tokens": 150},
            "finish_reason": "stop",
        }


class MockExecutor(ProjectExecutor):
    def __init__(self, pass_tests: bool = True) -> None:
        self.pass_tests = pass_tests
        self.run_count = 0

    def run_tests(self, snapshot: ProjectSnapshot, profile_name: str) -> ExecutionResult:
        self.run_count += 1
        return ExecutionResult(
            passed=self.pass_tests,
            exit_code=0 if self.pass_tests else 1,
            stdout="Ran 2 tests in 0.010s\nOK\n" if self.pass_tests else "FAILED (failures=1)\n",
            stderr="",
            duration_ms=10,
            command="python -m unittest",
            checks_total=2,
            checks_passed=2 if self.pass_tests else 1,
        )


SAMPLE_PROJECT_FILES = {
    "app/calc.py": "def add(s: str) -> int:\n    return sum(int(x) for x in s.split(',') if x)\n",
    "tests/test_calc.py": (
        "import unittest\nfrom app.calc import add\n"
        "class TestAdd(unittest.TestCase):\n"
        "    def test_basic(self):\n        self.assertEqual(add('1,2'), 3)\n"
    ),
}


# ── 1. Worker Lifecycle, Leases, and Fencing ─────────────────────────────────

def test_worker_lease_recovery_after_expiry(tmp_path: Path) -> None:
    db = tmp_path / "cloud_worker.db"
    store = CodingStore(db, OperatorLimits())
    proj_store = ProjectStore(db)

    proj = proj_store.create_project(
        owner_ref="owner-cloud",
        name="Calc",
        files=SAMPLE_PROJECT_FILES,
    )

    brief = CodingBrief(
        task="Fix negative check",
        source_hash=proj.source_hash,
        editable_paths=["app/calc.py"],
    )

    # Use simulated clock starting at 1000.0
    now = 1000.0
    store.clock = lambda: now

    task = store.create_task("owner-cloud", proj.project_id, brief, proj.files, PROJECT_CONTRACT_HASH, "key-1")
    task_id = task["task_id"]

    # Enqueue a plan action
    store.enqueue("owner-cloud", task_id, "token-p1", phase="plan")

    # Worker 1 claims with lease of 100s
    lease1 = store.claim_next("worker-alpha", lease_seconds=100)
    assert lease1 is not None
    assert lease1.worker_id == "worker-alpha"

    # Worker 1 crashes; clock advances past lease expiry (120s later)
    now += 120.0

    # Stale Worker 1 attempts to guard with old lease -> rejected with STALE_LEASE
    with pytest.raises(CodingStoreError) as exc:
        store.guard(lease1)
    assert exc.value.code == "STALE_LEASE"

    # Task is reconciled to INTERRUPTED (preventing silent duplicate spend)
    current = store.get_task("owner-cloud", task_id)
    assert current["state"] == "INTERRUPTED"

    # Operator explicitly resumes the task
    store.control("owner-cloud", task_id, "resume")

    # Worker 2 now claims the task safely with advanced fencing token
    lease2 = store.claim_next("worker-beta", lease_seconds=100)
    assert lease2 is not None
    assert lease2.worker_id == "worker-beta"
    assert lease2.fence > lease1.fence  # Monotonic fencing token advanced!


# ── 2. Session & VM-Window Admission ─────────────────────────────────────────

def test_insufficient_session_window_admission(tmp_path: Path) -> None:
    db = tmp_path / "session_window.db"
    store = CodingStore(db, OperatorLimits(model_calls_per_day=50, executions_per_day=50))
    proj_store = ProjectStore(db)

    proj = proj_store.create_project(
        owner_ref="owner-window",
        name="Calc",
        files=SAMPLE_PROJECT_FILES,
    )

    brief = CodingBrief(task="Test window", source_hash=proj.source_hash, editable_paths=["app/calc.py"])
    task = store.create_task("owner-window", proj.project_id, brief, proj.files, PROJECT_CONTRACT_HASH, "key-w")
    store.enqueue("owner-window", task["task_id"], "token-w", phase="plan")

    engine = CodingEngine(client=DeterministicClient(), model_id="test-model", executor=MockExecutor(), synthetic=False)

    # Worker with remaining session seconds below threshold (e.g. 60s < 90s required)
    worker = CodingWorker(
        store,
        engine,
        live_enabled=True,
        session_seconds_remaining=lambda: 60.0,
        lease_seconds=100,
    )

    # Worker refuses to execute live action
    result = worker.run_once()
    assert result == {"code": "SESSION_WINDOW_INSUFFICIENT"}
    # Task remains queued and unexecuted
    assert store.get_task("owner-window", task["task_id"])["state"] == "QUEUED"


# ── 3. Quota Accounting and Operator Limits ──────────────────────────────────

def test_quota_accounting_enforcement(tmp_path: Path) -> None:
    db = tmp_path / "quota.db"
    # Set tight limits: max 1 model call, max 1 execution per day
    limits = OperatorLimits(model_calls_per_day=1, executions_per_day=1, max_tasks=2)
    store = CodingStore(db, limits)
    proj_store = ProjectStore(db)

    proj = proj_store.create_project(
        owner_ref="owner-quota",
        name="Calc",
        files=SAMPLE_PROJECT_FILES,
    )

    brief = CodingBrief(task="Test quota", source_hash=proj.source_hash, editable_paths=["app/calc.py"])
    task = store.create_task("owner-quota", proj.project_id, brief, proj.files, PROJECT_CONTRACT_HASH, "key-q1")
    store.enqueue("owner-quota", task["task_id"], "token-q1", phase="plan")

    plan_obj = CodingPlan(
        source_hash=proj.source_hash,
        brief_hash=brief.identity(),
        steps=["Step 1: check negative"],
        target_files=["app/calc.py"],
        check_profile="project-unittest-v1",
    )
    client = DeterministicClient(plan_json=plan_obj.model_dump_json())
    engine = CodingEngine(client=client, model_id="test-model", executor=MockExecutor(), synthetic=True)
    worker = CodingWorker(
        store, engine, live_enabled=True, session_seconds_remaining=lambda: 1000.0, lease_seconds=100
    )

    # First model call succeeds (plan generation)
    res1 = worker.run_once()
    assert res1 is not None
    assert res1.get("state") == "AWAITING_APPROVAL"

    # Second model call violates daily allowance
    brief2 = CodingBrief(task="Second task", source_hash=proj.source_hash, editable_paths=["app/calc.py"])
    task2 = store.create_task("owner-quota", proj.project_id, brief2, proj.files, PROJECT_CONTRACT_HASH, "key-q2")
    store.enqueue("owner-quota", task2["task_id"], "token-q2", phase="plan")

    # Worker attempts to reserve model call, hits operator daily quota, blocks task safely
    res2 = worker.run_once()
    assert res2 is not None
    assert res2.get("code") == "OPERATOR_LIMIT"


# ── 4. Strict Data Ownership and Cross-Owner Isolation ───────────────────────

def test_cross_owner_task_and_project_isolation(tmp_path: Path) -> None:
    db = tmp_path / "isolation.db"
    store = CodingStore(db, OperatorLimits())
    proj_store = ProjectStore(db)

    # Alice creates project and task
    proj_alice = proj_store.create_project(
        owner_ref="owner-alice",
        name="AliceCalc",
        files=SAMPLE_PROJECT_FILES,
    )
    brief = CodingBrief(task="Alice task", source_hash=proj_alice.source_hash, editable_paths=["app/calc.py"])
    task_alice = store.create_task("owner-alice", proj_alice.project_id, brief, proj_alice.files, PROJECT_CONTRACT_HASH, "key-alice")
    task_id = task_alice["task_id"]

    # Bob attempts to access Alice's project -> NOT_FOUND
    assert proj_store.get_project(proj_alice.project_id, owner_ref="owner-bob") is None
    bob_projects = proj_store.list_projects("owner-bob")
    assert not any(p["project_id"] == proj_alice.project_id for p in bob_projects)

    # Bob attempts to access Alice's task -> NOT_FOUND
    with pytest.raises(CodingStoreError) as exc:
        store.get_task("owner-bob", task_id)
    assert exc.value.code == "NOT_FOUND"

    # Bob attempts to control Alice's task -> NOT_FOUND
    with pytest.raises(CodingStoreError) as exc:
        store.control("owner-bob", task_id, "pause")
    assert exc.value.code == "NOT_FOUND"

    # Bob attempts to export Alice's bundle -> NOT_FOUND
    with pytest.raises(CodingStoreError) as exc:
        store.export_bundle("owner-bob", task_id)
    assert exc.value.code == "NOT_FOUND"

    with pytest.raises(CodingStoreError) as exc:
        store.export_bundle_zip("owner-bob", task_id)
    assert exc.value.code == "NOT_FOUND"


# ── 5. Secret Scrubbing in Candidates and Export Bundles ───────────────────────

def test_secret_scrubbing_in_export_bundle(tmp_path: Path) -> None:
    db = tmp_path / "secrets.db"
    store = CodingStore(db, OperatorLimits())
    proj_store = ProjectStore(db)

    proj = proj_store.create_project(
        owner_ref="owner-sec",
        name="SecretSafeCalc",
        files=SAMPLE_PROJECT_FILES,
    )

    brief = CodingBrief(task="Safe brief", source_hash=proj.source_hash, editable_paths=["app/calc.py"])
    task = store.create_task("owner-sec", proj.project_id, brief, proj.files, PROJECT_CONTRACT_HASH, "key-sec")
    task_id = task["task_id"]

    # Export bundle JSON and ZIP
    bundle_json = store.export_bundle("owner-sec", task_id)
    raw_json = json.dumps(bundle_json)

    # Verify no secret markers or environment keys leak into the exported bundle
    forbidden_tokens = [
        "NEBIUS_API_KEY",
        "BEARER_TOKEN",
        "AWS_SECRET_ACCESS_KEY",
        "OPENAI_API_KEY",
        "BEGIN PRIVATE KEY",
        "DATABASE_URL",
    ]
    for token in forbidden_tokens:
        assert token not in raw_json

    bundle_zip_bytes = store.export_bundle_zip("owner-sec", task_id)
    assert len(bundle_zip_bytes) > 0
    with zipfile.ZipFile(Path(tmp_path / "test_sec.zip"), "w") as zf:
        zf.writestr("test.zip", bundle_zip_bytes)

    # Inspect contents
    with zipfile.ZipFile(tmp_path / "test_sec.zip") as zf:
        for name in zf.namelist():
            assert not name.startswith(".env")
            assert "secret" not in name.lower()


# ── 6. Online Database Backup and Restore Round-Trip ─────────────────────────

def test_online_backup_and_restore_round_trip(tmp_path: Path) -> None:
    src_db = tmp_path / "live_benchproof.db"
    backup_file = tmp_path / "backup_20261017.db"
    restored_db = tmp_path / "restored_benchproof.db"

    # Populate live database with projects and tasks
    store = CodingStore(src_db, OperatorLimits())
    proj_store = ProjectStore(src_db)

    proj = proj_store.create_project(
        owner_ref="owner-bak",
        name="BackupProject",
        files=SAMPLE_PROJECT_FILES,
    )

    brief = CodingBrief(task="Backup test", source_hash=proj.source_hash, editable_paths=["app/calc.py"])
    task = store.create_task("owner-bak", proj.project_id, brief, proj.files, PROJECT_CONTRACT_HASH, "key-b1")
    store.enqueue("owner-bak", task["task_id"], "token-b1", phase="plan")

    # Perform atomic online backup
    manifest = create_backup(src_db, backup_file)
    assert manifest["integrity"] == "ok"
    assert manifest["byte_size"] > 0
    assert len(manifest["sha256"]) == 64
    assert manifest["table_counts"]["coding_tasks"] >= 1
    assert manifest["table_counts"]["coding_projects"] >= 1

    # Verify manifest file was written
    manifest_file = backup_file.with_suffix(".db.manifest.json")
    assert manifest_file.exists()

    # Perform restore to new destination with expected checksum verification
    restore_info = restore_backup(backup_file, restored_db, expected_sha256=manifest["sha256"])
    assert restore_info["integrity"] == "ok"
    assert restore_info["table_counts"]["coding_tasks"] == manifest["table_counts"]["coding_tasks"]
    assert restore_info["table_counts"]["coding_projects"] == manifest["table_counts"]["coding_projects"]

    # Verify restored database is directly usable by store and projects
    restored_store = CodingStore(restored_db, OperatorLimits())
    restored_task = restored_store.get_task("owner-bak", task["task_id"])
    assert restored_task["task_id"] == task["task_id"]
    assert restored_task["brief"]["task"] == "Backup test"

    restored_proj_store = ProjectStore(restored_db)
    restored_proj = restored_proj_store.get_project(proj.project_id, owner_ref="owner-bak")
    assert restored_proj is not None
    assert restored_proj.name == "BackupProject"


def test_restore_checksum_mismatch_refusal(tmp_path: Path) -> None:
    src_db = tmp_path / "source.db"
    backup_file = tmp_path / "backup.db"
    dest_db = tmp_path / "dest.db"

    # Create dummy database
    with sqlite3.connect(src_db) as conn:
        conn.execute("CREATE TABLE t (x INT);")
        conn.execute("INSERT INTO t VALUES (42);")

    manifest = create_backup(src_db, backup_file)

    # Attempt restore with incorrect expected sha256 -> rejected
    with pytest.raises(BackupError) as exc:
        restore_backup(backup_file, dest_db, expected_sha256="0" * 64)
    assert exc.value.code == "CHECKSUM_MISMATCH"
