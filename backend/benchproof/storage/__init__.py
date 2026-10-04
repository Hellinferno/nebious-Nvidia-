"""SQLite storage — migrations, audit records, and artifact references."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from benchproof.domain import AuditRecord, GateVerdict, RunState

_DB_PATH = Path("benchproof.db")


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    p = db_path or _DB_PATH
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def migrate(db_path: Path | None = None) -> None:
    """Create tables if they do not exist."""
    conn = _connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS audits (
            audit_id      TEXT PRIMARY KEY,
            owner_ref     TEXT NOT NULL,
            fixture_id    TEXT NOT NULL,
            task_id       TEXT NOT NULL DEFAULT '',
            source_hash   TEXT NOT NULL,
            contract_hash TEXT NOT NULL,
            run_state     TEXT NOT NULL DEFAULT 'QUEUED',
            gate_verdict  TEXT NOT NULL DEFAULT 'PENDING',
            mode          TEXT NOT NULL DEFAULT 'live',
            created_at    TEXT NOT NULL,
            attempt       INTEGER NOT NULL DEFAULT 1,
            limits_json   TEXT NOT NULL DEFAULT '{}',
            reservations  TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id   TEXT NOT NULL REFERENCES audits(audit_id),
            attempt    INTEGER NOT NULL DEFAULT 1,
            sequence   INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload    TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(audit_id, attempt, sequence)
        );

        CREATE TABLE IF NOT EXISTS check_results (
            check_id       TEXT NOT NULL,
            audit_id       TEXT NOT NULL REFERENCES audits(audit_id),
            attempt        INTEGER NOT NULL DEFAULT 1,
            check_version  INTEGER NOT NULL DEFAULT 1,
            outcome        TEXT NOT NULL,
            oracle_kind    TEXT NOT NULL DEFAULT '',
            reason         TEXT NOT NULL DEFAULT '',
            duration_ms    INTEGER NOT NULL DEFAULT 0,
            source_hash    TEXT NOT NULL DEFAULT '',
            contract_hash  TEXT NOT NULL DEFAULT '',
            evaluator_hash TEXT NOT NULL DEFAULT '',
            created_at     TEXT NOT NULL,
            PRIMARY KEY (check_id, audit_id, attempt)
        );

        CREATE TABLE IF NOT EXISTS patches (
            patch_id       TEXT PRIMARY KEY,
            audit_id       TEXT NOT NULL REFERENCES audits(audit_id),
            base_hash      TEXT NOT NULL,
            diff_hash      TEXT NOT NULL DEFAULT '',
            diff_text      TEXT NOT NULL DEFAULT '',
            approved_paths TEXT NOT NULL DEFAULT '[]',
            changed_lines  INTEGER NOT NULL DEFAULT 0,
            policy_result  TEXT NOT NULL DEFAULT 'PENDING',
            author         TEXT NOT NULL DEFAULT '',
            provider_meta  TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id   TEXT PRIMARY KEY,
            owner         TEXT NOT NULL,
            audit_id      TEXT NOT NULL REFERENCES audits(audit_id),
            attempt       INTEGER NOT NULL DEFAULT 1,
            relative_name TEXT NOT NULL,
            mime_type     TEXT NOT NULL DEFAULT 'application/octet-stream',
            byte_size     INTEGER NOT NULL DEFAULT 0,
            sha256        TEXT NOT NULL DEFAULT '',
            visibility    TEXT NOT NULL DEFAULT 'private'
        );

        CREATE TABLE IF NOT EXISTS worker_heartbeats (
            worker_id TEXT PRIMARY KEY,
            runner    TEXT NOT NULL DEFAULT 'mock',
            last_seen TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def save_audit(audit: AuditRecord, db_path: Path | None = None) -> None:
    conn = _connect(db_path)
    conn.execute(
        """INSERT INTO audits
           (audit_id, owner_ref, fixture_id, task_id, source_hash,
            contract_hash, run_state, gate_verdict, mode, created_at,
            attempt, limits_json, reservations)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            audit.audit_id,
            audit.owner_ref,
            audit.fixture_id,
            audit.task_id,
            audit.source_hash,
            audit.contract_hash,
            audit.run_state.value,
            audit.gate_verdict.value,
            audit.mode,
            audit.created_at.isoformat(),
            audit.attempt,
            json.dumps(audit.limits),
            json.dumps(audit.reservations),
        ),
    )
    conn.commit()
    conn.close()


def update_audit_state(
    audit_id: str,
    new_state: RunState,
    verdict: GateVerdict | None = None,
    db_path: Path | None = None,
) -> None:
    conn = _connect(db_path)
    if verdict:
        conn.execute(
            "UPDATE audits SET run_state=?, gate_verdict=? WHERE audit_id=?",
            (new_state.value, verdict.value, audit_id),
        )
    else:
        conn.execute(
            "UPDATE audits SET run_state=? WHERE audit_id=?",
            (new_state.value, audit_id),
        )
    conn.commit()
    conn.close()


def get_audit(audit_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    conn = _connect(db_path)
    row = conn.execute("SELECT * FROM audits WHERE audit_id=?", (audit_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def list_audits(owner: str | None = None, db_path: Path | None = None) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    if owner:
        rows = conn.execute("SELECT * FROM audits WHERE owner_ref=? ORDER BY created_at DESC", (owner,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM audits ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
