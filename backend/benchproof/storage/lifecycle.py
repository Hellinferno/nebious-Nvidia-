"""Durable run lifecycle: leases, conditional transitions, ordered events,
immutable check results/artifacts, evaluator-only verdict authority, idempotency keys.

All writes are conditional (compare-and-swap) or insert-only so a lost worker,
a replayed POST or a candidate-controlled process cannot forge or duplicate
state. SQLite triggers make check_results and artifacts immutable at the
engine level, independent of application code.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from benchproof.domain import (
    Artifact,
    AuditRecord,
    CheckOutcome,
    CheckResult,
    GateVerdict,
    RunState,
)
from benchproof.storage import _connect

TRUSTED_EVALUATOR = "trusted-evaluator"

TERMINAL_STATES = {
    RunState.COMPLETED.value,
    RunState.FAILED.value,
    RunState.CANCELLED.value,
    RunState.TIMED_OUT.value,
    RunState.BLOCKED.value,
}


class VerdictAuthorityError(Exception):
    """Only the trusted evaluator may write check results or verdicts."""


class ImmutableRecordError(Exception):
    """An attempt to overwrite an immutable record."""


class TransitionRejected(Exception):
    """Compare-and-swap transition did not match the current state."""


def _now() -> datetime:
    return datetime.now(UTC)


def migrate_lifecycle(db_path: Path | None = None) -> None:
    conn = _connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS leases (
            audit_id    TEXT PRIMARY KEY REFERENCES audits(audit_id),
            worker_id   TEXT NOT NULL,
            acquired_at TEXT NOT NULL,
            expires_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS idempotency_keys (
            owner_ref     TEXT NOT NULL,
            endpoint      TEXT NOT NULL,
            idem_key      TEXT NOT NULL,
            body_hash     TEXT NOT NULL,
            audit_id      TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            PRIMARY KEY (owner_ref, endpoint, idem_key)
        );

        CREATE TRIGGER IF NOT EXISTS check_results_no_update BEFORE UPDATE ON check_results
        BEGIN SELECT RAISE(ABORT, 'check_results are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS check_results_no_delete BEFORE DELETE ON check_results
        BEGIN SELECT RAISE(ABORT, 'check_results are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS artifacts_no_update BEFORE UPDATE ON artifacts
        BEGIN SELECT RAISE(ABORT, 'artifacts are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS artifacts_no_delete BEFORE DELETE ON artifacts
        BEGIN SELECT RAISE(ABORT, 'artifacts are immutable'); END;
        """
    )
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(check_results)")}
    additions = {
        "written_by": "ALTER TABLE check_results ADD COLUMN written_by TEXT NOT NULL DEFAULT 'trusted-evaluator'",
        "patch_id": "ALTER TABLE check_results ADD COLUMN patch_id TEXT",
        "patch_hash": "ALTER TABLE check_results ADD COLUMN patch_hash TEXT",
        "image_hash": "ALTER TABLE check_results ADD COLUMN image_hash TEXT NOT NULL DEFAULT ''",
    }
    for column, statement in additions.items():
        if column not in cols:
            conn.execute(statement)
    conn.commit()
    conn.close()


class IdempotencyConflict(Exception):
    """The same Idempotency-Key was reused with a different request body."""


# ── Leases ───────────────────────────────────────────────────────────────

def acquire_lease(audit_id: str, worker_id: str, ttl_s: int = 60, db_path: Path | None = None) -> bool:
    """Exactly one live lease per audit. Returns True if this worker holds it."""
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT worker_id, expires_at FROM leases WHERE audit_id=?", (audit_id,)).fetchone()
        now = _now()
        if row is not None:
            expired = datetime.fromisoformat(row["expires_at"]) <= now
            if row["worker_id"] != worker_id and not expired:
                conn.execute("ROLLBACK")
                return False
        expires = (now + timedelta(seconds=ttl_s)).isoformat()
        conn.execute(
            """INSERT INTO leases (audit_id, worker_id, acquired_at, expires_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(audit_id) DO UPDATE SET worker_id=excluded.worker_id,
               acquired_at=excluded.acquired_at, expires_at=excluded.expires_at""",
            (audit_id, worker_id, now.isoformat(), expires),
        )
        conn.execute("COMMIT")
        return True
    finally:
        conn.close()


