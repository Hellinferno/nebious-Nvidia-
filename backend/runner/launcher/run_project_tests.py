"""Protected launcher: runs generic project test suites inside isolated candidate container.

Runs INSIDE the candidate container (or in-process for development).
Mounted read-only from outside the candidate tree; depends only on standard library.

Parent-child process isolation:
- Parent: never imports candidate code. Spawns child, verifies isolation/network probes,
  verifies child's stdout against /out/observations.json, prints record as last stdout line,
  exits with os._exit(0).
- Child: adds candidate root to sys.path, discovers and executes unittests under tests/,
  captures individual check results, collection counts, and failure traces,
  emits one JSON line and exits with os._exit(0).

Zero tests collected is an explicit failure code ('ZERO_TESTS_COLLECTED').
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from typing import Any

SCHEMA = "benchproof/project-observations-v1"
SECRET_PATTERN = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|NEBIUS|CONTREE)", re.IGNORECASE)
MAX_CHILD_OUTPUT = 256 * 1024
DEFAULT_CHILD_TIMEOUT_S = 25.0


def probe(host: str, port: int) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=2):
            return {"denied": False, "detail": "connected"}
    except OSError as e:
        return {"denied": True, "detail": f"{type(e).__name__}: {e}"[:120]}


def environment(candidate: Path) -> dict[str, Any]:
    files = sorted(
        str(p.relative_to(candidate)).replace("\\", "/")
        for p in candidate.rglob("*")
        if p.is_file()
    )
    return {
        "secret_env_names": sorted(k for k in os.environ if SECRET_PATTERN.search(k)),
        "candidate_files": files,
        "network": {
            "internet": probe("1.1.1.1", 443),
            "metadata": probe("169.254.169.254", 80),
        },
        "cwd_writable": os.access(os.getcwd(), os.W_OK),
        "candidate_writable": os.access(str(candidate), os.W_OK),
        "python": sys.version.split()[0],
        "launcher_isolation": "child-process",
    }


def execute_tests(candidate: Path) -> dict[str, Any]:
    """Child side: discover and execute unittests under tests/."""
    sys.path.insert(0, str(candidate))
    # Also add candidate/app to sys.path so 'import foo' or 'from app import foo' works
    app_dir = candidate / "app"
    if app_dir.exists():
        sys.path.insert(0, str(app_dir))

    tests_dir = candidate / "tests"
    if not tests_dir.exists():
        return {
            "schema": SCHEMA,
            "error": "MISSING_TESTS_DIRECTORY",
            "detail": f"Tests directory not found at {tests_dir}",
            "test_count": 0,
            "passed": [],
            "failures": [],
            "errors": [],
            "skipped": [],
            "duration_ms": 0,
        }

    loader = unittest.defaultTestLoader
    try:
        suite = loader.discover(start_dir=str(tests_dir), pattern="test_*.py")
    except Exception as exc:  # noqa: BLE001
        return {
            "schema": SCHEMA,
            "error": "TEST_DISCOVERY_ERROR",
            "detail": f"{type(exc).__name__}: {exc}",
            "test_count": 0,
            "passed": [],
            "failures": [],
            "errors": [],
            "skipped": [],
            "duration_ms": 0,
        }

    test_count = suite.countTestCases()
    if test_count == 0:
        return {
            "schema": SCHEMA,
            "error": "ZERO_TESTS_COLLECTED",
            "detail": "No test cases discovered under tests/ matching 'test_*.py'",
            "test_count": 0,
            "passed": [],
            "failures": [],
            "errors": [],
            "skipped": [],
            "duration_ms": 0,
        }

    # Custom TestResult collector
    class BoundedResult(unittest.TestResult):
        def __init__(self) -> None:
            super().__init__()
            self.passed_tests: list[str] = []
            self.failed_tests: list[dict[str, str]] = []
            self.error_tests: list[dict[str, str]] = []
            self.skipped_tests: list[dict[str, str]] = []

        def addSuccess(self, test: unittest.TestCase) -> None:
            super().addSuccess(test)
            self.passed_tests.append(test.id())

        def addFailure(self, test: unittest.TestCase, err: Any) -> None:
            super().addFailure(test, err)
            formatted = self._exc_info_to_string(err, test)
            self.failed_tests.append({
                "test_id": test.id(),
                "traceback": formatted[-2000:],
            })

        def addError(self, test: unittest.TestCase, err: Any) -> None:
            super().addError(test, err)
            formatted = self._exc_info_to_string(err, test)
            self.error_tests.append({
                "test_id": test.id(),
                "traceback": formatted[-2000:],
            })

        def addSkip(self, test: unittest.TestCase, reason: str) -> None:
            super().addSkip(test, reason)
            self.skipped_tests.append({
                "test_id": test.id(),
                "reason": str(reason)[:500],
            })

    result = BoundedResult()
    start_time = time.monotonic()
    # Suppress unittest stderr spam during execution
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=lambda *args, **kwargs: result, verbosity=0)
    runner.run(suite)
    duration_ms = int((time.monotonic() - start_time) * 1000)

    return {
        "schema": SCHEMA,
        "error": None,
        "test_count": test_count,
        "passed": result.passed_tests,
        "failures": result.failed_tests,
        "errors": result.error_tests,
        "skipped": result.skipped_tests,
        "duration_ms": duration_ms,
    }


def child_main(candidate: Path) -> None:
    try:
        obs = execute_tests(candidate)
    except Exception as exc:  # noqa: BLE001
        obs = {
            "schema": SCHEMA,
            "error": "EXECUTION_CRASH",
            "detail": f"{type(exc).__name__}: {exc}",
            "test_count": 0,
            "passed": [],
            "failures": [],
            "errors": [],
            "skipped": [],
            "duration_ms": 0,
        }
    print(json.dumps(obs, sort_keys=True, separators=(",", ":")), flush=True)
    os._exit(0)


def parent_main(candidate: Path, out_dir: Path, timeout_s: float) -> None:
    env = environment(candidate)
    cmd = [sys.executable, str(Path(__file__).resolve()), "--child", "--candidate", str(candidate)]
    start = time.monotonic()
    timed_out = False
    stdout = ""

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            out, _err = proc.communicate(timeout=timeout_s)
            stdout = out
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            out, _err = proc.communicate()
            stdout = out
    except OSError as exc:
        stdout = json.dumps({"schema": SCHEMA, "error": f"SPAWN_ERROR: {exc}"})

    duration_ms = int((time.monotonic() - start) * 1000)
    obs = None
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict) and parsed.get("schema") == SCHEMA:
            obs = parsed
            break

    if obs is None:
        obs = {
            "schema": SCHEMA,
            "error": "TIMED_OUT" if timed_out else "NO_OBSERVATION_RECORD",
            "test_count": 0,
            "passed": [],
            "failures": [],
            "errors": [],
            "skipped": [],
            "duration_ms": duration_ms,
        }

    full_record = {
        "schema": SCHEMA,
        "environment": env,
        "test_results": obs,
        "parent_duration_ms": duration_ms,
        "timed_out": timed_out,
    }

    out_file = out_dir / "observations.json"
    try:
        out_file.write_text(
            json.dumps(full_record, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        pass

    print(json.dumps(full_record, sort_keys=True, separators=(",", ":")), flush=True)
    os._exit(0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="/candidate", type=Path)
    parser.add_argument("--out", default="/out", type=Path)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--child-timeout", default=DEFAULT_CHILD_TIMEOUT_S, type=float)
    args = parser.parse_args()

    if args.child:
        child_main(args.candidate)
    else:
        parent_main(args.candidate, args.out, args.child_timeout)


if __name__ == "__main__":
    main()
