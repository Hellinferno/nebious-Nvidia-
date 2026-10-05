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
import subprocess
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
        info = subprocess.run(
            [self.docker, "info", "--format", "{{.ServerVersion}} {{.OSType}}"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if info.returncode != 0:
            return False, "docker daemon not running"
        img = subprocess.run(
            [self.docker, "image", "inspect", self.image, "--format", "{{.Id}}"],
            capture_output=True, text=True, timeout=30, check=False,
        )
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
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
            exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            stdout = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            self.cancel(snapshot.run_id)
        duration_ms = int((time.perf_counter() - started) * 1000)

        observations: dict[str, Any] | None = None
        error: str | None = None
        obs_file = snapshot.out_dir / "observations.json"
        if obs_file.exists():
            try:
                observations = json.loads(obs_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                error = f"observations.json malformed: {e.msg}"
        elif not timed_out:
            error = "launcher produced no observations.json"
        if timed_out:
            error = f"timed out after {timeout_s}s; container killed"

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
            artifacts=[p.name for p in self.collect_artifacts(snapshot)],
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
        return sorted(p for p in snapshot.out_dir.rglob("*") if p.is_file())