def release_lease(audit_id: str, worker_id: str, db_path: Path | None = None) -> bool:
    conn = _connect(db_path)
    cur = conn.execute("DELETE FROM leases WHERE audit_id=? AND worker_id=?", (audit_id, worker_id))
    conn.commit()
    conn.close()
    return cur.rowcount == 1


def lease_holder(audit_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    conn = _connect(db_path)
    row = conn.execute("SELECT * FROM leases WHERE audit_id=?", (audit_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Events ───────────────────────────────────────────────────────────────

def _append_event_conn(
    conn: sqlite3.Connection,
    audit_id: str,
    event_type: str,
    payload: dict[str, Any] | None,
    attempt: int = 1,
) -> int:
    """Insert one event inside the caller's open transaction and return its sequence."""
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) AS s FROM events WHERE audit_id=? AND attempt=?",
        (audit_id, attempt),
    ).fetchone()
    seq = int(row["s"]) + 1
    conn.execute(
        """INSERT INTO events (audit_id, attempt, sequence, event_type, payload, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (audit_id, attempt, seq, event_type, json.dumps(payload or {}, sort_keys=True), _now().isoformat()),
    )
    return seq


def append_event(
    audit_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    attempt: int = 1,
    db_path: Path | None = None,
) -> int:
    """Append with a per-audit monotonically increasing sequence. Returns the sequence."""
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        seq = _append_event_conn(conn, audit_id, event_type, payload, attempt)
        conn.execute("COMMIT")
        return seq
    finally:
        conn.close()


def list_events(audit_id: str, after: int = 0, db_path: Path | None = None) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    rows = conn.execute(
        """SELECT sequence, attempt, event_type, payload, created_at FROM events
           WHERE audit_id=? AND sequence>? ORDER BY attempt, sequence""",
        (audit_id, after),
    ).fetchall()
    conn.close()
    return [
        {
            "sequence": r["sequence"],
            "attempt": r["attempt"],
            "event_type": r["event_type"],
            "payload": json.loads(r["payload"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# ── Transitions ──────────────────────────────────────────────────────────

def transition(
    audit_id: str,
    from_states: set[RunState] | set[str],
    to_state: RunState,
    db_path: Path | None = None,
    reason: str | None = None,
) -> bool:
    """Compare-and-swap run_state. Emits state_changed on success; returns False if CAS missed."""
    allowed = tuple(s.value if isinstance(s, RunState) else s for s in from_states)
    conn = _connect(db_path)
    placeholders = ",".join("?" for _ in allowed)
    try:
        # The state write and its event commit together, so a reader that sees the new
        # state can never miss the state_changed event (and the SSE end frame cannot
        # overtake it).
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            f"UPDATE audits SET run_state=? WHERE audit_id=? AND run_state IN ({placeholders})",
            (to_state.value, audit_id, *allowed),
        )
        if cur.rowcount != 1:
            conn.execute("ROLLBACK")
            return False
        _append_event_conn(conn, audit_id, "state_changed", {"to": to_state.value, "reason": reason})
        conn.execute("COMMIT")
        return True
    finally:
        conn.close()


def request_cancellation(
    audit_id: str,
    *,
    remote_reconciliation_required: bool,
    db_path: Path | None = None,
) -> RunState:
    """Durably request cancellation without claiming an active remote run has stopped."""
    target = RunState.CANCEL_PENDING if remote_reconciliation_required else RunState.CANCELLED
    cancellable = {s.value for s in RunState} - TERMINAL_STATES - {RunState.CANCEL_PENDING.value}
    if not transition(audit_id, cancellable, target, db_path=db_path, reason="owner request"):
        conn = _connect(db_path)
        row = conn.execute("SELECT run_state FROM audits WHERE audit_id=?", (audit_id,)).fetchone()
        conn.close()
        current = row["run_state"] if row else "UNKNOWN"
        if current == RunState.CANCEL_PENDING.value:
            return RunState.CANCEL_PENDING
        raise TransitionRejected(f"audit is already in state {current}")
    append_event(
        audit_id,
        "cancel_pending" if remote_reconciliation_required else "cancelled",
        {
            "remote_reconciliation": (
                "required" if remote_reconciliation_required else "not applicable"
            )
        },
        db_path=db_path,
    )
    return target


def reconcile_cancellation(
    audit_id: str,
    *,
    remote_terminated: bool,
    db_path: Path | None = None,
) -> bool:
    """Worker-side reconciliation: only confirmed remote termination becomes CANCELLED."""
    if not remote_terminated:
        return False
    if not transition(
        audit_id,
        {RunState.CANCEL_PENDING},
        RunState.CANCELLED,
        db_path=db_path,
        reason="remote termination confirmed",
    ):
        return False
    append_event(
        audit_id,
        "cancelled",
        {"remote_reconciliation": "confirmed"},
        db_path=db_path,
    )
    return True


# ── Immutable results and verdict authority ──────────────────────────────

def _insert_check_result(conn: sqlite3.Connection, audit_id: str, result: CheckResult, author: str, attempt: int) -> None:
    conn.execute(
        """INSERT INTO check_results
           (check_id, audit_id, attempt, check_version, outcome, oracle_kind, reason, duration_ms,
            source_hash, contract_hash, evaluator_hash, created_at, written_by,
            patch_id, patch_hash, image_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            result.check_id, audit_id, attempt, result.check_version, result.outcome.value,
            result.oracle_kind, result.reason, result.duration_ms, result.source_hash,
            result.contract_hash, result.evaluator_hash, _now().isoformat(), author,
            result.patch_id, result.patch_hash, result.image_hash or "",
        ),
    )


def record_check_result(
    audit_id: str,
    result: CheckResult,
    author: str,
    attempt: int = 1,
    db_path: Path | None = None,
) -> None:
    if author != TRUSTED_EVALUATOR:
        raise VerdictAuthorityError(f"{author!r} may not write check results")
    conn = _connect(db_path)
    try:
        _insert_check_result(conn, audit_id, result, author, attempt)
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise ImmutableRecordError(f"check result {result.check_id} already recorded") from e
    finally:
        conn.close()


def record_check_results(
    audit_id: str,
    results: list[CheckResult],
    author: str,
    attempt: int,
    db_path: Path | None = None,
) -> None:
    """Record one verification attempt's complete check set in a single transaction.

    Either every check of the attempt is stored or none is, so a partially
    written attempt can never leave an audit permanently unverifiable.
    """
    if author != TRUSTED_EVALUATOR:
        raise VerdictAuthorityError(f"{author!r} may not write check results")
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for result in results:
            _insert_check_result(conn, audit_id, result, author, attempt)
        conn.execute("COMMIT")
    except sqlite3.IntegrityError as e:
        conn.execute("ROLLBACK")
        raise ImmutableRecordError(f"verification attempt {attempt} already recorded") from e
    finally:
        conn.close()


def latest_check_attempt(audit_id: str, db_path: Path | None = None) -> int:
    """Highest recorded verification attempt for the audit (0 when none)."""
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT COALESCE(MAX(attempt), 0) AS a FROM check_results WHERE audit_id=?", (audit_id,)
    ).fetchone()
    conn.close()
    return int(row["a"])


