"""Tests for Day 7 / B-11: Evidence Bundle Export, Non-executing Validation, and Independent Replay."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api.main import app
from benchproof.bundle import export_bundle, replay_bundle, validate_bundle_nonexecuting
from benchproof.bundle.exporter import (
    SafeArchivePathError,
    SecurityExclusionError,
    assert_safe_archive_name,
    scan_for_secrets,
)
from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord, GateVerdict, RunState
from benchproof.fixtures import source_hash
from benchproof.gate import execute_acceptance_gate
from benchproof.patch import (
    get_canonical_ac01_repair_diff,
    get_canonical_mc01_repair_diff,
)
from benchproof.storage import migrate, save_audit, save_patch
from benchproof.storage.lifecycle import migrate_lifecycle


def build_canonical_repair_diff(fixture_id: str) -> str:
    if fixture_id == "mc-01":
        return get_canonical_mc01_repair_diff()
    elif fixture_id == "ac-01":
        return get_canonical_ac01_repair_diff()
    return ""


@pytest.fixture
def bundle_db(tmp_path: Path) -> Path:
    db = tmp_path / "test_bundle.db"
    migrate(db)
    migrate_lifecycle(db)
    return db


def _create_verified_audit(db: Path, fixture_id: str = "mc-01") -> str:
    audit_id = f"aud-test-bundle-{fixture_id}"
    shash = source_hash(fixture_id)
    chash = contract_hash()

    audit = AuditRecord(
        audit_id=audit_id,
        owner_ref="test-owner",
        fixture_id=fixture_id,
        source_hash=shash,
        contract_hash=chash,
        run_state=RunState.QUEUED,
        gate_verdict=GateVerdict.PENDING,
        mode="live",
    )
    save_audit(audit, db_path=db)

    # Propose canonical repair
    diff = build_canonical_repair_diff(fixture_id)
    patch_id = f"patch-{audit_id}"
    save_patch(
        patch_id=patch_id,
        audit_id=audit_id,
        base_hash=shash,
        diff_hash="test-diff-hash",
        diff_text=diff,
        approved_paths=["app/services.py"],
        changed_lines=5,
        policy_result="APPROVED",
        db_path=db,
    )

    # Execute gate to verify and record checks
    res = execute_acceptance_gate(audit_id, patch_id=patch_id, db_path=db)
    assert res["verdict"] == "VERIFIED"
    return audit_id


def test_export_bundle_creates_valid_zip_with_all_files(bundle_db: Path, tmp_path: Path) -> None:
    audit_id = _create_verified_audit(bundle_db, "mc-01")
    zip_path, manifest = export_bundle(
        audit_id,
        output_path=tmp_path / "test_bundle.zip",
        db_path=bundle_db,
    )

    assert zip_path.exists()
    assert manifest.gate_verdict == "VERIFIED"
    assert manifest.audit_id == audit_id
    assert manifest.fixture_id == "mc-01"
    assert "P1-decisions" in manifest.omissions
    assert "P1-mutations" in manifest.omissions

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        expected_names = {
            "manifest.json",
            "constraints.json",
            "state.json",
            "coverage.json",
            "decisions.json",
            "trajectory.jsonl",
            "candidate.diff",
            "source-manifest.json",
            "checks.json",
            "mutations.json",
            "environment.json",
            "usage.json",
            "report.md",
            "REPLAY.md",
        }
        assert expected_names.issubset(names)

        # Check content of report and replay
        report = zf.read("report.md").decode("utf-8")
        assert f"**Audit ID:** `{audit_id}`" in report
        assert "amount-boundary" in report

        replay = zf.read("REPLAY.md").decode("utf-8")
        assert "python scripts/replay_bundle.py" in replay


def test_validate_bundle_nonexecuting_success(bundle_db: Path, tmp_path: Path) -> None:
    audit_id = _create_verified_audit(bundle_db, "mc-01")
    zip_path, _ = export_bundle(audit_id, output_path=tmp_path / "test_bundle.zip", db_path=bundle_db)

    val = validate_bundle_nonexecuting(zip_path)
    assert val["valid"] is True
    assert val["manifest_hash_valid"] is True
    assert val["discrepancies"] == []
    assert val["verified_files"] == 13  # all 13 artifacts in manifest
    assert val["gate_verdict"] == "VERIFIED"


def test_validate_bundle_nonexecuting_detects_tampered_file(bundle_db: Path, tmp_path: Path) -> None:
    audit_id = _create_verified_audit(bundle_db, "mc-01")
    orig_zip, _ = export_bundle(audit_id, output_path=tmp_path / "orig_bundle.zip", db_path=bundle_db)

    # Create a tampered copy by replacing candidate.diff
    tampered_zip = tmp_path / "tampered_bundle.zip"
    with zipfile.ZipFile(orig_zip, "r") as zin, zipfile.ZipFile(tampered_zip, "w") as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "candidate.diff":
                content = content + b"\n# TAMPERED LINE"
            zout.writestr(item, content)

    val = validate_bundle_nonexecuting(tampered_zip)
    assert val["valid"] is False
    assert any("candidate.diff" in d for d in val["discrepancies"])


def test_secret_scanner_and_safe_names() -> None:
    # Safe names
    assert_safe_archive_name("manifest.json")
    assert_safe_archive_name("candidate.diff")
    with pytest.raises(SafeArchivePathError):
        assert_safe_archive_name("../evil.py")
    with pytest.raises(SafeArchivePathError):
        assert_safe_archive_name("/etc/passwd")

    # Secret scanner
    scan_for_secrets("This is clean public code.", "test.py")
    with pytest.raises(SecurityExclusionError):
        scan_for_secrets("nvapi-12345678901234567890abcdef", "secret.json")
    with pytest.raises(SecurityExclusionError):
        scan_for_secrets("Authorization: Bearer my_secret_token_12345678901234567890", "req.json")


def test_replay_bundle_verified_candidate(bundle_db: Path, tmp_path: Path) -> None:
    audit_id = _create_verified_audit(bundle_db, "mc-01")
    zip_path, _ = export_bundle(audit_id, output_path=tmp_path / "test_bundle.zip", db_path=bundle_db)

    record = replay_bundle(zip_path)
    assert record.tampered is False
    assert record.verdict_matches is True
    assert record.checks_matched is True
    assert record.replayed_verdict == "VERIFIED"
    assert record.original_verdict == "VERIFIED"
    assert len(record.check_comparisons) >= 5


def test_replay_bundle_detects_tampered_bundle(bundle_db: Path, tmp_path: Path) -> None:
    audit_id = _create_verified_audit(bundle_db, "mc-01")
    orig_zip, _ = export_bundle(audit_id, output_path=tmp_path / "orig_bundle.zip", db_path=bundle_db)

    # Tamper with checks.json
    tampered_zip = tmp_path / "tampered_checks.zip"
    with zipfile.ZipFile(orig_zip, "r") as zin, zipfile.ZipFile(tampered_zip, "w") as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "checks.json":
                content = content.replace(b"PASS", b"FAIL")
            zout.writestr(item, content)

    record = replay_bundle(tampered_zip)
    assert record.tampered is True
    assert record.replayed_verdict == "BLOCKED"
    assert record.verdict_matches is False
    assert len(record.tamper_details) > 0


def test_api_bundle_and_replay_endpoints(bundle_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("benchproof.api.main._db", lambda: bundle_db)
    client = TestClient(app)

    audit_id = _create_verified_audit(bundle_db, "mc-01")

    # 1. POST /bundle
    res = client.post(f"/api/v1/audits/{audit_id}/bundle")
    assert res.status_code == 200
    b_data = res.json()
    assert b_data["audit_id"] == audit_id
    assert "sha256" in b_data

    # 2. GET /bundle?metadata=true
    res = client.get(f"/api/v1/audits/{audit_id}/bundle?metadata=true")
    assert res.status_code == 200
    meta = res.json()
    assert meta["manifest"]["gate_verdict"] == "VERIFIED"

    # 3. GET /bundle (binary zip)
    res = client.get(f"/api/v1/audits/{audit_id}/bundle")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert len(res.content) > 100

    # 4. POST /bundle/validate
    res = client.post(f"/api/v1/audits/{audit_id}/bundle/validate")
    assert res.status_code == 200
    val_data = res.json()
    assert val_data["valid"] is True

    # 5. POST /replay
    res = client.post(f"/api/v1/audits/{audit_id}/replay")
    assert res.status_code == 200
    rep_data = res.json()
    assert rep_data["replayed_verdict"] == "VERIFIED"
    assert rep_data["verdict_matches"] is True
    assert rep_data["checks_matched"] is True
