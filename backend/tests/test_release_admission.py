"""Release admission checks without inference or candidate execution."""

from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from benchproof.api.coding import _project_snapshot
from benchproof.coding.contracts import CodingBrief, CodingStoreError, OperatorLimits
from benchproof.coding.store import CodingStore
from benchproof.coding.worker import CodingWorker
from benchproof.execution.project_runner import PROJECT_CONTRACT_HASH, ProjectExecutor
from benchproof.projects.intake import ProjectIntakeError, validate_project_intake
from benchproof.projects.store import ProjectStore, ProjectStoreError
from benchproof.storage import admission
from benchproof.storage.admission import (
    StorageAdmissionError,
    StorageAdmissionLimits,
    check_storage_admission,
)

FILES = {"app/core.py": "VALUE = 1\n", "tests/test_core.py": "import unittest\n"}


def make_task(records, project, key="create-one"):
    brief = CodingBrief(
        task="Change the value", source_hash=project.source_hash, editable_paths=["app/core.py"],
    )
    return records.create_task(
        project.owner_ref, project.project_id, brief, project.files, PROJECT_CONTRACT_HASH, key,
    )


@pytest.mark.parametrize("profile", ["pytest", "shell", "", "project-unittest-v1"])
def test_unsupported_profiles_never_reach_storage_or_executor(tmp_path, profile):
    with pytest.raises(ProjectIntakeError, match="unsupported"):
        validate_project_intake(FILES, runner_profile=profile)
    projects = ProjectStore(tmp_path / "projects.db")
    with pytest.raises(ProjectIntakeError):
        projects.create_project("owner", "Project", FILES, runner_profile=profile)
    assert projects.list_projects("owner") == []

    def forbidden_execution(*args):
        pytest.fail("An unsupported profile must not dispatch candidate execution")

    executor = ProjectExecutor(synthetic_runner=forbidden_execution)
    with pytest.raises(ValueError, match="Only the unittest"):
        executor.run(FILES, operation_id="unsupported-profile", runner_profile=profile)
    assert not executor._cancelled


def test_api_rejects_unsupported_profile_without_persistence(client):
    response = client.post("/api/v1/projects", json={
        "name": "Unsupported", "runner_profile": "pytest", "files": FILES,
    })
    assert response.status_code == 422
    assert client.get("/api/v1/projects").json() == []


@pytest.mark.parametrize("change_manifest", [False, True])
def test_legacy_unsupported_projects_cannot_create_or_dispatch_tasks(tmp_path, change_manifest):
    database = tmp_path / "legacy.db"
    project = ProjectStore(database).create_project("owner", "Legacy", FILES)
    records = CodingStore(database, OperatorLimits(4, 4))
    task = make_task(records, project)
    records.enqueue("owner", task["task_id"], "queue-plan")
    lease = records.claim_next("worker")
    assert lease is not None
    with sqlite3.connect(database) as connection:
        if change_manifest:
            manifest = project.manifest.to_dict()
            manifest["runner_profile"] = "pytest"
            connection.execute(
                "UPDATE coding_projects SET manifest_json=?", (json.dumps(manifest),),
            )
        else:
            connection.execute("UPDATE coding_projects SET runner_profile='pytest'")
    with pytest.raises(CodingStoreError) as caught:
        make_task(records, project, key="another-task")
    assert caught.value.code == "UNSUPPORTED_RUNNER"
    with pytest.raises(CodingStoreError) as caught:
        _project_snapshot(database, project.project_id, "owner", project.source_hash)
    assert caught.value.code == "UNSUPPORTED_RUNNER"
    with pytest.raises(CodingStoreError) as caught:
        records.reserve_action(lease, "PLAN", project.source_hash)
    assert caught.value.code == "UNSUPPORTED_RUNNER"
    assert records.get_task("owner", task["task_id"])["counters"]["model_calls"] == 0


def test_global_project_count_cannot_be_reset_by_another_owner(tmp_path):
    projects = ProjectStore(tmp_path / "projects.db", max_projects=2)
    projects.create_project("first", "First", FILES)
    projects.create_project("second", "Second", FILES)
    with pytest.raises(ProjectStoreError) as caught:
        projects.create_project("new-owner", "Third", FILES)
    assert caught.value.code == "STORAGE_LIMIT"


def test_unsupported_legacy_queue_blocks_without_spending_or_holding_the_slot(tmp_path):
    database = tmp_path / "legacy-queue.db"
    project = ProjectStore(database).create_project("owner", "Legacy", FILES)
    records = CodingStore(database, OperatorLimits(4, 4))
    task = make_task(records, project)
    records.enqueue("owner", task["task_id"], "queue-plan")
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE coding_projects SET runner_profile='pytest'")

    def forbidden_dispatch(*args, **kwargs):
        pytest.fail("An unsupported legacy queue must not dispatch paid work")

    engine = SimpleNamespace(
        synthetic=True, validate=lambda task: None,
        max_output_tokens=2048, perform=forbidden_dispatch,
    )
    worker = CodingWorker(records, engine, worker_id="profile-guard")
    assert worker.run_once()["code"] == "UNSUPPORTED_RUNNER"
    final = records.get_task("owner", task["task_id"])
    assert final["state"] == "BLOCKED"
    assert final["counters"]["model_calls"] == 0
    assert final["actions"] == []
    assert worker.run_once() is None


