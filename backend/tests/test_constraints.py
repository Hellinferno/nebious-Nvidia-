from __future__ import annotations

from benchproof.constraints import (
    contract_hash,
    get_constraint,
    list_constraints,
    validate_required_checks,
)
from benchproof.domain import Constraint


def test_registry_has_three_required_constraints_with_hashes() -> None:
    cs = list_constraints()
    assert [c.constraint_id for c in cs] == ["C-API", "C-AMOUNT", "C-INTEGRITY"]
    for c in cs:
        assert c.required is True
        assert c.protected_check_ids, c.constraint_id
        assert len(c.hash) == 64
        assert c.approval_ref == "OWNER_MANUAL_REVIEW"


def test_constraint_hash_is_canonical_and_excludes_itself() -> None:
    c = get_constraint("C-AMOUNT")
    assert c is not None
    recomputed = Constraint(**c.model_dump(exclude={"hash"})).compute_hash()
    assert recomputed == c.hash
    changed = Constraint(**{**c.model_dump(exclude={"hash"}), "statement": "relaxed"}).compute_hash()
    assert changed != c.hash


def test_contract_hash_is_stable_across_calls() -> None:
    assert contract_hash() == contract_hash()
    assert len(contract_hash()) == 64


def test_missing_required_checks_are_reported() -> None:
    all_ids = {cid for c in list_constraints() for cid in c.protected_check_ids}
    assert validate_required_checks(all_ids) == []
    missing = validate_required_checks(all_ids - {"amount-boundary", "worker-caller-path"})
    assert missing == ["amount-boundary", "worker-caller-path"]
