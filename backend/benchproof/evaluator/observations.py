"""Observation-based evaluation: trusted checks over an untrusted observation record.

The launcher (runner/launcher/observe_invoice.py) reports what the candidate
did. This module decides what it should have done, using the constraint
definitions and trusted constants — never values reported by the candidate.
"""

from __future__ import annotations

import ast
from typing import Any

from benchproof.domain import CheckOutcome, CheckResult
from benchproof.evaluator import (
    check_amount_boundary,
    check_api_field_presence,
    check_api_status_code,
    check_caller_consistency,
    check_idempotency_conflict,
    check_idempotency_duplicate,
    check_worker_caller_path,
)

# Trusted inputs. The launcher uses the same values, but we never read them back from it.
BOUNDARY_LINES = ["0.005", "0.005"]
CONFLICT_LINES = ["1.00", "2.00"]


def worker_delegates_to_process_invoice(worker_source: str) -> bool:
    """Static check on trusted-side source: worker imports and calls services.process_invoice."""
    tree = ast.parse(worker_source)
    imported = called = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "services"
            and any(a.name == "process_invoice" for a in node.names)
        ):
            imported = True
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == "process_invoice") or (
                isinstance(f, ast.Attribute) and f.attr == "process_invoice"
            ):
                called = True
    return imported and called


def _unknown(check_id: str, reason: str) -> CheckResult:
    return CheckResult(check_id=check_id, outcome=CheckOutcome.UNKNOWN, oracle_kind="deterministic", reason=reason)


def evaluate_observations(obs: dict[str, Any] | None, worker_source: str | None) -> list[CheckResult]:
    """Map an observation record to the seven protected check results."""
    results: list[CheckResult] = []
    if not isinstance(obs, dict):
        reason = "no observations produced by the candidate run"
        return [_unknown(c, reason) for c in (
            "api-status-code", "api-field-presence", "amount-boundary",
            "idempotency-duplicate", "idempotency-conflict", "caller-consistency",
        )] + [_worker_path(worker_source)]

    if obs.get("error"):
        reason = f"candidate failed to load: {obs['error']}"
        results.extend(_unknown(c, reason) for c in (
            "api-status-code", "api-field-presence", "amount-boundary",
            "idempotency-duplicate", "idempotency-conflict", "caller-consistency",
        ))
        results.append(_worker_path(worker_source))
        return results

    route = obs.get("route") or {}
    first = route.get("first") or {}
    second = route.get("second") or {}
    conflict = route.get("conflict") or {}
    body = first.get("body") if isinstance(first.get("body"), dict) else {}

    status = first.get("status")
    results.append(
        check_api_status_code(status, 200) if isinstance(status, int)
        else _unknown("api-status-code", "no status observed")
    )
    results.append(check_api_field_presence(body))
    route_total = body.get("total_amount")
    results.append(check_amount_boundary(BOUNDARY_LINES, route_total if isinstance(route_total, str) else None))

    second_body = second.get("body") if second.get("status") == 200 and isinstance(second.get("body"), dict) else {}
    results.append(check_idempotency_duplicate(body, second_body))

    cstatus = conflict.get("status")
    results.append(
        check_idempotency_conflict(cstatus) if isinstance(cstatus, int)
        else _unknown("idempotency-conflict", "no conflict status observed")
    )

    stored = (obs.get("worker") or {}).get("stored_receipt")
    worker_total = None
    if isinstance(stored, dict) and isinstance(stored.get("response"), dict):
        wt = stored["response"].get("total_amount")
        worker_total = wt if isinstance(wt, str) else None
    results.append(check_caller_consistency(route_total if isinstance(route_total, str) else None, worker_total))

    results.append(_worker_path(worker_source))
    return results


def _worker_path(worker_source: str | None) -> CheckResult:
    if worker_source is None:
        return _unknown("worker-caller-path", "worker.py not available on the trusted side")
    try:
        return check_worker_caller_path(worker_delegates_to_process_invoice(worker_source))
    except SyntaxError as e:
        return _unknown("worker-caller-path", f"worker.py does not parse: {e.msg}")


def isolation_findings(obs: dict[str, Any] | None) -> dict[str, Any]:
    """Summarize the launcher's environment probes for the integrity record."""
    env = (obs or {}).get("environment") or {}
    net = env.get("network") or {}
    return {
        "secret_env_names": env.get("secret_env_names"),
        "trusted_assets_present": env.get("trusted_assets_present"),
        "internet_denied": (net.get("internet") or {}).get("denied"),
        "metadata_denied": (net.get("metadata") or {}).get("denied"),
        "candidate_writable": env.get("candidate_writable"),
        "python": env.get("python"),
    }
