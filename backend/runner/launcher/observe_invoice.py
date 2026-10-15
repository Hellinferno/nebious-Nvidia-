"""Protected launcher: observes a candidate invoice service from inside its runtime.

Runs INSIDE the candidate container (or in-process for development). It is
mounted read-only from outside the candidate's editable tree and depends only
on the standard library plus the packages the candidate itself needs.

Two processes, one trust direction:

* The **parent** never imports candidate code. It spawns the child, takes the
  child's final JSON line as the untrusted observation record, adds its own
  environment probes, writes `/out/observations.json`, prints the same record
  as its last stdout line and exits with `os._exit` (no atexit hooks run).
* The **child** imports the candidate, performs the fixed observations, prints
  one JSON line and exits immediately with `os._exit`, so candidate atexit
  handlers cannot append or rewrite output.

The host compares the parent's stdout record with the file. A candidate that
rewrites the file after the fact (or leaves a process behind to do so) produces
a mismatch and no observation is accepted. Everything in the record is still
untrusted data: expected values are computed by the trusted evaluator outside
the candidate runtime, and nothing here decides PASS or FAIL.

Usage: python observe_invoice.py [--candidate DIR] [--out DIR] [--sleep SECONDS]
                                 [--child-timeout SECONDS]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA = "benchproof/observations-v1"
BOUNDARY_LINES = ["0.005", "0.005"]
CONFLICT_LINES = ["1.00", "2.00"]
SECRET_PATTERN = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|NEBIUS|CONTREE)", re.IGNORECASE)
TRUSTED_NAMES = {"expected.json", "reference"}
MAX_CHILD_OUTPUT = 256 * 1024
DEFAULT_CHILD_TIMEOUT_S = 20.0


def probe(host: str, port: int) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=2):
            return {"denied": False, "detail": "connected"}
    except OSError as e:
        return {"denied": True, "detail": f"{type(e).__name__}: {e}"[:120]}


def environment(candidate: Path) -> dict[str, Any]:
    files = sorted(str(p.relative_to(candidate)).replace("\\", "/") for p in candidate.rglob("*") if p.is_file())
    return {
        "secret_env_names": sorted(k for k in os.environ if SECRET_PATTERN.search(k)),
        "candidate_files": files,
        "trusted_assets_present": sorted(f for f in files if any(part in TRUSTED_NAMES for part in f.split("/"))),
        "network": {"internet": probe("1.1.1.1", 443), "metadata": probe("169.254.169.254", 80)},
        "cwd_writable": os.access(os.getcwd(), os.W_OK),
        "candidate_writable": os.access(str(candidate), os.W_OK),
        "python": sys.version.split()[0],
        "launcher_isolation": "child-process",
    }


def observe(candidate: Path) -> dict[str, Any]:
    """Child side: import the candidate and record the fixed route and worker observations."""
    obs: dict[str, Any] = {
        "schema": SCHEMA,
        "inputs": {
            "tenant": "t1", "request": "r1", "boundary_lines": BOUNDARY_LINES,
            "conflict_lines": CONFLICT_LINES, "worker_tenant": "t2", "worker_request": "r2",
        },
        "route": {}, "worker": {}, "error": None,
    }
    sys.path.insert(0, str(candidate))
    try:
        from app import repository, routes, worker  # type: ignore[import-not-found]
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        api = FastAPI()
        api.include_router(routes.router)
        client = TestClient(api)

        def call(lines: list[str]) -> dict[str, Any]:
            r = client.post("/invoices", json={"tenant_id": "t1", "request_id": "r1", "line_amounts": lines})
            body: Any = None
            if r.headers.get("content-type", "").startswith("application/json"):
                try:
                    body = r.json()
                except ValueError:
                    body = None
            return {"status": r.status_code, "body": body if isinstance(body, dict) else None}

        obs["route"]["first"] = call(BOUNDARY_LINES)
        obs["route"]["second"] = call(BOUNDARY_LINES)
        obs["route"]["conflict"] = call(CONFLICT_LINES)

        def worker_job(lines: list[str]) -> dict[str, Any]:
            try:
                worker.handle_invoice_job("t2", "r2", lines)
                return {"stored_receipt": copy.deepcopy(repository.get_receipt("t2", "r2")), "error": None}
            except Exception as e:  # noqa: BLE001 — candidate failure is data
                return {"stored_receipt": None, "error": f"{type(e).__name__}: {e}"[:200]}

        obs["worker"] = worker_job(BOUNDARY_LINES)
        obs["worker"]["repeat"] = worker_job(BOUNDARY_LINES)
        obs["worker"]["conflict"] = worker_job(CONFLICT_LINES)
    except Exception as e:  # noqa: BLE001 — candidate import/crash is data
        obs["error"] = f"{type(e).__name__}: {e}"[:300]
    return obs


def _emit_and_exit(record: dict[str, Any], code: int) -> None:
    sys.stdout.write(json.dumps(record, default=str) + "\n")
    sys.stdout.flush()
    os._exit(code)


def run_child(candidate: Path) -> None:
    obs = observe(candidate)
    _emit_and_exit(obs, 0 if obs.get("error") is None else 2)


def _last_record(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict) and parsed.get("schema") == SCHEMA:
            return parsed
    return None


def child_environment() -> dict[str, str]:
    """Minimal environment for the candidate child: no inherited secrets or configuration.

    On Windows (development runs only; the container is Linux) CPython cannot start
    without SYSTEMROOT, so that one system variable is passed through there.
    """
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
    if os.name == "nt":
        for name in ("SYSTEMROOT", "TEMP", "TMP"):
            if os.environ.get(name):
                env[name] = os.environ[name]
    return env


def run_parent(candidate: Path, out: Path, child_timeout_s: float) -> None:
    record: dict[str, Any] = {"schema": SCHEMA, "route": {}, "worker": {}, "error": None}
    child = {"exit_code": None, "timed_out": False, "stderr_tail": ""}
    cmd = [sys.executable, "-I", os.path.abspath(__file__), "--child", "--candidate", str(candidate)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=child_timeout_s, check=False, env=child_environment(),
        )
        child["exit_code"] = proc.returncode
        child["stderr_tail"] = proc.stderr[-2000:].decode("utf-8", errors="replace")
        stdout = proc.stdout[-MAX_CHILD_OUTPUT:].decode("utf-8", errors="replace")
        observed = _last_record(stdout)
        if observed is None:
            record["error"] = "candidate child produced no valid observation record"
        else:
            record.update({key: observed.get(key) for key in ("inputs", "route", "worker", "error")})
            if record["error"] is None and not isinstance(record.get("route"), dict):
                record["error"] = "candidate child returned a malformed route record"
    except subprocess.TimeoutExpired as exc:
        child["timed_out"] = True
        child["stderr_tail"] = (exc.stderr or b"")[-2000:].decode("utf-8", errors="replace")
        record["error"] = f"candidate observation timed out after {child_timeout_s:g}s"
    except OSError as exc:
        record["error"] = f"could not start the candidate child process: {type(exc).__name__}"
    record["child"] = child
    record["environment"] = environment(candidate)
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "observations.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    except OSError as e:
        record["write_error"] = str(e)
    _emit_and_exit(record, 0 if record.get("error") is None else 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="/candidate")
    ap.add_argument("--out", default="/out")
    ap.add_argument("--sleep", type=float, default=0.0, help="test hook: stall before observing")
    ap.add_argument("--child-timeout", type=float, default=DEFAULT_CHILD_TIMEOUT_S)
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    candidate = Path(args.candidate)
    if args.child:
        run_child(candidate)
        return 0  # unreachable: run_child exits the process
    if args.sleep:
        time.sleep(args.sleep)
    run_parent(candidate, Path(args.out), args.child_timeout)
    return 0  # unreachable: run_parent exits the process


if __name__ == "__main__":
    sys.exit(main())