def next_check_attempt(audit_id: str, db_path: Path | None = None) -> int:
    return latest_check_attempt(audit_id, db_path) + 1


def list_check_results(
    audit_id: str, attempt: int | None = None, db_path: Path | None = None
) -> list[dict[str, Any]]:
    """Check results of one verification attempt; the latest attempt when none is given."""
    if attempt is None:
        attempt = latest_check_attempt(audit_id, db_path)
        if attempt == 0:
            return []
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT * FROM check_results WHERE audit_id=? AND attempt=? ORDER BY check_id", (audit_id, attempt)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_verdict(
    audit_id: str,
    verdict: GateVerdict,
    author: str,
    required_check_ids: set[str],
    attempt: int = 1,
    db_path: Path | None = None,
) -> None:
    """Write gate_verdict once, only by the trusted evaluator, and only if it matches stored checks."""
    if author != TRUSTED_EVALUATOR:
        raise VerdictAuthorityError(f"{author!r} may not write a verdict")
    stored = {r["check_id"]: r["outcome"] for r in list_check_results(audit_id, attempt, db_path)}
    computed = GateVerdict.VERIFIED
    for cid in sorted(required_check_ids):
        out = stored.get(cid)
        if out == CheckOutcome.FAIL.value:
            computed = GateVerdict.REJECTED
            break
        if out is None or out == CheckOutcome.UNKNOWN.value:
            computed = GateVerdict.INCONCLUSIVE
    if verdict != computed:
        raise VerdictAuthorityError(f"verdict {verdict.value} does not match stored checks ({computed.value})")
    conn = _connect(db_path)
    cur = conn.execute(
        "UPDATE audits SET gate_verdict=? WHERE audit_id=? AND gate_verdict=?",
        (verdict.value, audit_id, GateVerdict.PENDING.value),
    )
    conn.commit()
    conn.close()
    if cur.rowcount != 1:
        raise ImmutableRecordError("verdict already recorded for this audit")
    append_event(audit_id, "verification_completed", {"gate_verdict": verdict.value}, db_path=db_path)


