"""Execution adapter contract and snapshot preparation."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from benchproof.fixtures import assert_no_trusted_assets, source_hash_for_dir

LAUNCHER_DIR = Path(__file__).resolve().parents[2] / "runner" / "launcher"


class RunnerUnavailable(Exception):
    """The runner cannot execute (daemon down, image missing, access not granted)."""


@dataclass
class Snapshot:
    """A fresh, candidate-only copy of one fixture's app/ tree."""

    run_id: str
    root: Path  # temp dir; root/"candidate"/"app" is the mount source
    source_hash: str

    @property
    def candidate_dir(self) -> Path:
        return self.root / "candidate"

    @property
    def app_dir(self) -> Path:
        return self.candidate_dir / "app"

    @property
    def out_dir(self) -> Path:
        return self.root / "out"

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


@dataclass
class ExecutionResult:
    runner: str
    run_id: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str
    observations: dict[str, Any] | None
    image_ref: str | None = None
    operation_id: str | None = None
    isolation: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None

    def to_record(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["stdout"] = self.stdout[-4000:]
        d["stderr"] = self.stderr[-4000:]
        return d


class ExecutionAdapter(Protocol):
    name: str

    def available(self) -> tuple[bool, str]: ...

    def run_observation(self, snapshot: Snapshot, timeout_s: int = 60, **kwargs: Any) -> ExecutionResult: ...

    def cancel(self, run_id: str) -> bool: ...

    def collect_artifacts(self, snapshot: Snapshot) -> list[Path]: ...


def prepare_snapshot(app_dir: Path, base_dir: Path | None = None) -> Snapshot:
    """Copy exactly the candidate-visible app/ tree into a fresh temp directory."""
    app_dir = Path(app_dir)
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    root = Path(tempfile.mkdtemp(prefix=f"bp-{run_id}-", dir=str(base_dir) if base_dir else None))
    dst = root / "candidate" / "app"
    shutil.copytree(app_dir, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (root / "out").mkdir()
    assert_no_trusted_assets(dst)
    return Snapshot(run_id=run_id, root=root, source_hash=source_hash_for_dir(dst))
