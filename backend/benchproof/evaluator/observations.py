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
)

# Trusted inputs. The launcher uses the same values, but we never read them back from it.
BOUNDARY_LINES = ["0.005", "0.005"]
CONFLICT_LINES = ["1.00", "2.00"]
WORKER_CALLER_PATH_VERSION = 2

_ROUTE_CHECKS = (
    "api-status-code",
    "api-field-presence",
    "amount-boundary",
    "idempotency-duplicate",
    "idempotency-conflict",
    "caller-consistency",
)


def _constant_false(test: ast.expr) -> bool:
    return isinstance(test, ast.Constant) and not test.value


class _WorkerDelegationVisitor(ast.NodeVisitor):
    """Find a live call to services.process_invoice inside a function body.

    Calls under constant-false branches (`if False:`, `while 0:`) and calls at
    module import time do not count: a candidate must not satisfy the caller
    path with dead code.
    """

    def __init__(self) -> None:
        self.imported = False
        self.live_call = False
        self._function_depth = 0

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if (module == "services" or module.endswith(".services")) and any(
            alias.name == "process_invoice" for alias in node.names
        ):
            self.imported = True
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if any(alias.name.endswith("services") for alias in node.names):
            self.imported = True
        self.generic_visit(node)

    def _visit_function(self, node: ast.AST) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_If(self, node: ast.If) -> None:
        if _constant_false(node.test):
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        if _constant_false(node.test):
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        named = (isinstance(func, ast.Name) and func.id == "process_invoice") or (
            isinstance(func, ast.Attribute) and func.attr == "process_invoice"
        )
        if named and self._function_depth > 0:
            self.live_call = True
        self.generic_visit(node)


def worker_delegates_to_process_invoice(worker_source: str) -> bool:
    """Static check on trusted-side source: the worker imports and *live-calls* services.process_invoice."""
    visitor = _WorkerDelegationVisitor()
    visitor.visit(ast.parse(worker_source))
    return visitor.imported and visitor.live_call


def _unknown(check_id: str, reason: str, version: int = 1) -> CheckResult:
    return CheckResult(
        check_id=check_id, check_version=version, outcome=CheckOutcome.UNKNOWN,
        oracle_kind="deterministic", reason=reason,
    )


def _receipt_identity(stored: Any) -> tuple[str, str] | None:
    if not isinstance(stored, dict) or not isinstance(stored.get("response"), dict):
        return None
    response = stored["response"]
    receipt_id = response.get("receipt_id")
    total = response.get("total_amount")
    if not isinstance(receipt_id, str) or not isinstance(total, str):
        return None
    return receipt_id, total


def evaluate_observations(obs: dict[str, Any] | None, worker_source: str | None) -> list[CheckResult]:
    """Map an observation record to the seven protected check results."""
    results: list[CheckResult] = []
    if not isinstance(obs, dict):
        reason = "no observations produced by the candidate run"
        return [_unknown(c, reason) for c in _ROUTE_CHECKS] + [_worker_path(worker_source, None)]

    if obs.get("error"):
        reason = f"candidate failed to load: {obs['error']}"
        results.extend(_unknown(c, reason) for c in _ROUTE_CHECKS)
        results.append(_worker_path(worker_source, None))
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

    worker = obs.get("worker") or {}
    stored = worker.get("stored_receipt")
    worker_total = None
    if isinstance(stored, dict) and isinstance(stored.get("response"), dict):
        wt = stored["response"].get("total_amount")
        worker_total = wt if isinstance(wt, str) else None
    results.append(check_caller_consistency(route_total if isinstance(route_total, str) else None, worker_total))

    results.append(_worker_path(worker_source, worker if isinstance(worker, dict) else None))
    return results


def _worker_path(worker_source: str | None, worker_obs: dict[str, Any] | None) -> CheckResult:
    """C-INTEGRITY worker caller path, v2.

    PASS requires both a live static delegation to `services.process_invoice`
    and observed worker idempotency: repeating the identical job keeps the
    stored receipt, and a conflicting payload for the same key does not replace
    it. A missing dynamic observation yields UNKNOWN, never PASS.
    """
    version = WORKER_CALLER_PATH_VERSION
    if worker_source is None:
        return _unknown("worker-caller-path", "worker.py not available on the trusted side", version)
    try:
        delegates = worker_delegates_to_process_invoice(worker_source)
    except SyntaxError as e:
        return _unknown("worker-caller-path", f"worker.py does not parse: {e.msg}", version)

    reasons: list[str] = []
    if not delegates:
        reasons.append("worker has no live call to services.process_invoice")

    dynamic: CheckOutcome
    if worker_obs is None or "repeat" not in worker_obs or "conflict" not in worker_obs:
        dynamic = CheckOutcome.UNKNOWN
        reasons.append("worker idempotency was not observed")
    else:
        first = _receipt_identity(worker_obs.get("stored_receipt"))
        repeat = _receipt_identity((worker_obs.get("repeat") or {}).get("stored_receipt"))
        conflict = _receipt_identity((worker_obs.get("conflict") or {}).get("stored_receipt"))
        if first is None:
            dynamic = CheckOutcome.UNKNOWN
            reasons.append("worker stored no receipt for the first job")
        elif repeat != first:
            dynamic = CheckOutcome.FAIL
            reasons.append("repeating the identical worker job replaced the stored receipt")
        elif conflict != first:
            dynamic = CheckOutcome.FAIL
            reasons.append("a conflicting worker payload replaced the stored receipt")
        else:
            dynamic = CheckOutcome.PASS_

    if not delegates or dynamic == CheckOutcome.FAIL:
        outcome = CheckOutcome.FAIL
    elif dynamic == CheckOutcome.UNKNOWN:
        outcome = CheckOutcome.UNKNOWN
    else:
        outcome = CheckOutcome.PASS_
    reason = "; ".join(reasons) if reasons else (
        "Worker delegates to process_invoice and keeps the stored receipt across repeat and conflict"
    )
    return CheckResult(
        check_id="worker-caller-path", check_version=version, outcome=outcome,
        oracle_kind="deterministic", reason=reason,
    )


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