def test_concurrent_owners_share_one_transactional_project_limit(tmp_path):
    database = tmp_path / "projects.db"
    projects = ProjectStore(database, max_projects=1)

    def create(owner):
        try:
            return projects.create_project(owner, "Concurrent", FILES).project_id
        except ProjectStoreError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ["owner-one", "owner-two"]))
    assert results.count("STORAGE_LIMIT") == 1
    assert sum(result.startswith("proj-") for result in results) == 1


def test_project_payload_limit_counts_encoded_bytes_and_releases_deleted_records(tmp_path):
    database = tmp_path / "projects.db"
    initial = ProjectStore(database)
    first = initial.create_project("owner-one", "Unicode", {
        **FILES, "app/core.py": "VALUE = '世界'\n",
    })
    with sqlite3.connect(database) as connection:
        used_bytes = connection.execute(
            "SELECT length(CAST(manifest_json AS BLOB)) + length(CAST(files_json AS BLOB)) "
            "FROM coding_projects"
        ).fetchone()[0]
    projects = ProjectStore(database, max_payload_bytes=2 * used_bytes)
    second = projects.create_project("owner-two", "Unicode", first.files)
    with pytest.raises(ProjectStoreError, match="shared project"):
        projects.create_project("owner-three", "Unicode", first.files)
    assert not projects.delete_project(second.project_id, "wrong-owner")
    assert projects.delete_project(second.project_id, "owner-two")
    projects.create_project("owner-three", "Unicode", first.files)
    assert projects.get_project(first.project_id, "owner-one") is not None


def test_task_replay_and_existing_reads_survive_low_disk_without_new_writes(tmp_path, monkeypatch):
    database = tmp_path / "projects.db"
    projects = ProjectStore(database)
    project = projects.create_project("owner", "Preserved", FILES)
    records = CodingStore(database, OperatorLimits(4, 4))
    task = make_task(records, project)
    monkeypatch.setattr(admission.shutil, "disk_usage", lambda path: SimpleNamespace(free=0))
    with pytest.raises(ProjectStoreError, match="free-space"):
        projects.create_project("other-owner", "Blocked", FILES)
    with pytest.raises(CodingStoreError, match="free-space"):
        make_task(records, project, key="new-key")
    assert make_task(records, project)["task_id"] == task["task_id"]
    assert projects.get_project(project.project_id, "owner") is not None
    assert projects.delete_project(project.project_id, "owner")
    assert records.get_task("owner", task["task_id"])["source_files"] == FILES


def test_storage_probe_failure_denies_admission_without_exposing_host_paths(tmp_path, monkeypatch):
    projects = ProjectStore(tmp_path / "projects.db")

    def broken_probe(path):
        raise OSError("sensitive-host-path")

    monkeypatch.setattr(admission.shutil, "disk_usage", broken_probe)
    with pytest.raises(ProjectStoreError, match="could not be verified") as caught:
        projects.create_project("owner", "Blocked", FILES)
    assert "sensitive-host-path" not in str(caught.value)
    assert projects.list_projects("owner") == []


def test_database_limit_includes_wal_and_exact_reservation_boundary(tmp_path, monkeypatch):
    database = tmp_path / "sample.db"
    database.write_bytes(b"a" * 30)
    database.with_name("sample.db-wal").write_bytes(b"b" * 20)
    monkeypatch.setattr(admission.shutil, "disk_usage", lambda path: SimpleNamespace(free=100))
    limits = StorageAdmissionLimits(min_free_bytes=50, max_database_bytes=100)
    check_storage_admission(database, 50, limits)
    with pytest.raises(StorageAdmissionError, match="database"):
        check_storage_admission(database, 51, limits)


def test_free_space_reservation_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(admission.shutil, "disk_usage", lambda path: SimpleNamespace(free=100))
    limits = StorageAdmissionLimits(min_free_bytes=50, max_database_bytes=200)
    check_storage_admission(tmp_path / "new.db", 50, limits)
    with pytest.raises(StorageAdmissionError, match="free-space"):
        check_storage_admission(tmp_path / "new.db", 51, limits)


def test_project_api_reports_storage_denial_without_deleting_existing_data(client, monkeypatch):
    payload = {"name": "Original", "files": FILES}
    created = client.post("/api/v1/projects", json=payload)
    assert created.status_code == 201
    monkeypatch.setattr(admission.shutil, "disk_usage", lambda path: SimpleNamespace(free=0))
    blocked = client.post("/api/v1/projects", json=payload)
    assert blocked.status_code == 413
    assert blocked.json()["detail"]["code"] == "STORAGE_LIMIT"
    assert len(client.get("/api/v1/projects").json()) == 1


@pytest.mark.parametrize("invalid", [0, -1, True, 1.5])
def test_invalid_storage_limits_are_rejected(tmp_path, invalid):
    with pytest.raises(ValueError):
        ProjectStore(tmp_path / "invalid.db", max_projects=invalid)
    with pytest.raises(ValueError):
        StorageAdmissionLimits(min_free_bytes=invalid)