def record_artifact(artifact: Artifact, db_path: Path | None = None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO artifacts (artifact_id, owner, audit_id, attempt, relative_name, mime_type,
                                      byte_size, sha256, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                artifact.artifact_id, artifact.owner, artifact.audit_id, artifact.attempt,
                artifact.relative_name, artifact.mime_type, artifact.byte_size, artifact.sha256,
                artifact.visibility,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise ImmutableRecordError(f"artifact {artifact.artifact_id} already recorded") from e
    finally:
        conn.close()


# ── Idempotency ──────────────────────────────────────────────────────────

def body_hash(body: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def idempotency_get(owner_ref: str, endpoint: str, key: str, db_path: Path | None = None) -> dict[str, Any] | None:
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT * FROM idempotency_keys WHERE owner_ref=? AND endpoint=? AND idem_key=?",
        (owner_ref, endpoint, key),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["response"] = json.loads(d.pop("response_json"))
    return d


def idempotency_put(
    owner_ref: str,
    endpoint: str,
    key: str,
    bhash: str,
    audit_id: str,
    response: dict[str, Any],
    db_path: Path | None = None,
) -> None:
    conn = _connect(db_path)
    conn.execute(
        """INSERT OR IGNORE INTO idempotency_keys
           (owner_ref, endpoint, idem_key, body_hash, audit_id, response_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (owner_ref, endpoint, key, bhash, audit_id, json.dumps(response, sort_keys=True), _now().isoformat()),
    )
    conn.commit()
    conn.close()


def create_audit_idempotent(
    owner_ref: str,
    endpoint: str,
    key: str,
    bhash: str,
    audit: AuditRecord,
    response: dict[str, Any],
    db_path: Path | None = None,
) -> tuple[dict[str, Any], bool]:
    """Create the audit and its idempotency record in one serialized transaction.

    Returns (response, replayed). Two concurrent requests with the same key are
    serialized by SQLite's write lock: the second one sees the first row and
    replays it instead of creating a second audit. A different body for the same
    key raises IdempotencyConflict.
    """
    from benchproof.storage import insert_audit

    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT body_hash, response_json FROM idempotency_keys WHERE owner_ref=? AND endpoint=? AND idem_key=?",
            (owner_ref, endpoint, key),
        ).fetchone()
        if row is not None:
            conn.execute("ROLLBACK")
            if row["body_hash"] != bhash:
                raise IdempotencyConflict("Idempotency-Key reused with a different body")
            return json.loads(row["response_json"]), True
        insert_audit(conn, audit)
        conn.execute(
            """INSERT INTO idempotency_keys
               (owner_ref, endpoint, idem_key, body_hash, audit_id, response_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (owner_ref, endpoint, key, bhash, audit.audit_id, json.dumps(response, sort_keys=True), _now().isoformat()),
        )
        _append_event_conn(
            conn,
            audit.audit_id,
            "audit_created",
            {"fixture_id": audit.fixture_id, "source_hash": audit.source_hash,
             "contract_hash": audit.contract_hash, "mode": audit.mode},
        )
        conn.execute("COMMIT")
        return response, False
    finally:
        conn.close()
