"""Durable, owner-scoped project repository stored in SQLite (C-04)."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any

from benchproof.projects.intake import validate_project_intake
from benchproof.projects.models import ProjectManifest, ProjectRecord

MAX_PROJECTS_PER_OWNER = 10


class ProjectStoreError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ProjectStore:
    def __init__(
        self,
        db_path: Path | str,
        *,
        clock: Callable[[], float] = time.time,
        max_projects_per_owner: int = MAX_PROJECTS_PER_OWNER,
    ) -> None:
        self.db_path = Path(db_path)
        self.clock = clock
        self.max_projects_per_owner = max_projects_per_owner

        with closing(self._connect()) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS coding_projects (
                    project_id TEXT PRIMARY KEY,
                    owner_ref TEXT NOT NULL,
                    name TEXT NOT NULL,
                    runner_profile TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    files_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_projects_owner ON coding_projects(owner_ref, created_at);
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_project(
        self,
        owner_ref: str,
        name: str,
        files: dict[str, Any],
        runner_profile: str = "unittest",
    ) -> ProjectRecord:
        """Validate files and persist a new project snapshot for the owner."""
        if not isinstance(owner_ref, str) or not owner_ref.strip():
            raise ProjectStoreError("OWNER_REQUIRED", "owner_ref is required")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ProjectStoreError("INVALID_NAME", "Project name must be 1 to 100 characters")

        clean_name = name.strip()
        manifest, validated_files = validate_project_intake(files, runner_profile=runner_profile)

        now = self.clock()
        project_id = f"proj-{uuid.uuid4().hex[:12]}"

        with self._transaction() as connection:
            # Check owner quota
            count_cursor = connection.execute(
                "SELECT COUNT(*) FROM coding_projects WHERE owner_ref = ?",
                (owner_ref,),
            )
            count = count_cursor.fetchone()[0]
            if count >= self.max_projects_per_owner:
                raise ProjectStoreError(
                    "STORAGE_LIMIT",
                    f"Owner project limit reached ({self.max_projects_per_owner} projects max)",
                )

            manifest_json = json.dumps(manifest.to_dict(), separators=(",", ":"))
            files_json = json.dumps(validated_files, separators=(",", ":"))

            connection.execute(
                """
                INSERT INTO coding_projects (
                    project_id, owner_ref, name, runner_profile, source_hash,
                    manifest_json, files_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    owner_ref,
                    clean_name,
                    runner_profile,
                    manifest.source_hash,
                    manifest_json,
                    files_json,
                    now,
                    now,
                ),
            )

        return ProjectRecord(
            project_id=project_id,
            owner_ref=owner_ref,
            name=clean_name,
            runner_profile=runner_profile,
            source_hash=manifest.source_hash,
            manifest=manifest,
            files=validated_files,
            created_at=now,
            updated_at=now,
        )

    def get_project(self, project_id: str, owner_ref: str | None = None) -> ProjectRecord | None:
        """Retrieve a project by ID, optionally verifying owner."""
        with closing(self._connect()) as connection:
            query = "SELECT * FROM coding_projects WHERE project_id = ?"
            params: tuple[Any, ...] = (project_id,)
            if owner_ref is not None:
                query += " AND owner_ref = ?"
                params = (project_id, owner_ref)

            row = connection.execute(query, params).fetchone()
            if row is None:
                return None

            manifest = ProjectManifest.from_dict(json.loads(row["manifest_json"]))
            files = json.loads(row["files_json"])

            return ProjectRecord(
                project_id=row["project_id"],
                owner_ref=row["owner_ref"],
                name=row["name"],
                runner_profile=row["runner_profile"],
                source_hash=row["source_hash"],
                manifest=manifest,
                files=files,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_projects(self, owner_ref: str) -> list[dict[str, Any]]:
        """List summary records for all projects owned by owner_ref."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT project_id, owner_ref, name, runner_profile, source_hash,
                       manifest_json, created_at, updated_at
                FROM coding_projects
                WHERE owner_ref = ?
                ORDER BY created_at DESC
                """,
                (owner_ref,),
            ).fetchall()

            summaries = []
            for row in rows:
                manifest_dict = json.loads(row["manifest_json"])
                summaries.append({
                    "project_id": row["project_id"],
                    "owner_ref": row["owner_ref"],
                    "name": row["name"],
                    "runner_profile": row["runner_profile"],
                    "source_hash": row["source_hash"],
                    "total_files": manifest_dict["total_files"],
                    "total_bytes": manifest_dict["total_bytes"],
                    "app_files": manifest_dict["app_files"],
                    "test_files": manifest_dict["test_files"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })
            return summaries

    def delete_project(self, project_id: str, owner_ref: str) -> bool:
        """Delete an owned project record."""
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM coding_projects WHERE project_id = ? AND owner_ref = ?",
                (project_id, owner_ref),
            )
            return cursor.rowcount > 0
