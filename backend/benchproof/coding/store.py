"""Owner-scoped prepared-project tasks with durable, fenced action reservations."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
import time
import uuid
import zipfile
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchproof.coding.contracts import (
    CodingBrief,
    CodingPlan,
    CodingStoreError,
    Lease,
    OperatorLimits,
    TaskLimits,
)
from benchproof.fixtures import candidate_files, fixture_dir
from benchproof.storage.admission import StorageAdmissionError, check_storage_admission

_HASH = re.compile(r"^[a-f0-9]{64}$")
_PATH = re.compile(r"^(?:app|tests)/(?:[A-Za-z_][A-Za-z0-9_]*/)*[A-Za-z_][A-Za-z0-9_]*\.py$")
_TERMINAL = {"CANCELLED", "BLOCKED", "FAILED", "STALLED", "BUDGET_EXHAUSTED", "REVIEW_READY"}
_STAGES = {"PLAN", "BASELINE", "EDIT", "CANDIDATE", "FINAL", "DONE"}


def _json(value: Any, maximum: int = 262_144) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                             allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise CodingStoreError("INVALID_INPUT", "A bounded JSON value is required") from exc
    if len(encoded.encode("utf-8")) > maximum:
        raise CodingStoreError("STORAGE_LIMIT", "The coding record exceeds its byte allowance")
    return encoded


def _identity(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _token(value: str, label: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or not value.strip():
        raise CodingStoreError("INVALID_INPUT", f"A bounded {label} is required")
    return value


def _hash(value: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise CodingStoreError("INVALID_INPUT", "A SHA-256 source or contract identity is required")
    return value


def _snapshot(files: dict[str, str], brief: CodingBrief) -> str:
    if not isinstance(files, dict) or not 1 <= len(files) <= 20:
        raise CodingStoreError("INVALID_INPUT", "A prepared source snapshot is required")
    if not all(isinstance(path, str) for path in files):
        raise CodingStoreError("INVALID_INPUT", "Source paths must be text")
    if len({path.casefold() for path in files}) != len(files):
        raise CodingStoreError("INVALID_INPUT", "Source paths collide")
    total = 0
    manifest = {}
    for path, content in files.items():
        if not isinstance(path, str) or not _PATH.fullmatch(path) or not isinstance(content, str):
            raise CodingStoreError("INVALID_INPUT", "Only prepared app/ Python text is supported")
        try:
            raw = content.encode("utf-8")
        except UnicodeError as exc:
            raise CodingStoreError("INVALID_INPUT", "Source must be valid UTF-8") from exc
        if b"\x00" in raw or len(raw) > 24_576:
            raise CodingStoreError("STORAGE_LIMIT", "Source file exceeds the supported text profile")
        total += len(raw)
        manifest[path] = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if total > 131_072 or not set(brief.editable_paths) <= set(files):
        raise CodingStoreError("STORAGE_LIMIT", "Source snapshot or editable paths exceed the profile")
    if _identity(manifest) != brief.source_hash:
        raise CodingStoreError("STALE_SOURCE", "Snapshot does not match the reviewed source identity")
    return _json(files)


class CodingStore:
    def __init__(
        self, db_path: Path | str, operator_limits: OperatorLimits | None = None,
        *, clock: Callable[[], float] = time.time,
    ) -> None:
        self.db_path = Path(db_path)
        self.operator_limits = operator_limits or OperatorLimits()
        self.clock = clock
        with closing(self._connect()) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS coding_tasks (
                    task_id TEXT PRIMARY KEY, owner_ref TEXT NOT NULL, fixture_id TEXT NOT NULL,
                    brief_json TEXT NOT NULL, source_json TEXT NOT NULL, contract_hash TEXT NOT NULL,
                    plan_json TEXT, approved_plan_hash TEXT, state TEXT NOT NULL,
                    runtime_config_json TEXT NOT NULL DEFAULT '{}',
                    next_stage TEXT NOT NULL, checkpoint_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}', model_calls INTEGER NOT NULL DEFAULT 0,
                    patch_attempts INTEGER NOT NULL DEFAULT 0, executions INTEGER NOT NULL DEFAULT 0,
                    active_seconds REAL NOT NULL DEFAULT 0, active_since REAL,
                    lease_worker TEXT, lease_deadline REAL, fence INTEGER NOT NULL DEFAULT 0,
                    pause_requested INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS coding_actions (
                    action_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES coding_tasks(task_id),
                    kind TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL,
                    worker_id TEXT NOT NULL, fence INTEGER NOT NULL, source_hash TEXT NOT NULL,
                    plan_hash TEXT, details_json TEXT NOT NULL, result_json TEXT NOT NULL DEFAULT '{}',
                    usage_json TEXT NOT NULL DEFAULT '{"status":"UNKNOWN"}',
                    created_at REAL NOT NULL, finished_at REAL
                );
                CREATE TABLE IF NOT EXISTS coding_events (
                    task_id TEXT NOT NULL REFERENCES coding_tasks(task_id), sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at REAL NOT NULL,
                    PRIMARY KEY (task_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS coding_requests (
                    owner_ref TEXT NOT NULL, operation TEXT NOT NULL, request_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL, task_id TEXT NOT NULL REFERENCES coding_tasks(task_id),
                    PRIMARY KEY (owner_ref, operation, request_key)
                );
                CREATE TABLE IF NOT EXISTS coding_daily_usage (
                    day TEXT PRIMARY KEY, model_calls INTEGER NOT NULL DEFAULT 0,
                    executions INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS coding_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES coding_tasks(task_id),
                    sequence INTEGER NOT NULL, stage TEXT NOT NULL, state TEXT NOT NULL,
                    checkpoint_json TEXT NOT NULL, created_at REAL NOT NULL,
                    UNIQUE (task_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS coding_owner ON coding_tasks(owner_ref, created_at);
                CREATE INDEX IF NOT EXISTS coding_queue ON coding_tasks(state, created_at);
                CREATE INDEX IF NOT EXISTS coding_chk_idx ON coding_checkpoints(task_id, sequence);
            """)
            columns = {column[1] for column in connection.execute("PRAGMA table_info(coding_tasks)")}
            if "runtime_config_json" not in columns:
                connection.execute("ALTER TABLE coding_tasks ADD COLUMN runtime_config_json TEXT NOT NULL DEFAULT '{}'")

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

    def _row(self, connection: sqlite3.Connection, task_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM coding_tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise CodingStoreError("NOT_FOUND", "Coding task not found")
        return row

    def _owned(self, connection: sqlite3.Connection, owner_ref: str, task_id: str) -> sqlite3.Row:
        row = self._row(connection, task_id)
        if row["owner_ref"] != owner_ref:
            raise CodingStoreError("NOT_FOUND", "Coding task not found")
        return row

    def _limits(self, task: sqlite3.Row) -> TaskLimits:
        return TaskLimits.for_brief(CodingBrief.model_validate_json(task["brief_json"]))

    def _require_implementation(self, task: sqlite3.Row) -> None:
        brief = CodingBrief.model_validate_json(task["brief_json"])
        if brief.preferences is not None and brief.preferences.mode == "plan_only":
            raise CodingStoreError(
                "PLAN_ONLY", "This task allows planning only; edits and test execution are disabled",
            )

    def _event(self, connection: sqlite3.Connection, task_id: str, kind: str, payload: Any) -> None:
        connection.execute("""
            INSERT INTO coding_events(task_id,sequence,event_type,payload_json,created_at)
            SELECT ?,COALESCE(MAX(sequence),0)+1,?,?,? FROM coding_events WHERE task_id=?
        """, (task_id, kind, _json(payload, 32_768), self.clock(), task_id))

    def _save_checkpoint(
        self, connection: sqlite3.Connection, task_id: str, stage: str, state: str,
        checkpoint: dict[str, Any],
    ) -> str:
        chk_id = f"chk-{uuid.uuid4().hex[:12]}"
        connection.execute("""
            INSERT INTO coding_checkpoints(checkpoint_id,task_id,sequence,stage,state,checkpoint_json,created_at)
            SELECT ?,?,COALESCE(MAX(sequence),0)+1,?,?,?,?
            FROM coding_checkpoints WHERE task_id=?
        """, (chk_id, task_id, stage, state, _json(checkpoint), self.clock(), task_id))
        self._event(connection, task_id, "CHECKPOINT_SAVED", {
            "checkpoint_id": chk_id, "stage": stage, "state": state,
            "candidate_hash": checkpoint.get("candidate_hash"),
        })
        return chk_id

    def _task(self, connection: sqlite3.Connection, task_id: str) -> dict[str, Any]:
        row = dict(self._row(connection, task_id))
        row["schema_version"] = "coding-task-v1"
        row["source_profile"] = "prepared-fixture-v1"
        for field in ("brief", "source", "plan", "checkpoint", "result", "runtime_config"):
            encoded = row.pop(f"{field}_json")
            row[field if field != "source" else "source_files"] = json.loads(encoded) if encoded else None
        row["counters"] = {name: row.pop(name) for name in (
            "model_calls", "patch_attempts", "executions", "active_seconds",
        )}
        row["limits"] = vars(TaskLimits.for_brief(CodingBrief.model_validate(row["brief"]))).copy()
        row["pause_requested"] = bool(row["pause_requested"])
        row["actions"] = []
        for action in connection.execute(
            "SELECT * FROM coding_actions WHERE task_id=? ORDER BY created_at, rowid", (task_id,),
        ):
            item = dict(action)
            item["schema_version"] = "coding-action-v1"
            for field in ("details", "result", "usage"):
                item[field] = json.loads(item.pop(f"{field}_json"))
            row["actions"].append(item)
        return row

    def _replay(
        self, connection: sqlite3.Connection, owner_ref: str, operation: str, key: str, fingerprint: str,
    ) -> dict[str, Any] | None:
        _token(key, "idempotency key")
        request = connection.execute(
            "SELECT * FROM coding_requests WHERE owner_ref=? AND operation=? AND request_key=?",
            (owner_ref, operation, key),
        ).fetchone()
        if request is None:
            return None
        if request["request_hash"] != fingerprint:
            raise CodingStoreError("IDEMPOTENCY_CONFLICT", "Request key was used for different input")
        return self._task(connection, request["task_id"])

    def _request(
        self, connection: sqlite3.Connection, owner_ref: str, operation: str, key: str,
        fingerprint: str, task_id: str,
    ) -> None:
        connection.execute("INSERT INTO coding_requests VALUES(?,?,?,?,?)",
                           (owner_ref, operation, key, fingerprint, task_id))

    def create_task(
        self, owner_ref: str, fixture_id: str, brief: CodingBrief, source_files: dict[str, str],
        contract_hash: str, idempotency_key: str, *, runtime_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _token(owner_ref, "owner reference")
        _hash(contract_hash)
        brief = CodingBrief.model_validate(brief)
        brief_payload = brief.canonical_payload()
        source_json = _snapshot(source_files, brief)
        runtime_json = _json(runtime_config or {}, 4_096)
        fingerprint = _identity({"fixture_id": fixture_id, "brief": brief_payload,
                                 "source": source_files, "contract_hash": contract_hash,
                                 "runtime_config": runtime_config or {}})
        with self._transaction() as connection:
            replay = self._replay(connection, owner_ref, "create", idempotency_key, fingerprint)
            if replay:
                return replay
            if fixture_id.startswith("proj-"):
                proj = connection.execute(
                    "SELECT * FROM coding_projects WHERE project_id=? AND owner_ref=?",
                    (fixture_id, owner_ref),
                ).fetchone()
                if proj is None:
                    raise CodingStoreError("NOT_FOUND", f"Project '{fixture_id}' not found")
                manifest = json.loads(proj["manifest_json"])
                if proj["runner_profile"] != "unittest" or manifest.get("runner_profile") != "unittest":
                    raise CodingStoreError("UNSUPPORTED_RUNNER", "Only the unittest project profile is supported")
                proj_files = json.loads(proj["files_json"])
                if proj_files != source_files:
                    raise CodingStoreError("STALE_SOURCE", "Task source does not match stored project snapshot")
            else:
                try:
                    app_dir = fixture_dir(fixture_id) / "app"
                    if app_dir.is_symlink() or not app_dir.is_dir():
                        raise ValueError("Missing prepared fixture")
                    expected = {}
                    for path in candidate_files(app_dir):
                        if (any(parent.is_symlink() for parent in [path, *path.parents]
                                if parent != app_dir.parent)
                                or not path.resolve().is_relative_to(app_dir.resolve())):
                            raise ValueError("Linked fixture")
                        expected[path.relative_to(app_dir.parent).as_posix()] = path.read_bytes().decode("utf-8")
                    if expected != source_files:
                        raise ValueError("Changed prepared fixture")
                except (OSError, UnicodeError, ValueError) as exc:
                    raise CodingStoreError("STALE_SOURCE", "Only an exact prepared fixture snapshot is supported") from exc
            count = connection.execute("SELECT COUNT(*) FROM coding_tasks").fetchone()[0]
            if count >= self.operator_limits.max_tasks:
                raise CodingStoreError("STORAGE_LIMIT", "Prepared coding task storage is full")
            try:
                check_storage_admission(
                    self.db_path,
                    len((source_json + runtime_json + _json(brief_payload)).encode("utf-8")) + 16_384,
                )
            except StorageAdmissionError as exc:
                raise CodingStoreError("STORAGE_LIMIT", str(exc)) from exc
            task_id = f"coding-{uuid.uuid4().hex[:16]}"
            now = self.clock()
            connection.execute("""
                INSERT INTO coding_tasks(task_id,owner_ref,fixture_id,brief_json,source_json,
                                         contract_hash,runtime_config_json,state,next_stage,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,'DRAFT','PLAN',?,?)
            """, (task_id, owner_ref, fixture_id, _json(brief_payload), source_json,
                  contract_hash, runtime_json, now, now))
            self._request(connection, owner_ref, "create", idempotency_key, fingerprint, task_id)
            self._event(connection, task_id, "TASK_CREATED", {"source_hash": brief.source_hash})
            return self._task(connection, task_id)

    def get_task(self, owner_ref: str, task_id: str) -> dict[str, Any]:
        self.reconcile()
        with self._transaction() as connection:
            self._owned(connection, owner_ref, task_id)
            return self._task(connection, task_id)

    def list_tasks(self, owner_ref: str) -> list[dict[str, Any]]:
        with self._transaction() as connection:
            return [self._task(connection, row[0]) for row in connection.execute(
                "SELECT task_id FROM coding_tasks WHERE owner_ref=? ORDER BY created_at DESC",
                (owner_ref,),
            ).fetchall()]

    def list_events(
        self, owner_ref: str, task_id: str, after_sequence: int = 0,
    ) -> list[dict[str, Any]]:
        if type(after_sequence) is not int or after_sequence < 0:
            raise CodingStoreError("INVALID_INPUT", "Event cursor must be a nonnegative integer")
        with self._transaction() as connection:
            self._owned(connection, owner_ref, task_id)
            return [{"sequence": row["sequence"], "event_type": row["event_type"],
                     "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]}
                    for row in connection.execute(
                        "SELECT * FROM coding_events WHERE task_id=? AND sequence>? ORDER BY sequence",
                        (task_id, after_sequence),
                    )]

    def _require_project_runner(self, connection: sqlite3.Connection, task: sqlite3.Row) -> None:
        if not task["fixture_id"].startswith("proj-"):
            return
        project = connection.execute(
            "SELECT runner_profile,manifest_json FROM coding_projects WHERE project_id=? AND owner_ref=?",
            (task["fixture_id"], task["owner_ref"]),
        ).fetchone()
        if project is not None and (
            project["runner_profile"] != "unittest"
            or json.loads(project["manifest_json"]).get("runner_profile") != "unittest"
        ):
            raise CodingStoreError("UNSUPPORTED_RUNNER", "Only the unittest project profile is supported")

    def enqueue(
        self, owner_ref: str, task_id: str, idempotency_key: str, *, phase: str = "plan",
    ) -> dict[str, Any]:
        if phase not in {"plan", "run"}:
            raise CodingStoreError("INVALID_INPUT", "Unknown coding enqueue phase")
        fingerprint = _identity({"task_id": task_id, "phase": phase})
        with self._transaction() as connection:
            task = self._owned(connection, owner_ref, task_id)
            if phase == "run":
                self._require_implementation(task)
            replay = self._replay(connection, owner_ref, f"enqueue:{phase}", idempotency_key, fingerprint)
            if replay:
                return replay
            self._require_project_runner(connection, task)
            expected = "DRAFT" if phase == "plan" else "APPROVED"
            if task["state"] != expected:
                raise CodingStoreError("INVALID_STATE", f"Task must be {expected} before this enqueue")
            self._busy(connection, task_id)
            if phase == "run":
                plan = CodingPlan.model_validate_json(task["plan_json"])
                if plan.identity() != task["approved_plan_hash"]:
                    raise CodingStoreError("PLAN_UNAPPROVED", "Approve the exact current plan first")
            connection.execute("UPDATE coding_tasks SET state='QUEUED',updated_at=? WHERE task_id=?",
                               (self.clock(), task_id))
            self._request(connection, owner_ref, f"enqueue:{phase}", idempotency_key, fingerprint, task_id)
            self._event(connection, task_id, "TASK_QUEUED", {"phase": phase})
            return self._task(connection, task_id)

    def _plan(self, task: sqlite3.Row, plan: CodingPlan | dict[str, Any]) -> CodingPlan:
        plan = CodingPlan.model_validate(plan)
        brief = CodingBrief.model_validate_json(task["brief_json"])
        if (plan.source_hash != brief.source_hash or plan.brief_hash != brief.identity()
                or not set(plan.target_files) <= set(brief.editable_paths)):
            raise CodingStoreError("PLAN_UNAPPROVED", "Plan does not match the task's exact source and scope")
        return plan

    def update_plan(
        self, owner_ref: str, task_id: str, plan: CodingPlan | dict[str, Any],
    ) -> dict[str, Any]:
        with self._transaction() as connection:
            task = self._owned(connection, owner_ref, task_id)
            if task["state"] not in {"AWAITING_APPROVAL", "APPROVED"}:
                raise CodingStoreError("INVALID_STATE", "Plans can only change before running")
            plan = self._plan(task, plan)
            connection.execute("""
                UPDATE coding_tasks SET plan_json=?,approved_plan_hash=NULL,state='AWAITING_APPROVAL',
                                        updated_at=? WHERE task_id=?
            """, (_json(plan.model_dump()), self.clock(), task_id))
            self._event(connection, task_id, "PLAN_UPDATED", {"plan_hash": plan.identity()})
            return self._task(connection, task_id)

    def approve_plan(self, owner_ref: str, task_id: str, plan_hash: str) -> dict[str, Any]:
        with self._transaction() as connection:
            task = self._owned(connection, owner_ref, task_id)
            if task["state"] not in {"AWAITING_APPROVAL", "APPROVED"}:
                raise CodingStoreError("INVALID_STATE", "Task is not awaiting plan approval")
            plan = self._plan(task, CodingPlan.model_validate_json(task["plan_json"]))
            if plan_hash != plan.identity():
                raise CodingStoreError("STALE_PLAN", "The reviewed plan revision changed")
            if task["state"] != "APPROVED":
                connection.execute("""
                    UPDATE coding_tasks SET state='APPROVED',approved_plan_hash=?,next_stage='BASELINE',
                                            updated_at=? WHERE task_id=?
                """, (plan_hash, self.clock(), task_id))
                self._event(connection, task_id, "PLAN_APPROVED", {"plan_hash": plan_hash})
                self._save_checkpoint(connection, task_id, "BASELINE", "APPROVED", {})
            return self._task(connection, task_id)

    def _accrue(self, connection: sqlite3.Connection, task: sqlite3.Row, until: float) -> None:
        elapsed = max(0.0, until - task["active_since"]) if task["active_since"] is not None else 0.0
        connection.execute("""
            UPDATE coding_tasks SET active_seconds=active_seconds+?,active_since=?,updated_at=?
            WHERE task_id=?
        """, (elapsed, until, self.clock(), task["task_id"]))

    def _release(self, connection: sqlite3.Connection, task_id: str, state: str) -> None:
        connection.execute("""
            UPDATE coding_tasks SET state=?,lease_worker=NULL,lease_deadline=NULL,active_since=NULL,
                                    pause_requested=0,updated_at=? WHERE task_id=?
        """, (state, self.clock(), task_id))

    def _interrupt(self, connection: sqlite3.Connection, task: sqlite3.Row, state: str) -> None:
        until = min(self.clock(), task["lease_deadline"] or self.clock())
        self._accrue(connection, task, until)
        connection.execute("""
            UPDATE coding_actions SET status=CASE WHEN kind='EXECUTION' THEN 'INTERRUPTED' ELSE 'UNKNOWN' END,
                                      finished_at=? WHERE task_id=? AND status='RUNNING'
        """, (self.clock(), task["task_id"]))
        self._release(connection, task["task_id"], state)
        connection.execute("UPDATE coding_tasks SET fence=fence+1 WHERE task_id=?", (task["task_id"],))
        self._event(connection, task["task_id"], f"TASK_{state}", {"reason": "lease or control boundary"})

    def _reconcile(self, connection: sqlite3.Connection) -> None:
        for task in connection.execute(
            "SELECT * FROM coding_tasks WHERE state='RUNNING' AND lease_deadline<=?", (self.clock(),),
        ).fetchall():
            self._interrupt(connection, task, "INTERRUPTED")

    def _busy(self, connection: sqlite3.Connection, task_id: str) -> None:
        if connection.execute("""
            SELECT 1 FROM coding_tasks WHERE task_id!=? AND state IN ('QUEUED','RUNNING','CANCEL_PENDING')
            UNION ALL
            SELECT 1 FROM coding_actions WHERE kind='EXECUTION' AND status='INTERRUPTED'
        """, (task_id,)).fetchone():
            raise CodingStoreError("BUSY", "Another coding task occupies the single active slot")

    def reconcile(self) -> None:
        with self._transaction() as connection:
            self._reconcile(connection)

    def claim_next(self, worker_id: str, lease_seconds: float = 60) -> Lease | None:
        _token(worker_id, "worker identity")
        if not 1 <= lease_seconds <= 300:
            raise CodingStoreError("INVALID_INPUT", "Lease must be between 1 and 300 seconds")
        with self._transaction() as connection:
            self._reconcile(connection)
            if connection.execute("""
                SELECT 1 FROM coding_tasks WHERE state IN ('RUNNING','CANCEL_PENDING')
                UNION ALL
                SELECT 1 FROM coding_actions WHERE kind='EXECUTION' AND status='INTERRUPTED'
            """).fetchone():
                return None
            task = connection.execute(
                "SELECT * FROM coding_tasks WHERE state='QUEUED' ORDER BY created_at,rowid LIMIT 1",
            ).fetchone()
            if task is None:
                return None
            now = self.clock()
            fence = task["fence"] + 1
            connection.execute("""
                UPDATE coding_tasks SET state='RUNNING',lease_worker=?,lease_deadline=?,fence=?,
                                        active_since=?,updated_at=? WHERE task_id=?
            """, (worker_id, now + lease_seconds, fence, now, now, task["task_id"]))
            self._event(connection, task["task_id"], "TASK_CLAIMED", {"fence": fence})
            return Lease(task["task_id"], worker_id, fence)

    claim = claim_next

    def _lease(self, connection: sqlite3.Connection, lease: Lease) -> sqlite3.Row:
        task = self._row(connection, lease.task_id)
        if (task["state"] != "RUNNING" or task["lease_worker"] != lease.worker_id
                or task["fence"] != lease.fence or task["lease_deadline"] <= self.clock()):
            raise CodingStoreError("STALE_LEASE", "The worker no longer owns this task action")
        return task

    def guard(self, lease: Lease) -> dict[str, Any]:
        error = None
        self.reconcile()
        with self._transaction() as connection:
            task = self._lease(connection, lease)
            self._accrue(connection, task, self.clock())
            task = self._row(connection, lease.task_id)
            running = connection.execute(
                "SELECT 1 FROM coding_actions WHERE task_id=? AND status='RUNNING'", (lease.task_id,),
            ).fetchone()
            if not running and (task["pause_requested"] or task["active_seconds"] >= self._limits(task).active_seconds):
                state = "PAUSED" if task["pause_requested"] else "BUDGET_EXHAUSTED"
                self._release(connection, lease.task_id, state)
                self._event(connection, lease.task_id, f"TASK_{state}", {})
                error = CodingStoreError(state, "Task stopped at the next safe action boundary")
            result = self._task(connection, lease.task_id)
        if error:
            raise error
        return result

    def renew(self, lease: Lease, lease_seconds: float = 60) -> dict[str, Any]:
        if not 1 <= lease_seconds <= 300:
            raise CodingStoreError("INVALID_INPUT", "Lease must be between 1 and 300 seconds")
        with self._transaction() as connection:
            task = self._lease(connection, lease)
            self._accrue(connection, task, self.clock())
            connection.execute("UPDATE coding_tasks SET lease_deadline=? WHERE task_id=?",
                               (self.clock() + lease_seconds, lease.task_id))
            return self._task(connection, lease.task_id)

    def reserve_action(
        self, lease: Lease, kind: str, source_hash: str, plan_hash: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if kind not in {"PLAN", "EDIT", "EXECUTION"}:
            raise CodingStoreError("INVALID_INPUT", "Unknown coding action kind")
        _hash(source_hash)
        self.guard(lease)
        with self._transaction() as connection:
            task = self._lease(connection, lease)
            self._require_project_runner(connection, task)
            if task["pause_requested"]:
                raise CodingStoreError("PAUSED", "Task pause was requested")
            if connection.execute(
                "SELECT 1 FROM coding_actions WHERE task_id=? AND status='RUNNING'", (lease.task_id,),
            ).fetchone():
                raise CodingStoreError("ACTION_IN_FLIGHT", "Reconcile the current action before another one")
            brief = CodingBrief.model_validate_json(task["brief_json"])
            if kind != "PLAN":
                self._require_implementation(task)
            checkpoint = json.loads(task["checkpoint_json"])
            valid_sources = {brief.source_hash, checkpoint.get("candidate_source_hash"),
                             checkpoint.get("candidate_hash")}
            if source_hash not in valid_sources:
                raise CodingStoreError("STALE_SOURCE", "Action source is not a persisted task revision")
            if kind == "PLAN":
                if task["next_stage"] != "PLAN" or plan_hash is not None:
                    raise CodingStoreError("INVALID_STATE", "Plan generation is not the next action")
            elif not plan_hash or plan_hash != task["approved_plan_hash"]:
                raise CodingStoreError("PLAN_UNAPPROVED", "Action must pin the exact approved plan")
            if (kind == "EDIT" and task["next_stage"] != "EDIT") or (
                kind == "EXECUTION" and task["next_stage"] not in {"BASELINE", "CANDIDATE", "FINAL"}
            ):
                raise CodingStoreError("INVALID_STATE", "Action kind does not match the persisted next stage")
            model = int(kind in {"PLAN", "EDIT"})
            patch = int(kind == "EDIT")
            execution = int(kind == "EXECUTION")
            limits = self._limits(task)
            if (task["model_calls"] + model > limits.model_calls
                    or task["patch_attempts"] + patch > limits.patch_attempts
                    or task["executions"] + execution > limits.executions):
                raise CodingStoreError("BUDGET_EXHAUSTED", "Task action allowance is exhausted")
            day = datetime.fromtimestamp(self.clock(), UTC).date().isoformat()
            connection.execute("INSERT OR IGNORE INTO coding_daily_usage(day) VALUES(?)", (day,))
            daily = connection.execute("SELECT * FROM coding_daily_usage WHERE day=?", (day,)).fetchone()
            if ((model and daily["model_calls"] + model > self.operator_limits.model_calls_per_day)
                    or (execution and daily["executions"] + execution > self.operator_limits.executions_per_day)):
                raise CodingStoreError("OPERATOR_LIMIT", "Operator daily action allowance is disabled or exhausted")
            action_id = f"coding-action-{uuid.uuid4().hex[:16]}"
            connection.execute("""
                INSERT INTO coding_actions(action_id,task_id,kind,stage,status,worker_id,fence,
                                           source_hash,plan_hash,details_json,created_at)
                VALUES(?,?,?,?,'RUNNING',?,?,?,?,?,?)
            """, (action_id, lease.task_id, kind, task["next_stage"], lease.worker_id, lease.fence,
                  source_hash, plan_hash, _json(details or {}, 32_768), self.clock()))
            connection.execute("""
                UPDATE coding_tasks SET model_calls=model_calls+?,patch_attempts=patch_attempts+?,
                                        executions=executions+?,updated_at=? WHERE task_id=?
            """, (model, patch, execution, self.clock(), lease.task_id))
            connection.execute("""
                UPDATE coding_daily_usage SET model_calls=model_calls+?,executions=executions+? WHERE day=?
            """, (model, execution, day))
            self._event(connection, lease.task_id, "ACTION_RESERVED", {"action_id": action_id, "kind": kind})
            return self._task(connection, lease.task_id)["actions"][-1]

    def finish_action(
        self, lease: Lease, action_id: str, result: dict[str, Any], *,
        usage: dict[str, Any] | None = None, status: str = "SUCCEEDED",
        next_stage: str | None = None, checkpoint: dict[str, Any] | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"SUCCEEDED", "FAILED"}:
            raise CodingStoreError("INVALID_INPUT", "Action completion must be succeeded or failed")
        if next_stage is not None and next_stage not in _STAGES:
            raise CodingStoreError("INVALID_INPUT", "Unknown coding stage")
        if state is not None and state not in {
            "QUEUED", "AWAITING_APPROVAL", "PAUSED", "BLOCKED", "FAILED", "STALLED", "BUDGET_EXHAUSTED", "REVIEW_READY",
        }:
            raise CodingStoreError("INVALID_INPUT", "Unknown action completion state")
        result_json = _json(result, 131_072)
        usage_json = _json(usage if usage is not None else {"status": "UNKNOWN"}, 4_096)
        with self._transaction() as connection:
            task = self._lease(connection, lease)
            action = connection.execute("SELECT * FROM coding_actions WHERE action_id=? AND task_id=?",
                                        (action_id, lease.task_id)).fetchone()
            if (action is None or action["status"] != "RUNNING" or action["fence"] != lease.fence
                    or action["worker_id"] != lease.worker_id):
                raise CodingStoreError("STALE_ACTION", "Action result does not match the active reservation")
            if state == "AWAITING_APPROVAL":
                if action["kind"] != "PLAN" or status != "SUCCEEDED":
                    raise CodingStoreError("INVALID_STATE", "Only a generated plan can await approval")
                plan = self._plan(task, result.get("plan", {}))
                connection.execute("UPDATE coding_tasks SET plan_json=?,approved_plan_hash=NULL WHERE task_id=?",
                                   (_json(plan.model_dump()), lease.task_id))
            self._accrue(connection, task, self.clock())
            connection.execute("""
                UPDATE coding_actions SET status=?,result_json=?,usage_json=?,finished_at=? WHERE action_id=?
            """, (status, result_json, usage_json, self.clock(), action_id))
            connection.execute("UPDATE coding_tasks SET result_json=? WHERE task_id=?",
                               (result_json, lease.task_id))
            if next_stage is not None:
                connection.execute("UPDATE coding_tasks SET next_stage=? WHERE task_id=?",
                                   (next_stage, lease.task_id))
            if checkpoint is not None:
                connection.execute("UPDATE coding_tasks SET checkpoint_json=? WHERE task_id=?",
                                   (_json(checkpoint), lease.task_id))
            resulting_state = state
            if task["pause_requested"] and state != "AWAITING_APPROVAL" and state not in _TERMINAL:
                resulting_state = "PAUSED"
            if resulting_state is not None:
                self._release(connection, lease.task_id, resulting_state)
            if checkpoint is not None and resulting_state != "AWAITING_APPROVAL":
                self._save_checkpoint(connection, lease.task_id, next_stage or action["stage"],
                                      resulting_state or "RUNNING", checkpoint)
            self._event(connection, lease.task_id, "ACTION_FINISHED",
                        {"action_id": action_id, "status": status, "state": resulting_state or "RUNNING"})
            return self._task(connection, lease.task_id)

    def set_checkpoint(
        self, lease: Lease, next_stage: str, checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        if next_stage not in _STAGES:
            raise CodingStoreError("INVALID_INPUT", "Unknown coding stage")
        with self._transaction() as connection:
            task = self._lease(connection, lease)
            connection.execute("UPDATE coding_tasks SET next_stage=?,checkpoint_json=?,updated_at=? WHERE task_id=?",
                               (next_stage, _json(checkpoint), self.clock(), lease.task_id))
            self._save_checkpoint(connection, lease.task_id, next_stage, task["state"], checkpoint)
            return self._task(connection, lease.task_id)

    def finish_task(
        self, lease: Lease, state: str, result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if state not in _TERMINAL | {"PAUSED"}:
            raise CodingStoreError("INVALID_INPUT", "Unknown task completion state")
        with self._transaction() as connection:
            task = self._lease(connection, lease)
            if connection.execute("SELECT 1 FROM coding_actions WHERE task_id=? AND status='RUNNING'",
                                  (lease.task_id,)).fetchone():
                raise CodingStoreError("ACTION_IN_FLIGHT", "Finish or reconcile the active action first")
            self._accrue(connection, task, self.clock())
            connection.execute("UPDATE coding_tasks SET result_json=? WHERE task_id=?",
                               (_json(result or {}), lease.task_id))
            self._release(connection, lease.task_id, state)
            self._event(connection, lease.task_id, f"TASK_{state}", {})
            return self._task(connection, lease.task_id)

    def control(self, owner_ref: str, task_id: str, command: str) -> dict[str, Any]:
        if command not in {"pause", "resume", "cancel", "retry"}:
            raise CodingStoreError("INVALID_INPUT", "Unknown coding control")
        self.reconcile()
        with self._transaction() as connection:
            task = self._owned(connection, owner_ref, task_id)
            if command == "cancel":
                if task["state"] in {"CANCELLED", "CANCEL_PENDING"}:
                    return self._task(connection, task_id)
                if task["state"] in _TERMINAL:
                    raise CodingStoreError("INVALID_STATE", "Completed tasks cannot be cancelled")
                execution = connection.execute("""
                    SELECT 1 FROM coding_actions WHERE task_id=? AND kind='EXECUTION'
                    AND status IN ('RUNNING','INTERRUPTED')
                """, (task_id,)).fetchone()
                self._interrupt(connection, task, "CANCEL_PENDING" if execution else "CANCELLED")
            elif command == "pause":
                if task["state"] == "PAUSED" or task["pause_requested"]:
                    return self._task(connection, task_id)
                if task["state"] not in {"QUEUED", "RUNNING"}:
                    raise CodingStoreError("INVALID_STATE", "Only scheduled work can pause")
                if task["state"] == "RUNNING":
                    connection.execute("UPDATE coding_tasks SET pause_requested=1 WHERE task_id=?", (task_id,))
                else:
                    self._release(connection, task_id, "PAUSED")
                self._event(connection, task_id, "PAUSE_REQUESTED", {})
            else:
                if task["next_stage"] != "PLAN":
                    self._require_implementation(task)
                if task["state"] not in {"PAUSED", "INTERRUPTED"}:
                    raise CodingStoreError("INVALID_STATE", "Task is not paused or interrupted")
                uncertain = connection.execute("""
                    SELECT action_id,status,kind FROM coding_actions WHERE task_id=?
                    AND status IN ('UNKNOWN','INTERRUPTED','INTERRUPTED_STOPPED')
                """, (task_id,)).fetchall()
                if any(action["kind"] == "EXECUTION" and action["status"] == "INTERRUPTED" for action in uncertain):
                    raise CodingStoreError("RECONCILIATION_REQUIRED", "Confirm the previous container stopped before retry")
                if uncertain and command != "retry":
                    raise CodingStoreError("RECONCILIATION_REQUIRED", "A previous action may have run; explicit retry is required")
                self._busy(connection, task_id)
                if command == "retry":
                    connection.execute("""
                        UPDATE coding_actions SET status='RETRY_ACKNOWLEDGED'
                        WHERE task_id=? AND status IN ('UNKNOWN','INTERRUPTED_STOPPED')
                    """, (task_id,))
                connection.execute("UPDATE coding_tasks SET state='QUEUED',pause_requested=0,updated_at=? WHERE task_id=?",
                                   (self.clock(), task_id))
                self._event(connection, task_id, "TASK_RESUMED",
                            {"explicit_retry": command == "retry", "unknown_actions": len(uncertain)})
            return self._task(connection, task_id)

    def reconcile_execution(
        self, task_id: str, operation_id: str, *, stopped: bool,
    ) -> dict[str, Any]:
        _token(operation_id, "container operation identity")
        with self._transaction() as connection:
            task = self._row(connection, task_id)
            matches = [action for action in connection.execute(
                "SELECT * FROM coding_actions WHERE task_id=? AND kind='EXECUTION'",
                (task_id,),
            ) if json.loads(action["details_json"]).get("operation_id") == operation_id]
            if len(matches) != 1:
                raise CodingStoreError("NOT_FOUND", "No execution reservation matches this operation")
            action = matches[0]
            if stopped and action["status"] == "INTERRUPTED":
                connection.execute("UPDATE coding_actions SET status='INTERRUPTED_STOPPED' WHERE action_id=?",
                                   (action["action_id"],))
                self._event(connection, task_id, "EXECUTION_STOP_CONFIRMED", {"action_id": action["action_id"]})
                if task["state"] == "CANCEL_PENDING":
                    self._release(connection, task_id, "CANCELLED")
                    self._event(connection, task_id, "TASK_CANCELLED", {})
            return self._task(connection, task_id)

    def pending_executions(self) -> list[dict[str, Any]]:
        self.reconcile()
        with self._transaction() as connection:
            pending = []
            for action in connection.execute("""
                SELECT coding_actions.* FROM coding_actions JOIN coding_tasks USING(task_id)
                WHERE kind='EXECUTION' AND status='INTERRUPTED'
                AND state IN ('INTERRUPTED','CANCEL_PENDING') ORDER BY coding_actions.created_at
            """):
                operation_id = json.loads(action["details_json"]).get("operation_id")
                if operation_id:
                    pending.append({"task_id": action["task_id"], "action_id": action["action_id"],
                                    "operation_id": operation_id})
            return pending

    def list_checkpoints(self, owner_ref: str, task_id: str) -> list[dict[str, Any]]:
        self.reconcile()
        with self._transaction() as connection:
            self._owned(connection, owner_ref, task_id)
            rows = connection.execute(
                "SELECT * FROM coding_checkpoints WHERE task_id=? ORDER BY sequence ASC",
                (task_id,),
            ).fetchall()
            checkpoints = []
            for r in rows:
                item = dict(r)
                item["checkpoint"] = json.loads(item.pop("checkpoint_json"))
                checkpoints.append(item)
            return checkpoints

    def get_checkpoint(self, owner_ref: str, task_id: str, checkpoint_id: str) -> dict[str, Any]:
        _token(checkpoint_id, "checkpoint identity")
        self.reconcile()
        with self._transaction() as connection:
            self._owned(connection, owner_ref, task_id)
            row = connection.execute(
                "SELECT * FROM coding_checkpoints WHERE task_id=? AND checkpoint_id=?",
                (task_id, checkpoint_id),
            ).fetchone()
            if row is None:
                raise CodingStoreError("NOT_FOUND", f"Checkpoint '{checkpoint_id}' not found")
            item = dict(row)
            item["checkpoint"] = json.loads(item.pop("checkpoint_json"))
            return item

    def restore_checkpoint(
        self, owner_ref: str, task_id: str, checkpoint_id: str, *,
        expected_checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        _token(checkpoint_id, "checkpoint identity")
        if expected_checkpoint_id is not None:
            _token(expected_checkpoint_id, "expected checkpoint identity")
        self.reconcile()
        with self._transaction() as connection:
            task = self._owned(connection, owner_ref, task_id)
            if task["state"] == "RUNNING" and task["lease_deadline"] and task["lease_deadline"] > self.clock():
                raise CodingStoreError("INVALID_STATE", "Cannot restore while task is actively running")
            if task["state"] == "CANCEL_PENDING":
                raise CodingStoreError("INVALID_STATE", "Cannot restore a task pending cancellation")
            if connection.execute("SELECT 1 FROM coding_actions WHERE task_id=? AND status='RUNNING'",
                                  (task_id,)).fetchone():
                raise CodingStoreError("ACTION_IN_FLIGHT", "Cannot restore while an action is in flight")
            target = connection.execute(
                "SELECT * FROM coding_checkpoints WHERE task_id=? AND checkpoint_id=?",
                (task_id, checkpoint_id),
            ).fetchone()
            if target is None:
                raise CodingStoreError("NOT_FOUND", f"Checkpoint '{checkpoint_id}' not found")
            latest = connection.execute(
                "SELECT checkpoint_id FROM coding_checkpoints WHERE task_id=? ORDER BY sequence DESC LIMIT 1",
                (task_id,),
            ).fetchone()
            if expected_checkpoint_id is not None and (latest is None or latest["checkpoint_id"] != expected_checkpoint_id):
                raise CodingStoreError("CONFLICT", "Current checkpoint does not match expected checkpoint")

            target_checkpoint = json.loads(target["checkpoint_json"])
            restored_stage = target["stage"]
            if restored_stage != "PLAN":
                self._require_implementation(task)
            connection.execute("""
                UPDATE coding_tasks
                SET next_stage=?, checkpoint_json=?, state='PAUSED', pause_requested=0,
                    lease_worker=NULL, lease_deadline=NULL, active_since=NULL, updated_at=?
                WHERE task_id=?
            """, (restored_stage, target["checkpoint_json"], self.clock(), task_id))
            new_chk_id = self._save_checkpoint(connection, task_id, restored_stage, "PAUSED", target_checkpoint)
            self._event(connection, task_id, "CHECKPOINT_RESTORED", {
                "restored_from": checkpoint_id,
                "new_checkpoint_id": new_chk_id,
                "stage": restored_stage,
                "candidate_hash": target_checkpoint.get("candidate_hash"),
            })
            return self._task(connection, task_id)

    def export_bundle(self, owner_ref: str, task_id: str) -> dict[str, Any]:
        self.reconcile()
        with self._transaction() as connection:
            self._owned(connection, owner_ref, task_id)
            task_data = self._task(connection, task_id)
            events = [
                {"sequence": r["sequence"], "event_type": r["event_type"],
                 "payload": json.loads(r["payload_json"]), "created_at": r["created_at"]}
                for r in connection.execute(
                    "SELECT * FROM coding_events WHERE task_id=? ORDER BY sequence ASC",
                    (task_id,),
                ).fetchall()
            ]
            chk = task_data.get("checkpoint") or {}
            patch = chk.get("patch") or {}
            manifest_files = [
                {"path": p, "bytes": len(content.encode("utf-8"))}
                for p, content in sorted((task_data.get("source_files") or {}).items())
            ]
            reports = {}
            if chk.get("baseline"):
                reports["baseline"] = chk["baseline"]
            if chk.get("last_candidate"):
                reports["last_candidate"] = chk["last_candidate"]
            if chk.get("final"):
                reports["final"] = chk["final"]
            runtime = task_data.get("runtime_config") or {}
            runtime_manifest = {
                key: runtime[key] for key in ("model_id", "max_output_tokens", "engine_version")
                if key in runtime
            }
            policy = runtime.get("generation_policy")
            if isinstance(policy, dict):
                runtime_manifest["generation_policy"] = {
                    key: policy[key] for key in ("version", "sha256") if key in policy
                }
            return {
                "schema_version": "coding-bundle-v1",
                "task_id": task_id,
                "fixture_id": task_data["fixture_id"],
                "state": task_data["state"],
                "contract_hash": task_data["contract_hash"],
                "runtime_config": runtime_manifest,
                "created_at": task_data["created_at"],
                "exported_at": self.clock(),
                "brief": task_data["brief"],
                "plan": task_data.get("plan"),
                "approved_plan_hash": task_data.get("approved_plan_hash"),
                "source_manifest": {
                    "file_count": len(manifest_files),
                    "source_hash": task_data["brief"]["source_hash"],
                    "files": manifest_files,
                },
                "patch": {
                    "diff": patch.get("diff", ""),
                    "author": patch.get("author"),
                    "candidate_hash": chk.get("candidate_hash"),
                    "target_files": patch.get("target_files", []),
                },
                "test_reports": reports,
                "counters": task_data["counters"],
                "limits": task_data["limits"],
                "events": events,
            }

    def export_bundle_zip(self, owner_ref: str, task_id: str) -> bytes:
        bundle = self.export_bundle(owner_ref, task_id)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(bundle, indent=2))
            diff_text = bundle["patch"].get("diff", "")
            if diff_text:
                zf.writestr("patch.diff", diff_text)
            if bundle.get("plan"):
                zf.writestr("plan.json", json.dumps(bundle["plan"], indent=2))
            if bundle.get("test_reports"):
                zf.writestr("test_reports.json", json.dumps(bundle["test_reports"], indent=2))
            zf.writestr("events.json", json.dumps(bundle["events"], indent=2))
            summary_lines = [
                f"# Task Export: {bundle['task_id']}",
                f"- Project / Fixture: {bundle['fixture_id']}",
                f"- State: {bundle['state']}",
                f"- Created At: {datetime.fromtimestamp(bundle['created_at'], UTC).isoformat()}",
                f"- Exported At: {datetime.fromtimestamp(bundle['exported_at'], UTC).isoformat()}",
                "",
                "## Task Brief",
                f"{bundle['brief'].get('task', '')}",
                "",
                "## Counters & Limits",
                f"- Model Calls: {bundle['counters']['model_calls']} / {bundle['limits']['model_calls']}",
                f"- Patch Attempts: {bundle['counters']['patch_attempts']} / {bundle['limits']['patch_attempts']}",
                f"- Test Executions: {bundle['counters']['executions']} / {bundle['limits']['executions']}",
                f"- Active Seconds: {bundle['counters']['active_seconds']:.2f}s / {bundle['limits']['active_seconds']}s",
                "",
                "## Diff",
                "```diff",
                diff_text if diff_text else "(No patch generated)",
                "```",
            ]
            zf.writestr("summary.md", "\n".join(summary_lines))
        buffer.seek(0)
        return buffer.getvalue()
