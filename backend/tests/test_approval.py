"""Contract approval tests (B-03): pinned mappings, unapproved proposals, missing required checks."""

from __future__ import annotations

import pytest

from benchproof.constraints import contract_hash, list_constraints
from benchproof.constraints.approval import (
    ContractUnapproved,
    RequiredCheckMissing,
    approve_manifest,
    ensure_registry_executable,
)
from benchproof.evaluator import registry


def _approved() -> list[dict]:
    return [c.model_dump() for c in list_constraints()]


def test_registry_is_executable() -> None:
    ensure_registry_executable()


def test_exact_approved_manifest_is_accepted() -> None:
    out = approve_manifest(_approved())
    assert out["contract_hash"] == contract_hash()
    assert out["approved_ids"] == ["C-AMOUNT", "C-API", "C-INTEGRITY"]


def test_relaxed_statement_is_unapproved() -> None:
    m = _approved()
    m[1]["statement"] = "round each line first; close enough"
    with pytest.raises(ContractUnapproved, match="differs from the approved version"):
        approve_manifest(m)


def test_removed_protected_check_is_unapproved() -> None:
    m = _approved()
    m[1]["protected_check_ids"] = ["amount-boundary"]  # drops caller-consistency
    with pytest.raises(ContractUnapproved):
        approve_manifest(m)


def test_unknown_constraint_is_unapproved() -> None:
    m = _approved()
    m.append({**m[0], "constraint_id": "C-BOGUS"})
    with pytest.raises(ContractUnapproved, match="not an owner-approved"):
        approve_manifest(m)


def test_dropping_a_required_constraint_is_unapproved() -> None:
    with pytest.raises(ContractUnapproved, match="absent"):
        approve_manifest(_approved()[:2])


def test_malformed_proposal_is_invalid_input() -> None:
    with pytest.raises(ContractUnapproved, match="INVALID_INPUT"):
        approve_manifest([])
    with pytest.raises(ContractUnapproved, match="INVALID_INPUT"):
        approve_manifest([{"constraint_id": "C-API", "statement": 5}])


def test_required_check_without_oracle_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(registry.CHECK_REGISTRY, "amount-boundary")
    with pytest.raises(RequiredCheckMissing, match="C-AMOUNT -> amount-boundary"):
        ensure_registry_executable()
