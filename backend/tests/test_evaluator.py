from __future__ import annotations

from benchproof.domain import CheckOutcome, CheckResult
from benchproof.evaluator import (
    _expected_total,
    check_amount_boundary,
    check_api_field_presence,
    check_idempotency_conflict,
    run_gate,
)

REQUIRED = {"a", "b"}


def _r(check_id: str, outcome: CheckOutcome) -> CheckResult:
    return CheckResult(check_id=check_id, outcome=outcome)


def test_trusted_total_rounds_once_on_the_sum() -> None:
    assert _expected_total(["0.005", "0.005"]) == "0.01"
    assert _expected_total(["1.005"]) == "1.01"
    assert _expected_total(["10", "0.1"]) == "10.10"
    assert _expected_total([]) == "0.00"


def test_amount_boundary_detects_premature_rounding() -> None:
    assert check_amount_boundary(["0.005", "0.005"], "0.01").outcome == CheckOutcome.PASS_
    assert check_amount_boundary(["0.005", "0.005"], "0.02").outcome == CheckOutcome.FAIL
    assert check_amount_boundary(["0.005", "0.005"], None).outcome == CheckOutcome.UNKNOWN


def test_field_presence_reports_missing_fields() -> None:
    ok = {"receipt_id": "x", "tenant_id": "t", "request_id": "r", "total_amount": "1.00", "status": "processed"}
    assert check_api_field_presence(ok).outcome == CheckOutcome.PASS_
    bad = check_api_field_presence({"receipt_id": "x", "amount": "1.00"})
    assert bad.outcome == CheckOutcome.FAIL
    assert "status" in bad.reason and "total_amount" in bad.reason


def test_conflict_requires_409() -> None:
    assert check_idempotency_conflict(409).outcome == CheckOutcome.PASS_
    assert check_idempotency_conflict(200).outcome == CheckOutcome.FAIL


def test_gate_verified_only_when_every_required_check_passes() -> None:
    assert run_gate([_r("a", CheckOutcome.PASS_), _r("b", CheckOutcome.PASS_)], REQUIRED) == "VERIFIED"


def test_gate_missing_required_check_is_inconclusive_not_verified() -> None:
    assert run_gate([_r("a", CheckOutcome.PASS_)], REQUIRED) == "INCONCLUSIVE"


def test_gate_unknown_required_check_is_inconclusive() -> None:
    assert run_gate([_r("a", CheckOutcome.PASS_), _r("b", CheckOutcome.UNKNOWN)], REQUIRED) == "INCONCLUSIVE"


def test_gate_failure_outranks_unknown() -> None:
    assert run_gate([_r("a", CheckOutcome.FAIL), _r("b", CheckOutcome.UNKNOWN)], REQUIRED) == "REJECTED"


def test_gate_ignores_extra_non_required_passes() -> None:
    results = [_r("a", CheckOutcome.PASS_), _r("b", CheckOutcome.FAIL), _r("forged", CheckOutcome.PASS_)]
    assert run_gate(results, REQUIRED) == "REJECTED"
