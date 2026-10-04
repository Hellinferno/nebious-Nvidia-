"""Trusted evaluator — deterministic oracle checks for the synthetic service.

These checks run OUTSIDE the candidate runtime. Expected values come from
the constraint definitions, not from candidate output.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from benchproof.domain import CheckOutcome, CheckResult

# ── Oracle helpers ───────────────────────────────────────────────────────

def _expected_total(line_amounts: list[str]) -> str:
    """Trusted reference: sum then round once."""
    total = sum((Decimal(s) for s in line_amounts), Decimal(0))
    return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ── Individual checks ───────────────────────────────────────────────────

def check_api_field_presence(response_body: dict[str, Any]) -> CheckResult:
    """C-API: ReceiptResponse must include the required five fields."""
    required_fields = {"receipt_id", "tenant_id", "request_id", "total_amount", "status"}
    actual = set(response_body.keys())
    missing = required_fields - actual

    if missing:
        return CheckResult(
            check_id="api-field-presence",
            outcome=CheckOutcome.FAIL,
            oracle_kind="deterministic",
            reason=f"Missing required fields: {sorted(missing)}",
        )
    return CheckResult(
        check_id="api-field-presence",
        outcome=CheckOutcome.PASS_,
        oracle_kind="deterministic",
        reason="All required fields present",
    )


def check_api_status_code(status_code: int, expected: int) -> CheckResult:
    """C-API: verify HTTP status code matches expectation."""
    outcome = CheckOutcome.PASS_ if status_code == expected else CheckOutcome.FAIL
    return CheckResult(
        check_id="api-status-code",
        outcome=outcome,
        oracle_kind="deterministic",
        reason=f"Expected {expected}, got {status_code}",
    )


def check_amount_boundary(
    line_amounts: list[str], actual_total: str | None
) -> CheckResult:
    """C-AMOUNT: verify the total matches trusted reference."""
    expected = _expected_total(line_amounts)
    if actual_total is None:
        return CheckResult(
            check_id="amount-boundary",
            outcome=CheckOutcome.UNKNOWN,
            oracle_kind="deterministic",
            reason=f"Candidate returned no total_amount; expected {expected}",
        )
    if actual_total == expected:
        return CheckResult(
            check_id="amount-boundary",
            outcome=CheckOutcome.PASS_,
            oracle_kind="deterministic",
            reason=f"Total {actual_total} matches expected {expected}",
        )
    return CheckResult(
        check_id="amount-boundary",
        outcome=CheckOutcome.FAIL,
        oracle_kind="deterministic",
        reason=f"Total {actual_total} != expected {expected}",
    )


def check_caller_consistency(
    route_total: str | None, worker_total: str | None
) -> CheckResult:
    """C-AMOUNT / C-INTEGRITY: route and worker produce identical total."""
    if route_total is None or worker_total is None:
        return CheckResult(
            check_id="caller-consistency",
            outcome=CheckOutcome.UNKNOWN,
            oracle_kind="deterministic",
            reason=f"Missing total: route={route_total!r} worker={worker_total!r}",
        )
    if route_total == worker_total:
        return CheckResult(
            check_id="caller-consistency",
            outcome=CheckOutcome.PASS_,
            oracle_kind="deterministic",
            reason="Route and worker totals match",
        )
    return CheckResult(
        check_id="caller-consistency",
        outcome=CheckOutcome.FAIL,
        oracle_kind="deterministic",
        reason=f"Route total={route_total} vs worker total={worker_total}",
    )


def check_idempotency_duplicate(
    first_receipt: dict[str, Any],
    second_receipt: dict[str, Any],
) -> CheckResult:
    """C-INTEGRITY: identical re-submission returns original, no double count."""
    if first_receipt.get("receipt_id") == second_receipt.get("receipt_id"):
        return CheckResult(
            check_id="idempotency-duplicate",
            outcome=CheckOutcome.PASS_,
            oracle_kind="deterministic",
            reason="Same receipt_id on duplicate submission",
        )
    return CheckResult(
        check_id="idempotency-duplicate",
        outcome=CheckOutcome.FAIL,
        oracle_kind="deterministic",
        reason="Duplicate submission created new receipt_id",
    )


def check_idempotency_conflict(status_code: int) -> CheckResult:
    """C-INTEGRITY: same key / different payload returns 409."""
    outcome = CheckOutcome.PASS_ if status_code == 409 else CheckOutcome.FAIL
    return CheckResult(
        check_id="idempotency-conflict",
        outcome=outcome,
        oracle_kind="deterministic",
        reason=f"Expected 409 on conflict, got {status_code}",
    )


def check_worker_caller_path(worker_uses_process_invoice: bool) -> CheckResult:
    """C-INTEGRITY: worker must delegate to services.process_invoice, not bypass."""
    if worker_uses_process_invoice:
        return CheckResult(
            check_id="worker-caller-path",
            outcome=CheckOutcome.PASS_,
            oracle_kind="deterministic",
            reason="Worker delegates to process_invoice",
        )
    return CheckResult(
        check_id="worker-caller-path",
        outcome=CheckOutcome.FAIL,
        oracle_kind="deterministic",
        reason="Worker bypasses process_invoice — idempotency not enforced",
    )


# ── Gate ─────────────────────────────────────────────────────────────────

def run_gate(results: list[CheckResult], required_ids: set[str]) -> str:
    """Deterministic gate. Returns VERIFIED, REJECTED or INCONCLUSIVE.

    Any required FAIL -> REJECTED (a failure outranks an unknown).
    Any required check missing or UNKNOWN -> INCONCLUSIVE.
    VERIFIED only when every required check is present and PASS.
    Candidate output never reaches this function except as compared values.
    """
    results_by_id = {r.check_id: r for r in results}
    inconclusive = False
    for cid in sorted(required_ids):
        r = results_by_id.get(cid)
        if r is None or r.outcome == CheckOutcome.UNKNOWN:
            inconclusive = True
        elif r.outcome == CheckOutcome.FAIL:
            return "REJECTED"
    return "INCONCLUSIVE" if inconclusive else "VERIFIED"
