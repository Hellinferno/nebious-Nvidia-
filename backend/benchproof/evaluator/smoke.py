"""Visible smoke gate (baseline B0).

These checks are deliberately weak and fully public: they confirm that the
candidate loads, that the submit route answers with a success status and a
receipt identifier, and that the worker path runs without raising. They do
not test the rounding boundary, idempotency replay/conflict semantics, or the
worker caller path. The frozen V12 comparison measures what the protected
gate catches that this gate accepts.

The smoke gate reads the same untrusted observation record as the protected
oracle; it never consults candidate-reported verdicts.
"""

from __future__ import annotations

from typing import Any

from benchproof.domain import CheckOutcome, CheckResult

SMOKE_VERSION = "visible-smoke-v1"
SMOKE_CHECK_IDS: tuple[str, ...] = (
    "smoke-candidate-loads",
    "smoke-route-2xx",
    "smoke-receipt-id",
    "smoke-worker-runs",
)
_ORACLE = "visible-smoke"


def _result(check_id: str, outcome: CheckOutcome, reason: str) -> CheckResult:
    return CheckResult(check_id=check_id, outcome=outcome, oracle_kind=_ORACLE, reason=reason)


def evaluate_smoke(obs: dict[str, Any] | None) -> list[CheckResult]:
    """Map an observation record to the four visible smoke results."""
    if not isinstance(obs, dict):
        return [_result(cid, CheckOutcome.UNKNOWN, "no observations produced") for cid in SMOKE_CHECK_IDS]

    results: list[CheckResult] = []
    load_error = obs.get("error")
    if load_error:
        results.append(_result("smoke-candidate-loads", CheckOutcome.FAIL, f"candidate failed to load: {load_error}"))
        results.extend(
            _result(cid, CheckOutcome.UNKNOWN, "candidate did not load") for cid in SMOKE_CHECK_IDS[1:]
        )
        return results
    results.append(_result("smoke-candidate-loads", CheckOutcome.PASS_, "candidate package imported"))

    first = (obs.get("route") or {}).get("first") or {}
    status = first.get("status")
    if isinstance(status, int):
        ok = 200 <= status < 300
        results.append(
            _result(
                "smoke-route-2xx",
                CheckOutcome.PASS_ if ok else CheckOutcome.FAIL,
                f"POST /invoices answered {status}",
            )
        )
    else:
        results.append(_result("smoke-route-2xx", CheckOutcome.UNKNOWN, "no route status observed"))

    body = first.get("body") if isinstance(first.get("body"), dict) else None
    if body is None:
        results.append(_result("smoke-receipt-id", CheckOutcome.UNKNOWN, "no JSON body observed"))
    elif isinstance(body.get("receipt_id"), str) and body["receipt_id"]:
        results.append(_result("smoke-receipt-id", CheckOutcome.PASS_, "response carries a receipt_id"))
    else:
        results.append(_result("smoke-receipt-id", CheckOutcome.FAIL, "response has no receipt_id"))

    worker = obs.get("worker") or {}
    if "error" not in worker and "stored_receipt" not in worker:
        results.append(_result("smoke-worker-runs", CheckOutcome.UNKNOWN, "worker path was not observed"))
    elif worker.get("error"):
        results.append(_result("smoke-worker-runs", CheckOutcome.FAIL, f"worker raised: {worker['error']}"))
    else:
        results.append(_result("smoke-worker-runs", CheckOutcome.PASS_, "worker job completed without raising"))
    return results


def smoke_verdict(results: list[CheckResult]) -> str:
    """PASS only when every visible check passed; any FAIL is FAIL; otherwise UNKNOWN."""
    outcomes = {r.outcome for r in results}
    if CheckOutcome.FAIL in outcomes:
        return "FAIL"
    if CheckOutcome.UNKNOWN in outcomes or len(results) != len(SMOKE_CHECK_IDS):
        return "UNKNOWN"
    return "PASS"


def smoke_summary(obs: dict[str, Any] | None) -> dict[str, Any]:
    results = evaluate_smoke(obs)
    return {
        "smoke_version": SMOKE_VERSION,
        "verdict": smoke_verdict(results),
        "checks": [r.model_dump() for r in results],
        "failing_checks": sorted(r.check_id for r in results if r.outcome == CheckOutcome.FAIL),
    }
