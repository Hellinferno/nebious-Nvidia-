"""Project test execution adapter (C-04).

Executes unittest test suites for user-provided projects inside
the isolated container runner, strictly bounding runtime and output.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchproof.execution.base import (
    ExecutionResult,
    RunnerUnavailable,
    Snapshot,
)
from benchproof.execution.docker_runner import DockerRunner

PROJECT_LAUNCHER_FILE = "run_project_tests.py"
OBSERVATION_SCHEMA = "benchproof/project-observations-v1"
PROJECT_CONTRACT_HASH = hashlib.sha256(b"project-test-suite").hexdigest()


@dataclass
class ProjectSnapshot(Snapshot):
    """Snapshot containing candidate app/ and protected tests/ trees."""

    @property
    def tests_dir(self) -> Path:
        return self.candidate_dir / "tests"


def prepare_project_snapshot(
    target: Path | dict[str, str],
    base_dir: Path | None = None,
) -> ProjectSnapshot:
    """Create a temporary directory structure with app/ and tests/ from project files or directory."""
    path_pattern = re.compile(r"^(app|tests)/(?:[A-Za-z_][A-Za-z0-9_]*/)*[A-Za-z_][A-Za-z0-9_]*\.py$")
    if not isinstance(target, dict):
        source_root = target.parent if target.name == "app" else target
        source = {}
        if source_root.is_symlink():
            raise ValueError("Linked project roots are unsupported")
        for tree in (source_root / "app", source_root / "tests"):
            if tree.is_symlink():
                raise ValueError("Linked project directories are unsupported")
            if tree.exists():
                for path in tree.rglob("*"):
                    if path.is_symlink():
                        raise ValueError("Linked project files are unsupported")
                    if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                        if path.stat().st_size > 24_576 or len(source) >= 20:
                            raise ValueError("Project snapshot exceeds its file allowance")
                        source[path.relative_to(source_root).as_posix()] = path.read_text(encoding="utf-8")
        target = source
    if len(target) > 20 or any(not isinstance(path, str) or not path_pattern.fullmatch(path) or not isinstance(content, str) or "\x00" in content or len(content.encode("utf-8")) > 24_576 for path, content in target.items()):
        raise ValueError("Unsupported project snapshot paths or content")
    if sum(len(content.encode("utf-8")) for content in target.values()) > 131_072:
        raise ValueError("Project snapshot exceeds its total byte allowance")
    if len({path.casefold() for path in target}) != len(target):
        raise ValueError("Case-colliding snapshot paths are unsupported")
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    root = Path(tempfile.mkdtemp(prefix=f"bp-proj-{run_id}-", dir=str(base_dir) if base_dir else None))
    candidate = root / "candidate"
    app_dir = candidate / "app"
    tests_dir = candidate / "tests"
    out_dir = root / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.chmod(0o777)

    manifest: dict[str, str] = {}
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in target.items():
        dest = candidate / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        canonical = content.replace("\r\n", "\n")
        dest.write_text(canonical, encoding="utf-8", newline="\n")
        manifest[rel_path] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    source_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

    return ProjectSnapshot(run_id=run_id, root=root, source_hash=source_hash)


class ProjectExecutor:
    """Dispatches generic project test execution through isolated Docker runner or synthetic runner."""

    def __init__(
        self,
        runner: DockerRunner | None = None,
        *,
        synthetic_runner: Callable[[ProjectSnapshot, int], ExecutionResult] | None = None,
    ) -> None:
        self.runner = runner or DockerRunner()
        self.synthetic_runner = synthetic_runner
        self._cancelled: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def run(
        self,
        target: Path | dict[str, str],
        *,
        operation_id: str,
        timeout_s: int = 30,
        runner_profile: str = "unittest",
        should_cancel: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        if runner_profile != "unittest":
            raise ValueError("Only the unittest project profile is supported")
        with self._lock:
            cancelled = self._cancelled.setdefault(operation_id, threading.Event())

        snapshot = prepare_project_snapshot(target)
        snapshot.run_id = operation_id

        try:
            if self.synthetic_runner is not None:
                result = self.synthetic_runner(snapshot, timeout_s)
            else:
                # We reuse DockerRunner with the project launcher script
                # DockerRunner mounts snapshot.candidate_dir -> /candidate read-only,
                # LAUNCHER_DIR -> /launcher read-only, out_dir -> /out rw.
                result = self._run_docker_with_project_launcher(
                    snapshot,
                    timeout_s=timeout_s,
                    operation_id=operation_id,
                    should_cancel=lambda: cancelled.is_set() or bool(should_cancel and should_cancel()),
                )
                if not result.isolation.get("enforced") and not result.error:
                    raise RunnerUnavailable("Project execution isolation was not enforced")

            return self._evaluate_project_result(snapshot, result, runner_profile)
        finally:
            snapshot.cleanup()
            with self._lock:
                self._cancelled.pop(operation_id, None)

    def _run_docker_with_project_launcher(
        self,
        snapshot: ProjectSnapshot,
        *,
        timeout_s: int,
        operation_id: str,
        should_cancel: Callable[[], bool],
    ) -> ExecutionResult:
        return self.runner.run_observation(
            snapshot, timeout_s=timeout_s, operation_id=operation_id,
            should_cancel=should_cancel, launcher_file=PROJECT_LAUNCHER_FILE,
            launcher_args=["--candidate", "/candidate", "--out", "/out",
                           "--child-timeout", str(max(1, timeout_s - 2))],
        )

    def _evaluate_project_result(
        self,
        snapshot: ProjectSnapshot,
        result: ExecutionResult,
        runner_profile: str,
    ) -> dict[str, Any]:
        """Convert raw test observations into a structured check report."""
        obs = result.observations or {}
        test_results = obs.get("test_results", obs)
        invalid_record = not isinstance(test_results, dict)
        if invalid_record:
            test_results = {}

        test_count = test_results.get("test_count", 0)
        passed_tests = test_results.get("passed", [])
        failures = test_results.get("failures", [])
        errors = test_results.get("errors", [])
        skipped = test_results.get("skipped", [])
        obs_error = test_results.get("error")
        invalid_record = invalid_record or type(test_count) is not int or not 0 <= test_count <= 200
        invalid_record = invalid_record or not isinstance(passed_tests, list) or any(not isinstance(item, str) for item in passed_tests)
        for entries in (failures, errors, skipped):
            if not isinstance(entries, list) or len(entries) > 200 or any(not isinstance(item, dict) or not isinstance(item.get("test_id"), str) for item in entries):
                invalid_record = True
        if invalid_record:
            test_count, passed_tests, failures, errors, skipped = 0, [], [], [], []
            obs_error = "INVALID_CHECK_RECORD"

        checks: list[dict[str, Any]] = []

        if obs_error:
            checks.append({
                "check_id": obs_error,
                "status": "FAILED",
                "detail": test_results.get("detail", obs_error),
                "passed": False,
            })
            verdict = "REJECTED"
        elif test_count == 0:
            checks.append({
                "check_id": "ZERO_TESTS_COLLECTED",
                "status": "FAILED",
                "detail": "No test cases were discovered or collected",
                "passed": False,
            })
            verdict = "REJECTED"
        else:
            for t_id in passed_tests:
                checks.append({
                    "check_id": t_id,
                    "status": "PASSED",
                    "detail": "Test succeeded",
                    "passed": True,
                })
            for item in failures:
                checks.append({
                    "check_id": item["test_id"],
                    "status": "FAILED",
                    "detail": item.get("traceback", "Test failure"),
                    "passed": False,
                })
            for item in errors:
                checks.append({
                    "check_id": item["test_id"],
                    "status": "FAILED",
                    "detail": item.get("traceback", "Test error"),
                    "passed": False,
                })
            for item in skipped:
                checks.append({
                    "check_id": item["test_id"],
                    "status": "SKIPPED",
                    "detail": item.get("reason", "Skipped"),
                    "passed": False,
                })

            all_passed = (
                not failures and not errors and not skipped and type(test_count) is int
                and test_count > 0 and len(passed_tests) == test_count
                and len(set(passed_tests)) == test_count
            )
            verdict = "VERIFIED" if all_passed else "REJECTED"

        if invalid_record or result.error or result.timed_out or result.exit_code != 0:
            verdict = "INCONCLUSIVE"

        execution_record = result.to_record()
        observation = execution_record.pop("observations", None)
        obs_sha = hashlib.sha256(
            json.dumps(observation, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        execution_record["observation_sha256"] = obs_sha

        return {
            "profile": f"project-{runner_profile}-v1",
            "assurance": "user-supplied-project-checks-only",
            "source_hash": snapshot.source_hash,
            "contract_hash": PROJECT_CONTRACT_HASH,
            "evaluator_hash": hashlib.sha256(
                json.dumps([c["check_id"] for c in checks], sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "required_check_ids": sorted([c["check_id"] for c in checks]),
            "verdict": verdict,
            "checks": checks,
            "execution": execution_record,
            "summary": {
                "test_count": test_count,
                "passed": len(passed_tests),
                "failures": len(failures),
                "errors": len(errors),
                "skipped": len(skipped),
            },
        }

    def cancel(self, operation_id: str) -> bool:
        with self._lock:
            self._cancelled.setdefault(operation_id, threading.Event()).set()
        return self.runner.cancel_operation(operation_id)
