"""Project test execution adapter (C-04).

Executes unittest/pytest test suites for user-provided projects inside
the isolated container runner, strictly bounding runtime and output.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchproof.execution.base import (
    LAUNCHER_DIR,
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
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    root = Path(tempfile.mkdtemp(prefix=f"bp-proj-{run_id}-", dir=str(base_dir) if base_dir else None))
    candidate = root / "candidate"
    app_dir = candidate / "app"
    tests_dir = candidate / "tests"
    out_dir = root / "out"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.chmod(0o777)

    manifest: dict[str, str] = {}
    if isinstance(target, dict):
        app_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, content in target.items():
            dest = candidate / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            canonical = content.replace("\r\n", "\n")
            dest.write_text(canonical, encoding="utf-8")
            manifest[rel_path] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    else:
        src_root = target.parent if (target.name == "app" and (target.parent / "tests").exists()) else target
        if (src_root / "app").exists():
            shutil.copytree(src_root / "app", app_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if (src_root / "tests").exists():
            shutil.copytree(src_root / "tests", tests_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        for file_path in candidate.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".pyc"):
                rel = file_path.relative_to(candidate).as_posix()
                text = file_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
                manifest[rel] = hashlib.sha256(text.encode("utf-8")).hexdigest()

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
        # Check docker availability
        ok, detail = self.runner.available()
        if not ok:
            raise RunnerUnavailable(f"Docker runner unavailable: {detail}")

        # Execute container running run_project_tests.py
        # Docker command runs: python /launcher/run_project_tests.py --candidate /candidate --out /out
        import subprocess
        import time

        start_time = time.monotonic()
        cid = f"bp-proj-{operation_id[:24]}"
        cmd = [
            "docker", "run", "--rm",
            "--name", cid,
            "--network", "none",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--memory", "256m",
            "--memory-swap", "256m",
            "--cpus", "1.0",
            "--pids-limit", "64",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "-v", f"{snapshot.candidate_dir}:/candidate:ro",
            "-v", f"{LAUNCHER_DIR}:/launcher:ro",
            "-v", f"{snapshot.out_dir}:/out:rw",
            "-w", "/out",
            "benchproof-candidate:dev",
            "python", f"/launcher/{PROJECT_LAUNCHER_FILE}",
            "--candidate", "/candidate",
            "--out", "/out",
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(["docker", "kill", cid], capture_output=True, check=False)
            stdout, stderr = proc.communicate()

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Parse observation from stdout
        observations = None
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and parsed.get("schema") == OBSERVATION_SCHEMA:
                    observations = parsed
                    break
            except ValueError:
                continue

        return ExecutionResult(
            runner="docker",
            run_id=operation_id,
            exit_code=proc.returncode,
            timed_out=timed_out,
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
            observations=observations,
            isolation={"enforced": True, "network_none": True},
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

        test_count = test_results.get("test_count", 0)
        passed_tests = test_results.get("passed", [])
        failures = test_results.get("failures", [])
        errors = test_results.get("errors", [])
        skipped = test_results.get("skipped", [])
        obs_error = test_results.get("error")

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
                    "passed": True,
                })

            all_passed = (len(failures) == 0 and len(errors) == 0 and test_count > 0)
            verdict = "VERIFIED" if all_passed else "REJECTED"

        if result.error or result.timed_out or result.exit_code != 0:
            verdict = "INCONCLUSIVE"

        execution_record = result.to_record()
        observation = execution_record.pop("observations", None)
        obs_sha = hashlib.sha256(
            json.dumps(observation, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        execution_record["observation_sha256"] = obs_sha

        return {
            "profile": f"project-{runner_profile}-v1",
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
