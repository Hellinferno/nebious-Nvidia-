"""Owner-scoped, short coding-task controls; inference runs only in the worker."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from benchproof.coding.generation import CodingBrief, CodingPlan, SourceHash
from benchproof.coding.runtime import ADMISSION_MESSAGES, CodingRuntimeConfig
from benchproof.coding.store import CodingStore, CodingStoreError
from benchproof.constraints import contract_hash
from benchproof.execution.project_runner import PROJECT_CONTRACT_HASH
from benchproof.fixtures import candidate_files, fixture_dir, list_fixture_ids, source_hash_for_dir
from benchproof.projects.store import ProjectStore


class CreateCodingTask(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    fixture_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    project_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    task: str = Field(min_length=1, max_length=4_000)
    source_hash: SourceHash
    editable_paths: list[str] = Field(min_length=1, max_length=3)


class ApproveCodingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    plan_hash: SourceHash


class EmptyControl(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def _key(value: str | None) -> str:
    if value is None:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_REQUIRED", "message": "Idempotency-Key is required."})
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise HTTPException(400, detail={"code": "INVALID_INPUT", "message": "Invalid Idempotency-Key."})
    return value


def _snapshot(fixture_id: str, source_hash: str) -> dict[str, str]:
    if fixture_id not in list_fixture_ids():
        raise CodingStoreError("NOT_FOUND", "Prepared project not found")
    app_dir = fixture_dir(fixture_id) / "app"
    files = candidate_files(app_dir)
    if not 1 <= len(files) <= 20 or app_dir.is_symlink():
        raise CodingStoreError("STORAGE_LIMIT", "Prepared project exceeds the supported source profile")
    source = {}
    total_bytes = 0
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(app_dir.resolve()):
            raise CodingStoreError("INVALID_INPUT", "Linked prepared source is unsupported")
        if path.stat().st_size > 24_576:
            raise CodingStoreError("STORAGE_LIMIT", "Prepared source file exceeds its byte allowance")
        raw = path.read_bytes()
        total_bytes += len(raw)
        if total_bytes > 131_072:
            raise CodingStoreError("STORAGE_LIMIT", "Prepared project exceeds its byte allowance")
        source[path.relative_to(app_dir.parent).as_posix()] = raw.decode("utf-8")
    if source_hash_for_dir(app_dir) != source_hash:
        raise CodingStoreError("STALE_SOURCE", "The prepared project changed; select its current source revision")
    return source


def _project_snapshot(db_path: Path, project_id: str, owner: str, source_hash: str) -> dict[str, str]:
    proj = ProjectStore(db_path).get_project(project_id, owner_ref=owner)
    if proj is None:
        raise CodingStoreError("NOT_FOUND", f"Project '{project_id}' not found")
    if proj.source_hash != source_hash:
        raise CodingStoreError("STALE_SOURCE", "The project source changed; select its current source revision")
    return proj.files


def _public_task(task: dict[str, Any]) -> dict[str, Any]:
    return {key: task.get(key) for key in (
        "task_id", "fixture_id", "brief", "contract_hash", "runtime_config", "plan",
        "approved_plan_hash", "state", "next_stage", "checkpoint", "result", "counters",
        "limits", "pause_requested", "created_at", "updated_at",
    )}


def coding_router(
    owner_dependency: Callable[..., str],
    database_path: Callable[[], Path],
    runtime_config: Callable[[], CodingRuntimeConfig],
    provider_ready: Callable[[], bool],
    runner_ready: Callable[[], bool],
    model_id: Callable[[], str],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/coding-tasks", tags=["coding-tasks"])

    def store() -> CodingStore:
        return CodingStore(database_path(), runtime_config().operator_limits())

    def owned_call(operation: Callable[[CodingStore], Any]) -> Any:
        try:
            return operation(store())
        except CodingStoreError as exc:
            status = {
                "NOT_FOUND": 404, "INVALID_INPUT": 422, "STORAGE_LIMIT": 413,
                "OPERATOR_LIMIT": 429, "BUSY": 429,
            }.get(exc.code, 409)
            raise HTTPException(status, detail={"code": exc.code, "message": str(exc)}) from exc

    def require_admission() -> None:
        code = runtime_config().blocked_reason(
            provider_configured=provider_ready(), runner_ready=runner_ready(),
        )
        if code:
            raise HTTPException(503, detail={"code": code, "message": ADMISSION_MESSAGES[code]})

    def expected_runtime() -> dict[str, Any]:
        return {
            "model_id": model_id(), "max_output_tokens": runtime_config().max_output_tokens,
            "engine_version": "coding-engine-v1",
        }

    @router.post("", status_code=201)
    def create_task(
        body: CreateCodingTask,
        owner: str = Depends(owner_dependency),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        key = _key(idempotency_key)
        require_admission()

        if (body.fixture_id is None and body.project_id is None) or (body.fixture_id and body.project_id):
            raise HTTPException(422, detail={"code": "INVALID_INPUT", "message": "Specify exactly one of fixture_id or project_id."})

        def create(records: CodingStore) -> dict[str, Any]:
            brief = CodingBrief(
                task=body.task, source_hash=body.source_hash, editable_paths=body.editable_paths,
            )
            if body.project_id:
                target_id = body.project_id
                source = _project_snapshot(database_path(), body.project_id, owner, body.source_hash)
                task_contract = PROJECT_CONTRACT_HASH
            else:
                target_id = body.fixture_id  # type: ignore[assignment]
                source = _snapshot(body.fixture_id, body.source_hash)  # type: ignore[arg-type]
                task_contract = contract_hash()

            return records.create_task(
                owner, target_id, brief, source, task_contract, key,
                runtime_config=expected_runtime(),
            )

        try:
            return _public_task(owned_call(create))
        except ValueError as exc:
            raise HTTPException(422, detail={"code": "INVALID_INPUT", "message": "Unsupported task or source profile."}) from exc

    @router.get("")
    def list_tasks(owner: str = Depends(owner_dependency), limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
        return [_public_task(task) for task in owned_call(lambda records: records.list_tasks(owner))[:limit]]

    @router.get("/{task_id}")
    def get_task(task_id: str, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        return _public_task(owned_call(lambda records: records.get_task(owner, task_id)))

    @router.get("/{task_id}/source")
    def source(task_id: str, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        task = owned_call(lambda records: records.get_task(owner, task_id))
        return {"source_hash": task["brief"]["source_hash"], "files": task["source_files"]}

    @router.get("/{task_id}/plan")
    def get_plan(task_id: str, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        task = owned_call(lambda records: records.get_task(owner, task_id))
        plan = CodingPlan.model_validate(task["plan"]) if task["plan"] else None
        return {
            "state": task["state"], "plan": task["plan"],
            "plan_hash": plan.identity() if plan else None, "approved_plan_hash": task["approved_plan_hash"],
        }

    def enqueue(owner: str, task_id: str, phase: str, key: str | None) -> dict[str, Any]:
        token = _key(key)
        task = owned_call(lambda records: records.get_task(owner, task_id))
        require_admission()
        pinned = task.get("runtime_config") or {}
        if any(pinned.get(key) != value for key, value in expected_runtime().items()):
            raise HTTPException(409, detail={"code": "STALE_RUNTIME", "message": "The configured coding runtime differs from this task's pinned model or output allowance."})
        return _public_task(owned_call(lambda records: records.enqueue(owner, task_id, token, phase=phase)))

    @router.post("/{task_id}/plan", status_code=202)
    def queue_plan(
        task_id: str, body: EmptyControl | None = None,
        owner: str = Depends(owner_dependency),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        return enqueue(owner, task_id, "plan", idempotency_key)

    @router.post("/{task_id}/plan/edit")
    def edit_plan(task_id: str, body: CodingPlan, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        return _public_task(owned_call(lambda records: records.update_plan(owner, task_id, body)))

    @router.post("/{task_id}/approve")
    def approve(task_id: str, body: ApproveCodingPlan, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        return _public_task(owned_call(lambda records: records.approve_plan(owner, task_id, body.plan_hash)))

    @router.post("/{task_id}/start", status_code=202)
    def start(
        task_id: str, body: EmptyControl | None = None,
        owner: str = Depends(owner_dependency),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        return enqueue(owner, task_id, "run", idempotency_key)

    def control(owner: str, task_id: str, command: str) -> dict[str, Any]:
        return _public_task(owned_call(lambda records: records.control(owner, task_id, command)))

    @router.post("/{task_id}/pause")
    def pause(task_id: str, body: EmptyControl | None = None, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        return control(owner, task_id, "pause")

    @router.post("/{task_id}/resume", status_code=202)
    def resume(task_id: str, body: EmptyControl | None = None, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        owned_call(lambda records: records.get_task(owner, task_id))
        require_admission()
        return control(owner, task_id, "resume")

    @router.post("/{task_id}/cancel")
    def cancel(task_id: str, body: EmptyControl | None = None, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        return control(owner, task_id, "cancel")

    @router.get("/{task_id}/events")
    def events(task_id: str, after: int = Query(default=0, ge=0), owner: str = Depends(owner_dependency)) -> list[dict[str, Any]]:
        return owned_call(lambda records: records.list_events(owner, task_id, after_sequence=after))

    @router.get("/{task_id}/changes")
    def changes(task_id: str, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        task = owned_call(lambda records: records.get_task(owner, task_id))
        patch = (task["checkpoint"] or {}).get("patch") or {}
        return {
            "state": task["state"], "base_source_hash": task["brief"]["source_hash"],
            "candidate_source_hash": (task["checkpoint"] or {}).get("candidate_hash"),
            "diff": patch.get("diff", ""), "author": patch.get("author"),
            "tested_final": task["state"] == "REVIEW_READY",
        }

    @router.get("/{task_id}/executions")
    def executions(task_id: str, owner: str = Depends(owner_dependency)) -> list[dict[str, Any]]:
        task = owned_call(lambda records: records.get_task(owner, task_id))
        return [
            {key: action.get(key) for key in ("action_id", "stage", "status", "details", "result")}
            for action in task["actions"] if action["kind"] == "EXECUTION"
        ]

    @router.get("/{task_id}/usage")
    def usage(task_id: str, owner: str = Depends(owner_dependency)) -> dict[str, Any]:
        task = owned_call(lambda records: records.get_task(owner, task_id))
        model_actions = [action for action in task["actions"] if action["kind"] in {"PLAN", "EDIT"}]
        known_tokens = 0
        unknown = 0
        for action in model_actions:
            recorded = action.get("usage") or {}
            tokens = (recorded.get("usage") or recorded).get("total_tokens")
            if type(tokens) is int and tokens >= 0:
                known_tokens += tokens
            else:
                unknown += 1
        return {
            "counters": task["counters"], "limits": task["limits"], "recorded_tokens": known_tokens,
            "unknown_model_actions": unknown, "monetary_cost": "UNKNOWN",
            "hard_token_cap": False,
            "output_tokens_per_call": (task.get("runtime_config") or {}).get("max_output_tokens"),
        }

    return router
