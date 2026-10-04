"""Constraint registry — pins human-approved intent and check mappings.

The three initial constraints match the documented synthetic service:
  C-API       API compatibility (required public schema fields and status)
  C-AMOUNT    Exact amount boundary (Decimal rounding rule)
  C-INTEGRITY Cross-module caller/idempotency integrity
"""

from __future__ import annotations

from benchproof.domain import Constraint, _canonical_hash

# ── Approved constraint definitions ──────────────────────────────────────

C_API = Constraint(
    constraint_id="C-API",
    version=1,
    statement=(
        "ReceiptResponse must include receipt_id, tenant_id, request_id, "
        "total_amount (str) and status (str). POST /invoices must return 200 "
        "on valid input and 409 on idempotency conflict."
    ),
    scope=["app/schemas.py", "app/routes.py", "app/services.py"],
    required=True,
    protected_check_ids=["api-field-presence", "api-status-code"],
    approval_ref="OWNER_MANUAL_REVIEW",
)

C_AMOUNT = Constraint(
    constraint_id="C-AMOUNT",
    version=1,
    statement=(
        "Sum Decimal strings from line_amounts; round once on the invoice "
        "total using ROUND_HALF_UP; return exactly two decimal places. "
        "Example: 0.005 + 0.005 → 0.01, not 0.02."
    ),
    scope=["app/money.py", "app/services.py", "app/worker.py"],
    required=True,
    protected_check_ids=["amount-boundary", "caller-consistency"],
    approval_ref="OWNER_MANUAL_REVIEW",
)

C_INTEGRITY = Constraint(
    constraint_id="C-INTEGRITY",
    version=1,
    statement=(
        "Idempotency is tenant/request scoped. Identical payload returns "
        "the original receipt without double count. Same key / different "
        "payload returns a 409 conflict. Worker path uses the same "
        "process_invoice logic (not a bypass)."
    ),
    scope=["app/services.py", "app/worker.py", "app/repository.py"],
    required=True,
    protected_check_ids=["idempotency-duplicate", "idempotency-conflict", "worker-caller-path"],
    approval_ref="OWNER_MANUAL_REVIEW",
)


# ── Registry ─────────────────────────────────────────────────────────────

_CONSTRAINTS: dict[str, Constraint] = {}


def _register(c: Constraint) -> None:
    c.compute_hash()
    _CONSTRAINTS[c.constraint_id] = c


def _init_registry() -> None:
    for c in (C_API, C_AMOUNT, C_INTEGRITY):
        _register(c)


_init_registry()


def get_constraint(constraint_id: str) -> Constraint | None:
    return _CONSTRAINTS.get(constraint_id)


def list_constraints() -> list[Constraint]:
    return list(_CONSTRAINTS.values())


def contract_hash() -> str:
    """Hash of all registered constraints combined — the contract hash."""
    all_hashes = sorted(c.hash for c in _CONSTRAINTS.values())
    return _canonical_hash({"constraints": all_hashes})


def validate_required_checks(check_ids: set[str]) -> list[str]:
    """Return a list of missing required check IDs."""
    required = set()
    for c in _CONSTRAINTS.values():
        if c.required:
            required.update(c.protected_check_ids)
    return sorted(required - check_ids)
