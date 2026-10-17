"""Durable SQLite database backup and verification utility (C-08).

Performs transactionally consistent online backups of the BenchProof database
using SQLite's native backup API (WAL-safe), with SHA-256 integrity verification,
manifest generation, table row count telemetry, and safe restoration.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class BackupError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _get_table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [row[0] for row in cursor.fetchall()]
    counts: dict[str, int] = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM \"{table}\";")
            counts[table] = int(cursor.fetchone()[0])
        except sqlite3.OperationalError:
            counts[table] = 0
    return counts


def create_backup(
    source_db: Path,
    backup_dest: Path,
    *,
    include_manifest: bool = True,
) -> dict[str, Any]:
    """Create an atomic, WAL-consistent SQLite backup with checksum manifest."""
    source_db = Path(source_db).resolve()
    backup_dest = Path(backup_dest).resolve()

    if not source_db.exists() or not source_db.is_file():
        raise BackupError("SOURCE_NOT_FOUND", f"Source database not found: {source_db}")

    backup_dest.parent.mkdir(parents=True, exist_ok=True)

    # 1. Check source integrity first
    with sqlite3.connect(f"file:{source_db}?mode=ro", uri=True) as src_conn:
        cursor = src_conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            raise BackupError("SOURCE_INTEGRITY_FAILED", f"Source database integrity failed: {integrity}")

        # 2. Perform non-blocking online backup
        with sqlite3.connect(str(backup_dest)) as dst_conn:
            src_conn.backup(dst_conn, pages=100)

    # 3. Verify target database integrity and row counts
    with sqlite3.connect(f"file:{backup_dest}?mode=ro", uri=True) as dst_conn:
        cursor = dst_conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        dst_integrity = cursor.fetchone()[0]
        if dst_integrity != "ok":
            raise BackupError("BACKUP_INTEGRITY_FAILED", f"Backup file integrity check failed: {dst_integrity}")
        counts = _get_table_counts(dst_conn)

    checksum = _sha256(backup_dest)
    manifest: dict[str, Any] = {
        "source_db": str(source_db),
        "backup_path": str(backup_dest),
        "sha256": checksum,
        "byte_size": backup_dest.stat().st_size,
        "created_at": datetime.now(UTC).isoformat(),
        "integrity": dst_integrity,
        "table_counts": counts,
    }

    if include_manifest:
        manifest_path = backup_dest.with_suffix(backup_dest.suffix + ".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return manifest


def restore_backup(
    backup_file: Path,
    target_db: Path,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Safely restore a database from an authenticated backup."""
    backup_file = Path(backup_file).resolve()
    target_db = Path(target_db).resolve()

    if not backup_file.exists() or not backup_file.is_file():
        raise BackupError("BACKUP_NOT_FOUND", f"Backup file not found: {backup_file}")

    actual_sha256 = _sha256(backup_file)
    if expected_sha256 and actual_sha256 != expected_sha256:
        raise BackupError(
            "CHECKSUM_MISMATCH",
            f"Backup checksum mismatch: expected {expected_sha256}, got {actual_sha256}",
        )

    # Check backup file validity before restoring
    with sqlite3.connect(f"file:{backup_file}?mode=ro", uri=True) as chk_conn:
        cursor = chk_conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        chk_integrity = cursor.fetchone()[0]
        if chk_integrity != "ok":
            raise BackupError("CORRUPT_BACKUP", f"Backup integrity check failed: {chk_integrity}")

    target_db.parent.mkdir(parents=True, exist_ok=True)

    # Online atomic restore into target
    with sqlite3.connect(str(backup_file)) as src_conn:
        with sqlite3.connect(str(target_db)) as dst_conn:
            dst_conn.execute("PRAGMA journal_mode=WAL")
            src_conn.backup(dst_conn, pages=100)

    # Verify restored target
    with sqlite3.connect(f"file:{target_db}?mode=ro", uri=True) as dst_conn:
        cursor = dst_conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        dst_integrity = cursor.fetchone()[0]
        if dst_integrity != "ok":
            raise BackupError("RESTORE_FAILED", f"Restored database integrity failed: {dst_integrity}")
        cursor.execute("PRAGMA foreign_key_check;")
        fk_errors = cursor.fetchall()
        if fk_errors:
            raise BackupError("FOREIGN_KEY_VIOLATION", f"Restored database has foreign key violations: {fk_errors}")
        counts = _get_table_counts(dst_conn)

    return {
        "target_db": str(target_db),
        "source_backup": str(backup_file),
        "sha256": actual_sha256,
        "restored_at": datetime.now(UTC).isoformat(),
        "integrity": dst_integrity,
        "table_counts": counts,
    }
