"""Single-action durable worker; no provider call is made by a request handler."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

from benchproof.coding.engine import CodingEngine
from benchproof.coding.generation import GenerationError
from benchproof.coding.store import CodingStore, CodingStoreError


class CodingWorker:
    def __init__(
        self,
        store: CodingStore,
        engine: CodingEngine,
        *,
        worker_id: str | None = None,
        live_enabled: bool = False,
        session_seconds_remaining: Callable[[], float] | None = None,
        lease_seconds: int = 120,
    ) -> None:
        if lease_seconds < 90:
            raise ValueError("The lease must outlast one bounded provider action")
        self.store = store
        self.engine = engine
        self.worker_id = worker_id or f"coding-worker-{uuid.uuid4().hex[:12]}"
        self.live_enabled = live_enabled
        self.session_seconds_remaining = session_seconds_remaining or (lambda: 0.0)
        self.lease_seconds = lease_seconds

    def _watch_action(
        self,
        stop: threading.Event,
        task: dict[str, Any],
        operation_id: str,
        lease: Any,
        execution: bool,
    ) -> None:
        last_renewed = time.monotonic()
        while not stop.wait(0.5):
            current = self.store.get_task(task["owner_ref"], task["task_id"])
            if current["state"] in {"CANCEL_PENDING", "CANCELLED", "INTERRUPTED"}:
                if execution:
                    self.engine.cancel(operation_id)
                continue
            if current["state"] != "RUNNING":
                continue
            active = current["counters"]["active_seconds"]
            active += max(0.0, self.store.clock() - (current["active_since"] or self.store.clock()))
            if active >= current["limits"]["active_seconds"]:
                if execution:
                    self.engine.cancel(operation_id)
                continue
            if time.monotonic() - last_renewed >= 10:
                try:
                    self.store.renew(lease, lease_seconds=self.lease_seconds)
                except CodingStoreError:
                    if execution:
                        self.engine.cancel(operation_id)
                last_renewed = time.monotonic()

    def run_once(self) -> dict[str, Any] | None:
        pending = self.store.pending_executions()
        if pending:
            previous = pending[0]
            stopped = self.engine.cancel(previous["operation_id"])
            task = self.store.reconcile_execution(
                previous["task_id"],
                previous["operation_id"],
                stopped=stopped,
            )
            return {
                "task_id": previous["task_id"],
                "state": task["state"],
                "code": "OPERATION_STOPPED" if stopped else "RECONCILIATION_PENDING",
            }
        if not self.engine.synthetic and not self.live_enabled:
            return {"code": "LIVE_DISABLED"}
        if not self.engine.synthetic and self.session_seconds_remaining() < 90:
            return {"code": "SESSION_WINDOW_INSUFFICIENT"}
        lease = self.store.claim_next(self.worker_id, lease_seconds=self.lease_seconds)
        if lease is None:
            return None
        action = None
        outcome = None
        stop = threading.Event()
        watcher = None
        try:
            task = self.store.guard(lease)
            self.engine.validate(task)
            stage = task["next_stage"]
            if (
                not self.engine.synthetic
                and stage == "BASELINE"
                and self.session_seconds_remaining() < 330
            ):
                task = self.store.finish_task(
                    lease, "BLOCKED", {"code": "SESSION_WINDOW_INSUFFICIENT"}
                )
                return {
                    "task_id": lease.task_id,
                    "state": task["state"],
                    "code": "SESSION_WINDOW_INSUFFICIENT",
                }
            kind = "PLAN" if stage == "PLAN" else "EDIT" if stage == "EDIT" else "EXECUTION"
            operation_id = f"bp-coding-{uuid.uuid4().hex}"
            action = self.store.reserve_action(
                lease,
                kind,
                source_hash=(
                    task["checkpoint"]["candidate_hash"]
                    if stage in {"CANDIDATE", "FINAL"}
                    else task["brief"]["source_hash"]
                ),
                plan_hash=task.get("approved_plan_hash"),
                details={
                    "stage": stage,
                    "operation_id": operation_id,
                    "max_output_tokens": self.engine.max_output_tokens
                    if kind != "EXECUTION"
                    else 0,
                },
            )
            self.store.guard(lease)
            watcher = threading.Thread(
                target=self._watch_action,
                args=(stop, task, operation_id, lease, kind == "EXECUTION"),
                daemon=True,
            )
            watcher.start()
            outcome = self.engine.perform(
                task,
                operation_id=operation_id,
                before_external=lambda: self.store.guard(lease),
            )
            task = self.store.finish_action(
                lease,
                action["action_id"],
                outcome.result,
                usage=outcome.usage,
                next_stage=outcome.next_stage,
                checkpoint=outcome.checkpoint,
                state=outcome.state,
            )
            return {"task_id": lease.task_id, "state": task["state"], "stage": task["next_stage"]}
        except GenerationError as exc:
            try:
                if action is not None:
                    task = self.store.finish_action(
                        lease,
                        action["action_id"],
                        {"code": exc.code, "message": str(exc), "provider": exc.metadata},
                        usage=exc.metadata or None,
                        status="FAILED",
                        state="BLOCKED",
                    )
                else:
                    task = self.store.finish_task(
                        lease, "BLOCKED", {"code": exc.code, "message": str(exc)}
                    )
            except CodingStoreError as stale:
                return {"task_id": lease.task_id, "code": stale.code}
            return {"task_id": lease.task_id, "state": task["state"], "code": exc.code}
        except CodingStoreError as exc:
            if action is not None and exc.code == "STORAGE_LIMIT":
                try:
                    self.store.finish_action(
                        lease,
                        action["action_id"],
                        {
                            "code": "RESULT_LIMIT",
                            "message": "The action result exceeded its persistence allowance",
                        },
                        usage=outcome.usage if outcome else None,
                        status="FAILED",
                        state="BLOCKED",
                    )
                except CodingStoreError:
                    pass
            elif action is not None and action["kind"] == "EXECUTION":
                operation_id = action["details"]["operation_id"]
                stopped = self.engine.cancel(operation_id)
                self.store.reconcile_execution(lease.task_id, operation_id, stopped=stopped)
            elif action is None and exc.code in {"OPERATOR_LIMIT", "BUDGET_EXHAUSTED"}:
                try:
                    self.store.finish_task(
                        lease,
                        "BUDGET_EXHAUSTED" if exc.code == "BUDGET_EXHAUSTED" else "BLOCKED",
                        {"code": exc.code},
                    )
                except CodingStoreError:
                    pass
            return {"task_id": lease.task_id, "code": exc.code}
        finally:
            stop.set()
            if watcher is not None:
                watcher.join(timeout=1)
                current = self.store.get_task(task["owner_ref"], lease.task_id)
                if action["kind"] == "EXECUTION" and current["state"] in {
                    "CANCEL_PENDING",
                    "INTERRUPTED",
                }:
                    operation_id = action["details"]["operation_id"]
                    stopped = self.engine.cancel(operation_id)
                    self.store.reconcile_execution(lease.task_id, operation_id, stopped=stopped)
