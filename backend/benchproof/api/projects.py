"""Owner-scoped project intake and retrieval router (C-04)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from benchproof.projects.intake import ProjectIntakeError
from benchproof.projects.store import ProjectStore, ProjectStoreError


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=100)
    runner_profile: str = Field(default="unittest", pattern=r"^(unittest|pytest)$")
    files: dict[str, str] = Field(min_length=1, max_length=20)


def projects_router(
    owner_dependency: Callable[..., str],
    database_path: Callable[[], Path],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    def store() -> ProjectStore:
        return ProjectStore(database_path())

    @router.post("", status_code=201)
    def create_project(
        payload: CreateProjectRequest,
        owner: str = Depends(owner_dependency),
    ) -> dict[str, Any]:
        try:
            record = store().create_project(
                owner_ref=owner,
                name=payload.name,
                files=payload.files,
                runner_profile=payload.runner_profile,
            )
            return record.to_dict()
        except ProjectIntakeError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        except ProjectStoreError as exc:
            status = 413 if exc.code == "STORAGE_LIMIT" else 400
            raise HTTPException(
                status_code=status,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

    @router.get("")
    def list_projects(
        owner: str = Depends(owner_dependency),
    ) -> list[dict[str, Any]]:
        return store().list_projects(owner)

    @router.get("/{project_id}")
    def get_project(
        project_id: str,
        owner: str = Depends(owner_dependency),
    ) -> dict[str, Any]:
        record = store().get_project(project_id, owner_ref=owner)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": f"Project '{project_id}' not found"},
            )
        return record.to_dict()

    @router.get("/{project_id}/source")
    def get_project_source(
        project_id: str,
        path: str | None = Query(default=None),
        owner: str = Depends(owner_dependency),
    ) -> dict[str, Any]:
        record = store().get_project(project_id, owner_ref=owner)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": f"Project '{project_id}' not found"},
            )
        if path is not None:
            if path not in record.files:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "NOT_FOUND", "message": f"File '{path}' not found in project"},
                )
            return {"path": path, "content": record.files[path]}
        return {"project_id": project_id, "files": record.files}

    @router.delete("/{project_id}")
    def delete_project(
        project_id: str,
        owner: str = Depends(owner_dependency),
    ) -> dict[str, Any]:
        deleted = store().delete_project(project_id, owner_ref=owner)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": f"Project '{project_id}' not found"},
            )
        return {"status": "deleted", "project_id": project_id}

    return router
