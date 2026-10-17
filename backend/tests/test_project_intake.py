"""Tests for project intake, security boundaries, and storage (C-04)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api.main import app
from benchproof.projects.intake import (
    MAX_FILE_BYTES,
    MAX_FILES,
    ProjectIntakeError,
    validate_project_intake,
    validate_relative_path,
)
from benchproof.projects.store import ProjectStore, ProjectStoreError

OWNER_A = "owner-alpha-1234"
OWNER_B = "owner-bravo-5678"


def test_intake_valid_small_project() -> None:
    files = {
        "app/maths.py": "def add(a: int, b: int) -> int:\n    return a + b\n",
        "tests/test_maths.py": (
            "import unittest\nfrom app.maths import add\n\n"
            "class TestMaths(unittest.TestCase):\n"
            "    def test_add(self):\n"
            "        self.assertEqual(add(2, 3), 5)\n"
        ),
    }
    manifest, norm = validate_project_intake(files, runner_profile="unittest")
    assert manifest.runner_profile == "unittest"
    assert manifest.total_files == 2
    assert "app/maths.py" in manifest.app_files
    assert "tests/test_maths.py" in manifest.test_files
    assert len(manifest.source_hash) == 64
    assert norm["app/maths.py"] == files["app/maths.py"]


def test_intake_rejects_path_traversal() -> None:
    bad_paths = [
        "app/../etc/passwd",
        "../tests/test_foo.py",
        "/app/main.py",
        "app/./main.py",
        "app//main.py",
        "C:\\app\\main.py",
        "app\\main.py",
    ]
    for path in bad_paths:
        with pytest.raises(ProjectIntakeError) as exc_info:
            validate_relative_path(path)
        assert exc_info.value.code in {"PATH_TRAVERSAL", "INVALID_PATH"}


def test_intake_rejects_unsafe_and_secret_files() -> None:
    bad_files = [
        "app/.env",
        "tests/.git",
        "app/credentials.json",
        "app/secret_token.py",
        "app/private_key.pem",
        "app/id_rsa",
        "app/__pycache__/cached.py",
        "app/.pytest_cache/v.py",
        "app/database.sqlite",
        "app/archive.zip",
    ]
    for path in bad_files:
        with pytest.raises(ProjectIntakeError) as exc_info:
            validate_relative_path(path)
        assert exc_info.value.code in {"UNSAFE_FILE", "SECRET_DETECTED"}


def test_intake_rejects_case_collisions() -> None:
    files = {
        "app/calculator.py": "def calc(): pass\n",
        "app/CALCULATOR.PY": "def calc(): pass\n",
        "tests/test_calc.py": "import unittest\n",
    }
    with pytest.raises(ProjectIntakeError) as exc_info:
        validate_project_intake(files)
    assert exc_info.value.code == "CASE_COLLISION"


def test_intake_rejects_oversized_file() -> None:
    large_content = "x = 1\n" * ((MAX_FILE_BYTES // 6) + 10)
    files = {
        "app/large.py": large_content,
        "tests/test_large.py": "import unittest\n",
    }
    with pytest.raises(ProjectIntakeError) as exc_info:
        validate_project_intake(files)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_intake_rejects_oversized_total_project() -> None:
    # 6 files of 22.95 KiB each = 137.7 KiB > MAX_TOTAL_BYTES (128 KiB)
    chunk = "# comment line for padding\n" * 850  # ~22.95 KiB
    files = {f"app/mod_{i}.py": chunk for i in range(6)}
    files["tests/test_all.py"] = "import unittest\n"
    with pytest.raises(ProjectIntakeError) as exc_info:
        validate_project_intake(files)
    assert exc_info.value.code == "TOTAL_SIZE_EXCEEDED"


def test_intake_rejects_file_count_exceeded() -> None:
    files = {f"app/m_{i}.py": "pass\n" for i in range(MAX_FILES + 1)}
    files["tests/test_m.py"] = "import unittest\n"
    with pytest.raises(ProjectIntakeError) as exc_info:
        validate_project_intake(files)
    assert exc_info.value.code == "FILE_COUNT_EXCEEDED"


def test_intake_rejects_binary_null_bytes() -> None:
    files = {
        "app/binary.py": "x = 'hello\x00world'\n",
        "tests/test_b.py": "import unittest\n",
    }
    with pytest.raises(ProjectIntakeError) as exc_info:
        validate_project_intake(files)
    assert exc_info.value.code == "BINARY_FILE"


def test_intake_rejects_missing_app_or_tests() -> None:
    no_app = {"tests/test_foo.py": "import unittest\n"}
    with pytest.raises(ProjectIntakeError) as exc_info:
        validate_project_intake(no_app)
    assert exc_info.value.code == "MISSING_APP_FILES"

    no_tests = {"app/foo.py": "x = 1\n"}
    with pytest.raises(ProjectIntakeError) as exc_info:
        validate_project_intake(no_tests)
    assert exc_info.value.code == "MISSING_TEST_FILES"


def test_project_store_persistence_and_owner_isolation(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "projects.db")
    files = {
        "app/service.py": "def run(): return 42\n",
        "tests/test_service.py": "import unittest\n",
    }
    created = store.create_project(OWNER_A, "Service Alpha", files)
    assert created.project_id.startswith("proj-")
    assert created.name == "Service Alpha"

    # Owner A can retrieve
    retrieved = store.get_project(created.project_id, owner_ref=OWNER_A)
    assert retrieved is not None
    assert retrieved.name == "Service Alpha"

    # Owner B cannot retrieve or delete Owner A's project
    assert store.get_project(created.project_id, owner_ref=OWNER_B) is None
    assert not store.delete_project(created.project_id, owner_ref=OWNER_B)

    # Owner list
    a_projects = store.list_projects(OWNER_A)
    assert len(a_projects) == 1
    assert a_projects[0]["project_id"] == created.project_id
    assert len(store.list_projects(OWNER_B)) == 0


def test_project_store_quota_enforcement(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "projects.db", max_projects_per_owner=2)
    files = {
        "app/s.py": "pass\n",
        "tests/test_s.py": "import unittest\n",
    }
    store.create_project(OWNER_A, "Proj 1", files)
    store.create_project(OWNER_A, "Proj 2", files)
    with pytest.raises(ProjectStoreError) as exc_info:
        store.create_project(OWNER_A, "Proj 3", files)
    assert exc_info.value.code == "STORAGE_LIMIT"


def test_api_projects_endpoints(tmp_path: Path) -> None:
    client = TestClient(app)
    headers = {"X-BenchProof-Owner": "owner-api-test-1234"}

    payload = {
        "name": "API Test Project",
        "runner_profile": "unittest",
        "files": {
            "app/calc.py": "def multiply(a, b): return a * b\n",
            "tests/test_calc.py": (
                "import unittest\nfrom app.calc import multiply\n\n"
                "class TestCalc(unittest.TestCase):\n"
                "    def test_mult(self):\n"
                "        self.assertEqual(multiply(2, 4), 8)\n"
            ),
        },
    }

    # 1. Create project
    res = client.post("/api/v1/projects", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    project_id = data["project_id"]
    assert project_id.startswith("proj-")
    assert data["manifest"]["total_files"] == 2

    # 2. List projects
    list_res = client.get("/api/v1/projects", headers=headers)
    assert list_res.status_code == 200
    assert any(p["project_id"] == project_id for p in list_res.json())

    # 3. Get project by ID
    get_res = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "API Test Project"

    # 4. Get source
    src_res = client.get(f"/api/v1/projects/{project_id}/source", headers=headers)
    assert src_res.status_code == 200
    assert "app/calc.py" in src_res.json()["files"]

    # 5. Delete project
    del_res = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_api_projects_body_limit_413() -> None:
    client = TestClient(app)
    headers = {"X-BenchProof-Owner": "owner-api-test-1234", "Content-Type": "application/json"}

    # Exceed 256 KiB body limit (> 262,144 bytes)
    big_padding = "x" * 270_000
    oversize_payload = json.dumps({"name": "Huge", "files": {"app/x.py": big_padding}})
    res = client.post("/api/v1/projects", content=oversize_payload, headers=headers)
    assert res.status_code == 413
    assert res.json()["detail"]["code"] == "SOURCE_LIMIT"
