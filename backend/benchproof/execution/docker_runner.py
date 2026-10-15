"""Local Docker runner — isolated development alternate to Nebius Sandboxes.

Controls enforced per run (all recorded in ExecutionResult.isolation):
  --network none           no egress; launcher probes confirm denial
  --read-only + tmpfs      immutable root, scratch only in /tmp
  --memory/--pids/--cpus   resource caps
  --cap-drop ALL, no-new-privileges, non-root user
  snapshot and launcher mounted read-only; only /out is writable
  wall-clock timeout -> docker kill, container removed (--rm)

This is a tested local alternate, not the hosted sandbox story (DECISIONS D-024).
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from benchproof.execution.base import (
    LAUNCHER_DIR,
    ExecutionResult,
    RunnerUnavailable,
    Snapshot,
)

DEFAULT_IMAGE = "benchproof-candidate:dev"
LAUNCHER_FILE = "observe_invoice.py"
MAX_CAPTURE_BYTES = 64 * 1024
MAX_OBSERVATION_BYTES = 256 * 1024
MAX_ARTIFACT_FILES = 16
MAX_ARTIFACT_TOTAL_BYTES = 512 * 1024


def _drain_bounded(stream: Any, captured: bytearray, seen: list[int]) -> None:
    """Drain a pipe without allowing candidate output to grow host memory."""
    while True:
        chunk = stream.read(8192)
        if not chunk:
            return
        seen[0] += len(chunk)
        remaining = MAX_CAPTURE_BYTES - len(captured)
        if remaining > 0:
            captured.extend(chunk[:remaining])


def _captured_text(data: bytearray, seen: int) -> str:
    text = bytes(data).decode("utf-8", errors="replace")
    if seen > len(data):
        text += f"\n[output truncated: retained {len(data)} of {seen} bytes]"
    return text


OBSERVATION_SCHEMA = "benchproof/observations-v1"


def _last_record(stdout: str) -> dict[str, Any] | None:
    """The launcher parent prints the observation record as its final stdout line."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict) and parsed.get("schema") == OBSERVATION_SCHEMA:
            return parsed
    return None


def reconcile_records(
    file_record: dict[str, Any] | None, stdout_record: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, str | None]:
    """Accept observations only when the launcher's stdout record equals the file it wrote.

    Candidate code runs in the launcher's child process and shares the writable
    `/out` mount, so the file alone could be rewritten after the fact. The
    parent's final stdout line is written after the child has exited; any
    difference means the file was altered and nothing is accepted.
    """
    if file_record is None:
        return None, None
    if stdout_record is None:
        return None, "launcher stdout carried no final observation record; the file alone is not trusted"
    if stdout_record != file_record:
        return None, "observation record on stdout differs from /out/observations.json (tampering suspected)"
    return file_record, None


