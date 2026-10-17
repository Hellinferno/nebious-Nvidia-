"""Reserve legacy diagnosis attempts before crossing the paid provider boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchproof.storage import _connect
from benchproof.storage.lifecycle import TERMINAL_STATES, _append_event_conn
from benchproof.trajectory import TrajectoryError


def reserve_diagnosis(
    audit_id: str,
    action_id: str,
    source_hash: str,
    context_hash: str,
    strategy: str,
    db_path: Path | None,
) -> dict[str, int]:
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        audit = conn.execute("SELECT * FROM audits WHERE audit_id=?", (audit_id,)).fetchone()
        if audit is None or audit["run_state"] in TERMINAL_STATES | {"CANCEL_PENDING", "STALLED"}:
            raise TrajectoryError("INVALID_STATE", "This audit cannot start another diagnosis")
        actions = conn.execute("SELECT status, elapsed_ms FROM actions WHERE audit_id=?", (audit_id,)).fetchall()
        if any(action["status"] == "in_flight" for action in actions):
            raise TrajectoryError(
                "INVALID_STATE", "A diagnosis is running or its interrupted result needs reconciliation"
            )
        limits = json.loads(audit["limits_json"])
        used_ms = sum(action["elapsed_ms"] for action in actions)
        remaining = {
            "max_actions": max(0, int(limits.get("max_actions", 15)) - len(actions)),
            "audit_deadline_s": max(0, int(limits.get("audit_deadline_s", 300)) - used_ms // 1000),
            "used_actions": len(actions),
            "used_elapsed_ms": used_ms,
        }
        if remaining["max_actions"] <= 0 or remaining["audit_deadline_s"] <= 0:
            raise TrajectoryError("BUDGET_EXHAUSTED", "Original audit action/time budget is exhausted")
        reserved = {**remaining, "max_actions": remaining["max_actions"] - 1, "used_actions": len(actions) + 1}
        conn.execute(
            """INSERT INTO actions
               (action_id, audit_id, role, tool, canonical_args_hash, source_hash,
                context_hash, strategy, remaining_limits, status, created_at)
               VALUES (?, ?, 'investigator', 'diagnose', ?, ?, ?, ?, ?, 'in_flight', ?)""",
            (action_id, audit_id, context_hash, source_hash, context_hash, strategy,
             json.dumps(reserved), datetime.now(UTC).isoformat()),
        )
        _append_event_conn(conn, audit_id, "action_started", {
            "action_id": action_id, "role": "investigator", "tool": "diagnose",
        })
        conn.commit()
        return remaining
    finally:
        conn.close()


def finish_diagnosis(
    *,
    action_id: str,
    audit_id: str,
    status: str,
    elapsed_ms: int,
    provider_metadata: dict[str, Any],
    db_path: Path | None,
    error_code: str | None = None,
    tool: str = "diagnose",
    canonical_args_hash: str = "",
    observation_ids: list[str] | None = None,
    failure_fingerprint: str | None = None,
    failure_category: str | None = None,
    observation_fingerprints: list[str] | None = None,
    remaining_limits: dict[str, int] | None = None,
) -> None:
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        updated = conn.execute(
            """UPDATE actions SET status=?, elapsed_ms=?, provider_meta=?, usage_json=?,
               tool=?, canonical_args_hash=?, observation_ids=?, failure_fingerprint=?,
               failure_category=?, observation_fps=?, remaining_limits=?
               WHERE action_id=? AND audit_id=? AND status='in_flight'""",
            (status, elapsed_ms, json.dumps(provider_metadata),
             json.dumps(provider_metadata.get("usage") or {}), tool, canonical_args_hash,
             json.dumps(observation_ids or []), failure_fingerprint, failure_category,
             json.dumps(observation_fingerprints or []), json.dumps(remaining_limits or {}),
             action_id, audit_id),
        )
        if updated.rowcount != 1:
            raise TrajectoryError("INVALID_STATE", "Diagnosis reservation is no longer in flight")
        if error_code:
            _append_event_conn(conn, audit_id, "action_failed", {
                "action_id": action_id, "code": error_code, "elapsed_ms": elapsed_ms,
                "provider_metadata": provider_metadata,
            })
        conn.commit()
    finally:
        conn.close()
