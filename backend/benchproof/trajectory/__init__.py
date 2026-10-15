"""Canonical action fingerprints, no-progress stopping, and one bounded recovery (B-15)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from benchproof.domain import RunState
from benchproof.storage import _connect, get_audit, list_actions, list_patches
from benchproof.storage.lifecycle import TERMINAL_STATES, append_event, transition

FINGERPRINT_RULE_VERSION = "trajectory-fingerprint-v1"
STALL_REPEAT_THRESHOLD = 2
RECOVERY_STRATEGY = "narrow_failure_probe"

_UNSTABLE_KEYS = {
    "action_id",
    "created_at",
    "request_id",
    "response_id",
    "run_id",
    "timestamp",
    "trace_id",
}
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_TIMESTAMP_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b")
_REQUEST_ID_RE = re.compile(r"\b(?:req|request|response|trace|run|action)[-_][A-Za-z0-9_-]{6,}\b", re.IGNORECASE)


class TrajectoryError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class TraceStep(BaseModel):
    source_hash: str
    role: str = "investigator"
    tool: str
    strategy: str = "broad_diagnosis"
    arguments: dict[str, Any] = Field(default_factory=dict)
    failure_category: str
    failed_check_ids: list[str] = Field(default_factory=list)
    affected_constraints: list[str] = Field(default_factory=list)
    salient_detail: str = ""
    observation_fingerprints: list[str] = Field(default_factory=list)
    resolved_check_ids: list[str] = Field(default_factory=list)


def normalize_unstable(value: Any) -> Any:
    """Remove request-local IDs/timestamps while retaining meaningful failure details."""
    if isinstance(value, dict):
        return {
            key: normalize_unstable(item)
            for key, item in sorted(value.items())
            if key.lower() not in _UNSTABLE_KEYS
        }
    if isinstance(value, list):
        return [normalize_unstable(item) for item in value]
    if isinstance(value, str):
        normalized = _UUID_RE.sub("<uuid>", value)
        normalized = _TIMESTAMP_RE.sub("<timestamp>", normalized)
        return _REQUEST_ID_RE.sub("<request-id>", normalized)
    return value


def _canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(normalize_unstable(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def action_fingerprint(
    *,
    role: str,
    tool: str,
    strategy: str,
    arguments: dict[str, Any],
) -> str:
    return f"{FINGERPRINT_RULE_VERSION}:{_canonical_hash({'role': role, 'tool': tool, 'strategy': strategy, 'arguments': arguments})}"


def failure_fingerprint(
    *,
    category: str,
    failed_check_ids: list[str],
    affected_constraints: list[str],
    salient_detail: str,
) -> str:
    return f"{FINGERPRINT_RULE_VERSION}:{_canonical_hash({'category': category, 'failed_check_ids': sorted(set(failed_check_ids)), 'affected_constraints': sorted(set(affected_constraints)), 'salient_detail': salient_detail})}"


def observation_fingerprints(
    failed_check_ids: list[str],
    check_results: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Build stable semantic observations; generated row/request IDs never imply progress."""
    if check_results:
        return sorted(
            _canonical_hash(
                {
                    "check_id": item.get("check_id"),
                    "outcome": getattr(item.get("outcome"), "value", item.get("outcome")),
                    "reason": item.get("reason", ""),
                }
            )
            for item in check_results
        )
    return sorted(_canonical_hash({"check_id": check_id, "outcome": "FAIL"}) for check_id in failed_check_ids)


def materialize_trace_step(step: TraceStep) -> dict[str, Any]:
    return {
        **step.model_dump(),
        "action_fingerprint": action_fingerprint(
            role=step.role,
            tool=step.tool,
            strategy=step.strategy,
            arguments=step.arguments,
        ),
        "failure_fingerprint": failure_fingerprint(
            category=step.failure_category,
            failed_check_ids=step.failed_check_ids,
            affected_constraints=step.affected_constraints,
            salient_detail=step.salient_detail,
        ),
    }


