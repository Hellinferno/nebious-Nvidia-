from pathlib import Path

import pytest

from benchproof.patch import compute_diff_hash, extract_diff_paths, get_canonical_ac01_repair_diff
from benchproof.storage import list_patches, migrate
from benchproof.storage.lifecycle import migrate_lifecycle
from scripts import run_bundle_replay


def test_unavailable_runner_creates_no_evidence(tmp_path, monkeypatch, capsys):
    output = tmp_path / "evidence"
    monkeypatch.setattr(run_bundle_replay.DockerRunner, "available", lambda self: (False, "offline"))
    monkeypatch.setattr("sys.argv", ["run_bundle_replay.py", "--output-dir", str(output)])

    assert run_bundle_replay.main() == 2
    assert not output.exists()
    assert "RUNNER_UNAVAILABLE" in capsys.readouterr().err


def test_existing_output_is_not_overwritten(tmp_path, monkeypatch):
    output = tmp_path / "evidence"
    output.mkdir()
    sentinel = output / "replay-evidence.db"
    sentinel.write_bytes(b"existing evidence")
    monkeypatch.setattr(run_bundle_replay.DockerRunner, "available", lambda self: (True, "ready"))
    monkeypatch.setattr("sys.argv", ["run_bundle_replay.py", "--output-dir", str(output)])

    with pytest.raises(FileExistsError):
        run_bundle_replay.main()
    assert sentinel.read_bytes() == b"existing evidence"


def test_reference_patch_has_real_hash_and_requires_docker(tmp_path, monkeypatch):
    database = tmp_path / "test.db"
    migrate(database)
    migrate_lifecycle(database)
    calls = []

    def verify(audit_id, **kwargs):
        calls.append(kwargs)
        return {"verdict": "VERIFIED"}

    monkeypatch.setattr(run_bundle_replay, "execute_acceptance_gate", verify)
    diff = get_canonical_ac01_repair_diff()
    audit_id = run_bundle_replay.setup_audit_and_gate(database, "AC-01", diff)
    patch = list_patches(audit_id, db_path=database)[0]

    assert calls[0]["use_docker"] is True
    assert calls[0]["db_path"] == database
    assert patch["diff_hash"] == compute_diff_hash(diff)
    assert patch["approved_paths"] == extract_diff_paths(diff)
    assert patch["policy_result"] == "PENDING"
    assert patch["author"] == "trusted-reference-repair"


def test_reference_failure_cannot_be_reported_as_success(tmp_path: Path, monkeypatch):
    database = tmp_path / "test.db"
    migrate(database)
    migrate_lifecycle(database)
    monkeypatch.setattr(
        run_bundle_replay, "execute_acceptance_gate", lambda *args, **kwargs: {"verdict": "REJECTED"}
    )

    with pytest.raises(RuntimeError, match="did not verify"):
        run_bundle_replay.setup_audit_and_gate(database, "clean-service")
