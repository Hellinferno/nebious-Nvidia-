"""Decision-ledger freshness, current-context, and delayed-response tests (B-14)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api.main import app, settings
from benchproof.decisions import build_current_context, create_decision, refresh_decisions
from benchproof.domain import AuditRecord, DecisionReviewStatus
from benchproof.fixtures import source_hash_for_dir
from benchproof.investigation import (
    DiagnosisProposal,
    Hypothesis,
    InvestigationError,
    run_investigation,
)
from benchproof.storage import migrate, save_audit
from benchproof.storage.lifecycle import list_events, migrate_lifecycle


def _audit(tmp_path: Path, *, audit_id: str = "audit-decisions") -> tuple[Path, Path]:
    db = tmp_path / "test.db"
    app_dir = tmp_path / "fixture" / "app"
    app_dir.mkdir(parents=True)
    (app_dir / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (app_dir / "other.py").write_text("OTHER = 1\n", encoding="utf-8")
    migrate(db)
    migrate_lifecycle(db)
    save_audit(
        AuditRecord(
            audit_id=audit_id,
            owner_ref="test-owner",
            fixture_id="fixture",
            source_hash=source_hash_for_dir(app_dir),
            contract_hash="contract-v1",
        ),
        db,
    )
    return db, app_dir


@pytest.mark.parametrize(
    ("transition", "expected_status", "expected_dependency_status"),
    [
        ("changed_file", "STALE", "CHANGED"),
        ("deleted_file", "STALE", "DELETED"),
        ("changed_contract", "STALE", "CHANGED"),
        ("unchanged", "CURRENT", "CURRENT"),
        ("unrelated_edit", "CURRENT", "CURRENT"),
        ("unrelated_add", "CURRENT", "CURRENT"),
    ],
)
def test_three_stale_and_three_fresh_transitions(
    tmp_path: Path,
    transition: str,
    expected_status: str,
    expected_dependency_status: str,
) -> None:
    db, app_dir = _audit(tmp_path, audit_id=f"audit-{transition}")
    decision = create_decision(
        audit_id=f"audit-{transition}",
        app_dir=app_dir,
        statement="Keep core behavior compatible with the accepted contract.",
        owner="test-owner",
        review_status=DecisionReviewStatus.REVIEWED,
        current_contract_hash="contract-v1",
        dependency_paths=["app/core.py"],
        include_contract=True,
        db_path=db,
    )

    current_contract = "contract-v1"
    if transition == "changed_file":
        (app_dir / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
    elif transition == "deleted_file":
        (app_dir / "core.py").unlink()
    elif transition == "changed_contract":
        current_contract = "contract-v2"
    elif transition == "unrelated_edit":
        (app_dir / "other.py").write_text("OTHER = 2\n", encoding="utf-8")
    elif transition == "unrelated_add":
        (app_dir / "new.py").write_text("NEW = True\n", encoding="utf-8")

    ledger = refresh_decisions(f"audit-{transition}", app_dir, current_contract, db)
    assert ledger["refresh_overhead_ms"] >= 0
    record = ledger["decisions"][0]
    assert record["status"] == expected_status
    statuses = {item["dependency_type"]: item["status"] for item in record["dependencies"]}
    if transition == "changed_contract":
        assert statuses["contract"] == expected_dependency_status
    else:
        assert statuses["file"] == expected_dependency_status
    assert (decision.decision_id in ledger["current_decision_ids"]) is (expected_status == "CURRENT")


def test_stale_and_proposed_decisions_are_excluded_from_rebuilt_context(tmp_path: Path) -> None:
    db, app_dir = _audit(tmp_path)
    reviewed = create_decision(
        audit_id="audit-decisions",
        app_dir=app_dir,
        statement="Reviewed and relevant.",
        owner="test-owner",
        review_status=DecisionReviewStatus.REVIEWED,
        current_contract_hash="contract-v1",
        dependency_paths=["core.py"],
        db_path=db,
    )
    proposed = create_decision(
        audit_id="audit-decisions",
        app_dir=app_dir,
        statement="Agent proposal awaiting review.",
        owner="test-owner",
        review_status=DecisionReviewStatus.PROPOSED,
        current_contract_hash="contract-v1",
        dependency_paths=["other.py"],
        db_path=db,
    )
    _, _, initial_context, _ = build_current_context(
        "audit-decisions", app_dir, "contract-v1", db_path=db
    )
    assert initial_context.current_decision_ids == [reviewed.decision_id]
    assert proposed.decision_id not in initial_context.current_decision_ids

    (app_dir / "core.py").write_text("VALUE = 99\n", encoding="utf-8")
    _, _, rebuilt_context, ledger = build_current_context(
        "audit-decisions", app_dir, "contract-v1", db_path=db
    )
    assert reviewed.decision_id not in rebuilt_context.current_decision_ids
    assert ledger["decisions"][0]["stale_reason"]
    assert ledger["decisions"][0]["current_versions"]


def test_provider_response_is_rejected_when_source_changes_during_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, app_dir = _audit(tmp_path, audit_id="audit-late-response")
    fixture_root = app_dir.parent

    def change_source(*_args, **_kwargs):
        (app_dir / "core.py").write_text("VALUE = 7\n", encoding="utf-8")
        proposal = DiagnosisProposal(
            hypotheses=[
                Hypothesis(
                    hypothesis_id="H1",
                    constraint_id="C-AMOUNT",
                    source_location="app/core.py:VALUE",
                    claim="A bounded claim.",
                    refutation_condition="The accepted check passes.",
                )
            ]
        )
        return proposal, {"mode": "test"}

    monkeypatch.setattr("benchproof.investigation.fixture_dir", lambda _fixture_id: fixture_root)
    monkeypatch.setattr("benchproof.investigation.generate_structured_diagnosis", change_source)

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation("fixture", "audit-late-response", db_path=db)
    assert exc_info.value.code == "STALE_CONTEXT"
    assert any(event["event_type"] == "context_stale" for event in list_events("audit-late-response", db_path=db))


def test_api_exposes_versions_and_rejects_patch_from_old_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixtures = tmp_path / "fixtures"
    fixture = fixtures / "local"
    app_dir = fixture / "app"
    app_dir.mkdir(parents=True)
    (app_dir / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (fixture / "fixture.json").write_text(
        '{"fixture_id":"local","suite":"test","family":"test","synthetic":true}',
        encoding="utf-8",
    )
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(fixtures))
    settings.database_path = str(tmp_path / "api.db")

    with TestClient(app) as client:
        client.headers.update({"X-BenchProof-Owner": "test-owner"})
        created = client.post("/api/v1/audits", json={"fixture_id": "local", "mode": "mock"})
        assert created.status_code == 201
        audit_id = created.json()["audit_id"]
        recorded = client.post(
            f"/api/v1/audits/{audit_id}/decisions",
            json={
                "statement": "Core remains stable.",
                "review_status": "REVIEWED",
                "dependency_paths": ["app/core.py"],
                "include_contract": True,
            },
        )
        assert recorded.status_code == 201
        old_context = client.get(f"/api/v1/audits/{audit_id}/impact").json()["context_hash"]

        missing_context = client.post(
            f"/api/v1/audits/{audit_id}/patch",
            json={
                "diff": "--- a/app/core.py\n+++ b/app/core.py\n",
                "base_source_hash": source_hash_for_dir(app_dir),
                "target_files": ["app/core.py"],
            },
        )
        assert missing_context.status_code == 409
        assert missing_context.json()["detail"]["code"] == "STALE_CONTEXT"

        (app_dir / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
        rejected = client.post(
            f"/api/v1/audits/{audit_id}/patch",
            json={
                "diff": "--- a/app/core.py\n+++ b/app/core.py\n",
                "base_source_hash": source_hash_for_dir(app_dir),
                "target_files": ["app/core.py"],
                "context_hash": old_context,
            },
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["code"] == "STALE_CONTEXT"
        ledger = client.get(f"/api/v1/audits/{audit_id}/decisions").json()
        assert ledger["decisions"][0]["status"] == "STALE"
        assert ledger["decisions"][0]["stale_reason"]
        assert ledger["decisions"][0]["current_versions"]