class DockerRunner:
    name = "docker-local"

    def __init__(self, image: str = DEFAULT_IMAGE, docker_bin: str = "docker") -> None:
        self.image = image
        self.docker = docker_bin
        self._containers: dict[str, str] = {}

    # ── availability / provenance ───────────────────────────────────────

    def available(self) -> tuple[bool, str]:
        if shutil.which(self.docker) is None:
            return False, "docker CLI not found"
        try:
            info = subprocess.run(
                [self.docker, "info", "--format", "{{.ServerVersion}} {{.OSType}}"],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "docker daemon probe timed out after 30s"
        if info.returncode != 0:
            return False, "docker daemon not running"
        try:
            img = subprocess.run(
                [self.docker, "image", "inspect", self.image, "--format", "{{.Id}}"],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "docker image probe timed out after 30s"
        if img.returncode != 0:
            return False, f"image {self.image} not built (see backend/runner/image/Dockerfile)"
        return True, f"daemon {info.stdout.strip()}; image {img.stdout.strip()}"

    def image_ref(self) -> str:
        r = subprocess.run(
            [self.docker, "image", "inspect", self.image, "--format", "{{.Id}}"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return f"{self.image}@{r.stdout.strip()}" if r.returncode == 0 else self.image

    # ── execution ────────────────────────────────────────────────────────

    def run_observation(
        self,
        snapshot: Snapshot,
        timeout_s: int = 60,
        launcher_args: list[str] | None = None,
        **_: Any,
    ) -> ExecutionResult:
        ok, why = self.available()
        if not ok:
            raise RunnerUnavailable(why)
        if not (LAUNCHER_DIR / LAUNCHER_FILE).exists():
            raise RunnerUnavailable(f"launcher missing: {LAUNCHER_DIR / LAUNCHER_FILE}")

        name = f"bp-{snapshot.run_id}-{uuid.uuid4().hex[:6]}"
        self._containers[snapshot.run_id] = name
        isolation = {
            "network": "none",
            "read_only_root": True,
            "tmpfs": "/tmp:64m",
            "memory": "256m",
            "pids_limit": 64,
            "cpus": "1",
            "cap_drop": "ALL",
            "no_new_privileges": True,
            "user": "65534:65534",
            "mounts": {"/candidate": "ro", "/launcher": "ro", "/out": "rw"},
            "env_cleared": True,
            "timeout_s": timeout_s,
            "enforced": True,
        }
        cmd = [
            self.docker, "run", "--rm", "--name", name,
            "--network", "none",
            "--read-only", "--tmpfs", "/tmp:rw,size=64m",
            "--memory", "256m", "--memory-swap", "256m",
            "--pids-limit", "64", "--cpus", "1",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--user", "65534:65534",
            "-v", f"{snapshot.candidate_dir}:/candidate:ro",
            "-v", f"{LAUNCHER_DIR}:/launcher:ro",
            "-v", f"{snapshot.out_dir}:/out",
            self.image,
            # env -i: drop every inherited variable (the python base image exports GPG_KEY)
            "env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE=1",
            "python", f"/launcher/{LAUNCHER_FILE}", *(launcher_args or []),
        ]
        started = time.perf_counter()
        timed_out = False
        exit_code: int | None = None
        stdout = stderr = ""
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout_bytes = bytearray()
            stderr_bytes = bytearray()
            stdout_seen = [0]
            stderr_seen = [0]
            readers = [
                threading.Thread(
                    target=_drain_bounded,
                    args=(proc.stdout, stdout_bytes, stdout_seen),
                    daemon=True,
                ),
                threading.Thread(
                    target=_drain_bounded,
                    args=(proc.stderr, stderr_bytes, stderr_seen),
                    daemon=True,
                ),
            ]
            for reader in readers:
                reader.start()
            try:
                exit_code = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                self.cancel(snapshot.run_id)
                proc.kill()
                proc.wait(timeout=5)
            finally:
                for reader in readers:
                    reader.join(timeout=5)
            stdout = _captured_text(stdout_bytes, stdout_seen[0])
            stderr = _captured_text(stderr_bytes, stderr_seen[0])
        except OSError as exc:
            raise RunnerUnavailable(f"docker execution failed: {type(exc).__name__}") from exc
        finally:
            self._containers.pop(snapshot.run_id, None)
        duration_ms = int((time.perf_counter() - started) * 1000)

        observations: dict[str, Any] | None = None
        error: str | None = None
        obs_file = snapshot.out_dir / "observations.json"
        if obs_file.exists():
            info = obs_file.lstat()
            if obs_file.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size > MAX_OBSERVATION_BYTES:
                error = "observations.json is linked, not a regular file, or exceeds the output size limit"
            else:
                try:
                    parsed = json.loads(obs_file.read_text(encoding="utf-8"))
                    if not isinstance(parsed, dict) or parsed.get("schema") != OBSERVATION_SCHEMA:
                        error = "observations.json has an unapproved schema"
                    else:
                        observations, error = reconcile_records(parsed, _last_record(stdout))
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    error = f"observations.json malformed: {type(e).__name__}"
        elif not timed_out:
            error = "launcher produced no observations.json"
        if timed_out:
            observations = None
            error = f"timed out after {timeout_s}s; container killed"

        artifacts = self.collect_artifacts(snapshot)
        artifact_bytes = sum(path.stat().st_size for path in artifacts)
        if len(artifacts) > MAX_ARTIFACT_FILES or artifact_bytes > MAX_ARTIFACT_TOTAL_BYTES:
            observations = None
            error = (
                "runner artifacts exceed limits: "
                f"files={len(artifacts)}/{MAX_ARTIFACT_FILES}, "
                f"bytes={artifact_bytes}/{MAX_ARTIFACT_TOTAL_BYTES}"
            )

        return ExecutionResult(
            runner=self.name,
            run_id=snapshot.run_id,
            exit_code=exit_code,
            timed_out=timed_out,
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
            observations=observations,
            image_ref=self.image_ref(),
            operation_id=name,
            isolation=isolation,
            artifacts=[p.name for p in artifacts[:MAX_ARTIFACT_FILES]],
            error=error,
        )

    def cancel(self, run_id: str) -> bool:
        name = self._containers.get(run_id)
        if not name:
            return False
        r = subprocess.run([self.docker, "kill", name], capture_output=True, text=True, timeout=30, check=False)
        return r.returncode == 0

    def container_running(self, run_id: str) -> bool:
        name = self._containers.get(run_id)
        if not name:
            return False
        r = subprocess.run(
            [self.docker, "ps", "-q", "--filter", f"name=^{name}$"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return bool(r.stdout.strip())

    def collect_artifacts(self, snapshot: Snapshot) -> list[Path]:
        return sorted(
            p for p in snapshot.out_dir.rglob("*")
            if p.is_file() and not p.is_symlink()
        )
