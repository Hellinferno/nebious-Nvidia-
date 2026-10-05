"""Executable check registry — the only check ids a constraint may reference.

A required constraint whose protected_check_ids are not all present here has
no trusted oracle and must be rejected (REQUIRED_CHECK_MISSING).
"""

from __future__ import annotations

CHECK_REGISTRY: dict[str, dict[str, object]] = {
    "api-field-presence": {"version": 1, "oracle_kind": "deterministic", "constraint": "C-API"},
    "api-status-code": {"version": 1, "oracle_kind": "deterministic", "constraint": "C-API"},
    "amount-boundary": {"version": 1, "oracle_kind": "deterministic", "constraint": "C-AMOUNT"},
    "caller-consistency": {"version": 1, "oracle_kind": "deterministic", "constraint": "C-AMOUNT"},
    "idempotency-duplicate": {"version": 1, "oracle_kind": "deterministic", "constraint": "C-INTEGRITY"},
    "idempotency-conflict": {"version": 1, "oracle_kind": "deterministic", "constraint": "C-INTEGRITY"},
    "worker-caller-path": {"version": 1, "oracle_kind": "deterministic", "constraint": "C-INTEGRITY"},
}


def known_check_ids() -> set[str]:
    return set(CHECK_REGISTRY)


def missing_checks(check_ids: set[str] | list[str]) -> list[str]:
    return sorted(set(check_ids) - known_check_ids())
