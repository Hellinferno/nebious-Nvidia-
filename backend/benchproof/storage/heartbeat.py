"""Worker heartbeat records — lets /ready report whether a worker is alive."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchproof.storage import _connect


def migrate_heartbeat(db_path: Path | None = None) -> None:
    conn = _connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS worker_heartbeats (
               worker_id TEXT PRIMARY KEY,
               runner    TEXT NOT NULL DEFAULT 'mock',
               last_seen TEXT NOT NULL
           )"""
    )
    conn.commit()
    conn.close()


def record_heartbeat(worker_id: str, runner: str, db_path: Path | None = None) -> None:
    conn = _connect(db_path)
    conn.execute(
        """INSERT INTO worker_heartbeats (worker_id, runner, last_seen) VALUES (?, ?, ?)
           ON CONFLICT(worker_id) DO UPDATE SET runner=excluded.runner, last_seen=excluded.last_seen""",
        (worker_id, runner, datetime.now(UTC).isoformat()),
    )
    conn.commit()
    conn.close()


def latest_heartbeat(db_path: Path | None = None) -> dict[str, Any] | None:
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT worker_id, runner, last_seen FROM worker_heartbeats ORDER BY last_seen DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return None
    seen = datetime.fromisoformat(row["last_seen"])
    age = (datetime.now(UTC) - seen).total_seconds()
    return {"worker_id": row["worker_id"], "runner": row["runner"], "last_seen": row["last_seen"], "age_s": round(age, 1)}