def classify_trace(steps: list[TraceStep]) -> dict[str, Any]:
    """Classify the first true two-attempt no-progress repetition, if any."""
    materialized = [materialize_trace_step(step) for step in steps]
    for index in range(1, len(materialized)):
        previous = materialized[index - 1]
        current = materialized[index]
        new_observations = set(current["observation_fingerprints"]) - set(previous["observation_fingerprints"])
        resolved = set(current["resolved_check_ids"])
        same_triplet = (
            current["source_hash"] == previous["source_hash"]
            and current["action_fingerprint"] == previous["action_fingerprint"]
            and current["failure_fingerprint"] == previous["failure_fingerprint"]
        )
        if same_triplet and not new_observations and not resolved:
            return {
                "classification": "STALLED",
                "stall_index": index,
                "rule_version": FINGERPRINT_RULE_VERSION,
                "repeat_threshold": STALL_REPEAT_THRESHOLD,
                "reason": "same source/action/failure fingerprints with no new relevant observation",
                "steps": materialized,
            }
    return {
        "classification": "PROGRESSING",
        "stall_index": None,
        "rule_version": FINGERPRINT_RULE_VERSION,
        "repeat_threshold": STALL_REPEAT_THRESHOLD,
        "reason": "source, intent, failure, or relevant evidence changed",
        "steps": materialized,
    }


def budget_snapshot(audit_id: str, db_path: Path | None = None) -> dict[str, int]:
    audit = get_audit(audit_id, db_path)
    if audit is None:
        raise TrajectoryError("INVALID_INPUT", "Audit not found")
    limits = json.loads(audit.get("limits_json") or "{}")
    reservations = json.loads(audit.get("reservations") or "{}")
    actions = list_actions(audit_id, db_path)
    patches = list_patches(audit_id, db_path)
    used_elapsed_ms = sum(int(action.get("elapsed_ms") or 0) for action in actions)
    return {
        "max_actions": max(0, int(limits.get("max_actions", 15)) - len(actions)),
        "max_patches": max(0, int(limits.get("max_patches", 5)) - len(patches)),
        "max_executions": max(
            0,
            int(limits.get("max_executions", 12))
            - int(reservations.get("mutation_executions", 0)),
        ),
        "process_timeout_s": int(limits.get("process_timeout_s", 60)),
        "audit_deadline_s": max(
            0,
            int(limits.get("audit_deadline_s", 300)) - (used_elapsed_ms // 1000),
        ),
        "used_actions": len(actions),
        "used_patches": len(patches),
        "used_executions": int(reservations.get("mutation_executions", 0)),
        "used_elapsed_ms": used_elapsed_ms,
    }


def ensure_action_budget(audit_id: str, db_path: Path | None = None) -> dict[str, int]:
    remaining = budget_snapshot(audit_id, db_path)
    if remaining["max_actions"] <= 0 or remaining["audit_deadline_s"] <= 0:
        audit = get_audit(audit_id, db_path)
        if (
            audit
            and audit["run_state"] not in TERMINAL_STATES
            and audit["run_state"] != RunState.CANCEL_PENDING.value
        ):
            transition(
                audit_id,
                {audit["run_state"]},
                RunState.BLOCKED,
                db_path,
                reason="original audit budget exhausted",
            )
        append_event(audit_id, "budget_exhausted", remaining, db_path=db_path)
        raise TrajectoryError("BUDGET_EXHAUSTED", "Original audit action/time budget is exhausted")
    return remaining


def recovery_state(audit_id: str, db_path: Path | None = None) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path)
    if audit is None:
        raise TrajectoryError("INVALID_INPUT", "Audit not found")
    reservations = json.loads(audit.get("reservations") or "{}")
    return {
        "recovery_count": int(reservations.get("recovery_count", 0)),
        "recovery_strategy": reservations.get("recovery_strategy"),
        "remaining_limits": budget_snapshot(audit_id, db_path),
    }


