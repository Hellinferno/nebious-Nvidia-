"""Protected launcher: observes a candidate invoice service from inside its runtime.

Runs INSIDE the candidate container (or in-process for development). It is
mounted read-only from outside the candidate's editable tree and depends only
on the standard library plus the packages the candidate itself needs.

It records observations only. It never decides PASS/FAIL: expected values are
computed by the trusted evaluator outside the candidate runtime. Everything
printed here is treated as untrusted data by that evaluator.

Usage: python observe_invoice.py [--candidate DIR] [--out DIR] [--sleep SECONDS]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA = "benchproof/observations-v1"
BOUNDARY_LINES = ["0.005", "0.005"]
CONFLICT_LINES = ["1.00", "2.00"]
SECRET_PATTERN = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|NEBIUS|CONTREE)", re.IGNORECASE)
TRUSTED_NAMES = {"expected.json", "reference"}


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
    }


def observe(candidate: Path) -> dict[str, Any]:
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

        try:
            worker.handle_invoice_job("t2", "r2", BOUNDARY_LINES)
            obs["worker"]["stored_receipt"] = repository.get_receipt("t2", "r2")
            obs["worker"]["error"] = None
        except Exception as e:  # noqa: BLE001 — candidate failure is data
            obs["worker"]["stored_receipt"] = None
            obs["worker"]["error"] = f"{type(e).__name__}: {e}"[:200]
    except Exception as e:  # noqa: BLE001 — candidate import/crash is data
        obs["error"] = f"{type(e).__name__}: {e}"[:300]
    return obs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="/candidate")
    ap.add_argument("--out", default="/out")
    ap.add_argument("--sleep", type=float, default=0.0, help="test hook: stall before observing")
    args = ap.parse_args()
    if args.sleep:
        time.sleep(args.sleep)
    candidate = Path(args.candidate)
    obs = observe(candidate)
    obs["environment"] = environment(candidate)
    out = Path(args.out)
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "observations.json").write_text(json.dumps(obs, indent=2, default=str), encoding="utf-8")
    except OSError as e:
        obs["write_error"] = str(e)
    print(json.dumps(obs, default=str))
    return 0 if obs.get("error") is None else 2


if __name__ == "__main__":
    sys.exit(main())
