"""Tests for bounded NVIDIA investigation, diagnosis validation and probe execution (B-08)."""

from pathlib import Path

import pytest

from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord
from benchproof.fixtures import source_hash
from benchproof.investigation import (
    DiagnosisProposal,
    Hypothesis,
    InvestigationError,
    run_investigation,
)
from benchproof.storage import migrate, save_audit
from benchproof.storage.lifecycle import migrate_lifecycle


def test_hypothesis_validation():
    # Valid hypothesis
    h = Hypothesis(
        hypothesis_id="H1",
        constraint_id="C-AMOUNT",
        source_location="app/money.py:compute_total",
        claim="Line rounding violates C-AMOUNT",
        refutation_condition="Check passes under boundary values",
        proposed_probe="observe_invoice",
    )
    assert h.constraint_id == "C-AMOUNT"

    # Normalized constraint ID
    h2 = Hypothesis(
        hypothesis_id="H2",
        constraint_id="C-API-FIELD",
        source_location="app/schemas.py:ReceiptResponse",
        claim="Missing response fields",
        refutation_condition="Schema validator passes",
    )
    assert h2.constraint_id == "C-API"

    # Unapproved constraint rejected
    with pytest.raises(ValueError, match="Unknown or unapproved constraint"):
        Hypothesis(
            hypothesis_id="H3",
            constraint_id="C-UNKNOWN-DOES-NOT-EXIST",
            source_location="app/dummy.py",
            claim="Invalid",
            refutation_condition="Invalid",
        )


def test_diagnosis_proposal_max_two_hypotheses():
    h1 = Hypothesis(
        hypothesis_id="H1",
        constraint_id="C-AMOUNT",
        source_location="app/money.py:compute_total",
        claim="Claim 1",
        refutation_condition="Refutation 1",
    )
    h2 = Hypothesis(
        hypothesis_id="H2",
        constraint_id="C-API",
        source_location="app/schemas.py:ReceiptResponse",
        claim="Claim 2",
        refutation_condition="Refutation 2",
    )
    h3 = Hypothesis(
        hypothesis_id="H3",
        constraint_id="C-INTEGRITY",
        source_location="app/worker.py:handle_invoice_job",
        claim="Claim 3",
        refutation_condition="Refutation 3",
    )

    # 2 hypotheses is valid
    p = DiagnosisProposal(hypotheses=[h1, h2])
    assert len(p.hypotheses) == 2

    # 3 hypotheses rejected
    with pytest.raises(ValueError):
        DiagnosisProposal(hypotheses=[h1, h2, h3])


def test_stale_hash_rejected(tmp_path: Path):
    db = tmp_path / "test.db"
    migrate(db)
    migrate_lifecycle(db)

    aid = "audit-stale-test"
    rec = AuditRecord(
        audit_id=aid,
        owner_ref="test-owner",
        fixture_id="MC-01",
        source_hash=source_hash("MC-01"),
        contract_hash=contract_hash(),
    )
    save_audit(rec, db_path=db)

    # Stale source hash rejected
    with pytest.raises(InvestigationError) as exc_info:
        run_investigation("MC-01", aid, current_source_hash="wrong_stale_hash", db_path=db)
    assert exc_info.value.code == "STALE_SOURCE"

    # Stale contract hash rejected
    with pytest.raises(InvestigationError) as exc_info:
        run_investigation("MC-01", aid, current_contract_hash="wrong_contract_hash", db_path=db)
    assert exc_info.value.code == "CONTRACT_UNAPPROVED"


def test_investigation_supported_for_faulty_fixture(tmp_path: Path):
    db = tmp_path / "test.db"
    migrate(db)
    migrate_lifecycle(db)

    aid = "audit-faulty-mc01"
    rec = AuditRecord(
        audit_id=aid,
        owner_ref="test-owner",
        fixture_id="MC-01",
        source_hash=source_hash("MC-01"),
        contract_hash=contract_hash(),
    )
    save_audit(rec, db_path=db)

    res = run_investigation("MC-01", aid, target_symbols=["app.money:compute_total"], db_path=db)
    assert res["action_id"].startswith("act-")
    assert res["risk_severity"] == "HIGH"
    assert len(res["hypotheses_evaluation"]) >= 1

    # In MC-01, amount-boundary fails, so C-AMOUNT hypothesis should be SUPPORTED
    h_eval = res["hypotheses_evaluation"][0]
    if h_eval["constraint_id"] == "C-AMOUNT":
        assert h_eval["outcome"] == "SUPPORTED"


def test_investigation_refuted_for_clean_service(tmp_path: Path):
    db = tmp_path / "test.db"
    migrate(db)
    migrate_lifecycle(db)

    aid = "audit-clean-svc"
    rec = AuditRecord(
        audit_id=aid,
        owner_ref="test-owner",
        fixture_id="clean-service",
        source_hash=source_hash("clean-service"),
        contract_hash=contract_hash(),
    )
    save_audit(rec, db_path=db)

    res = run_investigation("clean-service", aid, db_path=db)
    assert res["action_id"].startswith("act-")
    assert len(res["hypotheses_evaluation"]) >= 1

    # In clean-service, all checks pass, so hypothesis should be REFUTED
    for h in res["hypotheses_evaluation"]:
        assert h["outcome"] == "REFUTED"