def reserve_recovery(audit_id: str, db_path: Path | None = None) -> dict[str, Any]:
    """Atomically consume the single recovery without altering original limits/counters."""
    remaining = ensure_action_budget(audit_id, db_path)
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT run_state, reservations, limits_json FROM audits WHERE audit_id=?",
            (audit_id,),
        ).fetchone()
        if row is None:
            conn.execute("ROLLBACK")
            raise TrajectoryError("INVALID_INPUT", "Audit not found")
        reservations = json.loads(row["reservations"] or "{}")
        if row["run_state"] != RunState.STALLED.value:
            conn.execute("ROLLBACK")
            raise TrajectoryError("INVALID_STATE", "Recovery requires a STALLED audit")
        if int(reservations.get("recovery_count", 0)) >= 1:
            conn.execute("ROLLBACK")
            raise TrajectoryError("RECOVERY_EXHAUSTED", "The single recovery has already been used")
        reservations["recovery_count"] = 1
        reservations["recovery_strategy"] = RECOVERY_STRATEGY
        reservations["recovery_started_with"] = remaining
        conn.execute(
            "UPDATE audits SET run_state=?, reservations=? WHERE audit_id=?",
            (RunState.ANALYZING.value, json.dumps(reservations, sort_keys=True), audit_id),
        )
        conn.execute("COMMIT")
    finally:
        conn.close()
    append_event(
        audit_id,
        "state_changed",
        {"to": RunState.ANALYZING.value, "reason": "single bounded recovery"},
        db_path=db_path,
    )
    append_event(
        audit_id,
        "recovery_started",
        {
            "strategy": RECOVERY_STRATEGY,
            "strategy_change": "broad diagnosis -> narrower failing-check probe",
            "remaining_limits": remaining,
            "counters_reset": False,
        },
        db_path=db_path,
    )
    return recovery_state(audit_id, db_path)


def apply_stall_policy(audit_id: str, db_path: Path | None = None) -> dict[str, Any]:
    actions = [action for action in list_actions(audit_id, db_path) if action["status"] == "completed"]
    if len(actions) < STALL_REPEAT_THRESHOLD:
        return {"outcome": "PROGRESSING", **recovery_state(audit_id, db_path)}

    previous, current = actions[-2:]
    new_observations = set(current["observation_fingerprints"]) - set(previous["observation_fingerprints"])
    repeated = (
        current["source_hash"] == previous["source_hash"]
        and current["canonical_args_hash"] == previous["canonical_args_hash"]
        and current["failure_fingerprint"] == previous["failure_fingerprint"]
        and not new_observations
    )
    if not repeated:
        return {"outcome": "PROGRESSING", **recovery_state(audit_id, db_path)}

    state = recovery_state(audit_id, db_path)
    audit = get_audit(audit_id, db_path)
    if audit is None:
        raise TrajectoryError("INVALID_INPUT", "Audit not found")
    if audit["run_state"] in TERMINAL_STATES or audit["run_state"] == RunState.CANCEL_PENDING.value:
        # A cancelled or cancel-pending audit keeps its state; the stall is still visible in actions.
        return {"outcome": audit["run_state"], **state}
    append_event(
        audit_id,
        "stalled",
        {
            "action_ids": [previous["action_id"], current["action_id"]],
            "source_hash": current["source_hash"],
            "action_fingerprint": current["canonical_args_hash"],
            "failure_fingerprint": current["failure_fingerprint"],
            "rule_version": FINGERPRINT_RULE_VERSION,
            "new_relevant_observations": [],
        },
        db_path=db_path,
    )
    target = RunState.BLOCKED if state["recovery_count"] >= 1 else RunState.STALLED
    moved = transition(
        audit_id,
        {audit["run_state"]},
        target,
        db_path,
        reason="second no-progress stall" if target == RunState.BLOCKED else "repeated no-progress fingerprint",
    )
    if not moved:
        current = get_audit(audit_id, db_path)
        return {"outcome": current["run_state"] if current else "UNKNOWN", **state}
    if target == RunState.BLOCKED:
        append_event(
            audit_id,
            "blocked",
            {"reason": "second stall after the single recovery", "recovery_count": 1},
            db_path=db_path,
        )
    return {"outcome": target.value, **recovery_state(audit_id, db_path)}
