"""Owner approval of contract manifests.

A repository may propose constraints (e.g. `.benchproof/contracts.json`); intake
treats them as untrusted. A proposal is accepted only when every constraint
hashes exactly to a registered, owner-approved record and every required
check has an executable trusted oracle.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from benchproof.constraints import contract_hash, get_constraint, list_constraints
from benchproof.domain import Constraint
from benchproof.evaluator.registry import missing_checks


class ContractUnapproved(Exception):
    """CONTRACT_UNAPPROVED: proposal differs from the owner-approved registry."""


class RequiredCheckMissing(Exception):
    """REQUIRED_CHECK_MISSING: a required constraint references a check with no trusted oracle."""


def ensure_registry_executable() -> None:
    """Fail fast if any registered required constraint lacks an executable check."""
    problems: list[str] = []
    for c in list_constraints():
        if c.required:
            for cid in missing_checks(c.protected_check_ids):
                problems.append(f"{c.constraint_id} -> {cid}")
    if problems:
        raise RequiredCheckMissing("; ".join(problems))


def proposed_constraint_hash(proposed: dict[str, Any]) -> str:
    """Canonical hash of a proposed constraint record (its own `hash` field is ignored)."""
    try:
        model = Constraint(**{k: v for k, v in proposed.items() if k != "hash"})
    except ValidationError as e:
        raise ContractUnapproved(f"INVALID_INPUT: {e.errors()[0]['msg']}") from e
    return model.compute_hash()


def approve_manifest(proposed: list[dict[str, Any]]) -> dict[str, Any]:
    """Accept a proposed manifest only if it is byte-for-byte the approved registry."""
    if not isinstance(proposed, list) or not proposed:
        raise ContractUnapproved("INVALID_INPUT: manifest must be a non-empty list")

    seen: set[str] = set()
    for item in proposed:
        cid = item.get("constraint_id") if isinstance(item, dict) else None
        if not cid:
            raise ContractUnapproved("INVALID_INPUT: constraint_id missing")
        registered = get_constraint(cid)
        if registered is None:
            raise ContractUnapproved(f"{cid} is not an owner-approved constraint")
        if proposed_constraint_hash(item) != registered.hash:
            raise ContractUnapproved(f"{cid} differs from the approved version {registered.version}")
        if item.get("required", True):
            gaps = missing_checks(item.get("protected_check_ids", []))
            if gaps:
                raise RequiredCheckMissing(f"{cid} -> {gaps}")
        seen.add(cid)

    required_ids = {c.constraint_id for c in list_constraints() if c.required}
    absent = sorted(required_ids - seen)
    if absent:
        raise ContractUnapproved(f"required constraints absent from proposal: {absent}")

    return {"contract_hash": contract_hash(), "approved_ids": sorted(seen)}
