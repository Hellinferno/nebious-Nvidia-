"""Project models and manifests for user-provided small Python projects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProjectManifest:
    """Canonical manifest representing a validated project snapshot."""

    manifest_version: str
    runner_profile: str
    source_hash: str
    files: dict[str, str]
    app_files: list[str]
    test_files: list[str]
    total_files: int
    total_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectManifest:
        return cls(
            manifest_version=data["manifest_version"],
            runner_profile=data["runner_profile"],
            source_hash=data["source_hash"],
            files=dict(data["files"]),
            app_files=list(data["app_files"]),
            test_files=list(data["test_files"]),
            total_files=int(data["total_files"]),
            total_bytes=int(data["total_bytes"]),
        )


@dataclass(frozen=True)
class ProjectRecord:
    """Durable owner-scoped project record stored in SQLite."""

    project_id: str
    owner_ref: str
    name: str
    runner_profile: str
    source_hash: str
    manifest: ProjectManifest
    files: dict[str, str]
    created_at: float
    updated_at: float

    def to_summary(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "owner_ref": self.owner_ref,
            "name": self.name,
            "runner_profile": self.runner_profile,
            "source_hash": self.source_hash,
            "total_files": self.manifest.total_files,
            "total_bytes": self.manifest.total_bytes,
            "app_files": self.manifest.app_files,
            "test_files": self.manifest.test_files,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dict(self) -> dict[str, Any]:
        summary = self.to_summary()
        summary["manifest"] = self.manifest.to_dict()
        summary["files"] = self.files
        return summary
