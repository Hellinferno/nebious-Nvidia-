"""Runner preflight (B-05): isolated execution evidence and the Sandboxes access check.

1. Nebius Sandboxes (Contree): report SDK versions and the account's actual
   permissions from GET /whoami. No execution is attempted without `spawn`.
2. Local Docker runner: fresh snapshot per run, launcher mounted read-only,
   network none. Runs clean-service and MC-01, judges them OUTSIDE the
   container, runs a timeout negative, and records isolation findings.

Writes artifacts/runner/runner_<timestamp>.json (sanitized; no credentials).
Exit 0 when the Docker route produced judged evidence; 1 otherwise.

Usage: python scripts/runner_preflight.py [--skip-contree] [--timeout 60]
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from dotenv import load_dotenv

from benchproof.evaluator.harness import judge
from benchproof.evaluator.observations import isolation_findings
from benchproof.execution.base import RunnerUnavailable, prepare_snapshot
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import fixture_dir, load_expected

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "runner"
SANDBOX_BASE = "https://api.tokenfactory.nebius.com/sandboxes/v1"


def contree_status() -> dict:
    out: dict = {"route": "nebius-sandboxes", "status": "BLOCKED"}
    for pkg in ("contree-sdk", "contree-client", "contree-cli"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            out[pkg] = None
    key = os.getenv("NEBIUS_API_KEY", "")
    if not key or key == "your_api_key_here":
        out["blocker"] = "no credential"
        return out
    try:
        r = httpx.get(
            f"{SANDBOX_BASE}/whoami",
            headers={"Authorization": f"Bearer {key}", "Project": os.getenv("CONTREE_PROJECT", "unset")},
            timeout=20,
        )
    except httpx.HTTPError as e:
        out["blocker"] = f"whoami request failed: {type(e).__name__}"
        return out
    out["whoami_status"] = r.status_code
    if r.status_code != 200:
        out["blocker"] = r.text.replace(key, "<KEY>")[:200]
        return out
    body = r.json()
    perms = body.get("permissions") or {}
    exp = body.get("token_expiration")
    out["permissions"] = perms
    out["token_expiration"] = (
        datetime.fromtimestamp(exp, UTC).isoformat() if isinstance(exp, int | float) else None
    )
    out["limits"] = body.get("limits")
    if perms.get("spawn") or perms.get("spawn_disposable"):
        out["status"] = "ACCESS_GRANTED_UNTESTED"
    else:
        out["blocker"] = "token authenticates but has no spawn/list permission (beta access not granted)"
    return out


def docker_route(timeout_s: int) -> dict:
    out: dict = {"route": "docker-local", "status": "BLOCKED", "runs": []}
    runner = DockerRunner()
    ok, why = runner.available()
    out["available"] = ok
    out["detail"] = why
    if not ok:
        out["blocker"] = why
        return out
    out["image_ref"] = runner.image_ref()

    for fid in ("clean-service", "MC-01"):
        snap = prepare_snapshot(fixture_dir(fid) / "app")
        try:
            res = runner.run_observation(snap, timeout_s=timeout_s)
            verdict = judge(res.observations, snap.app_dir)
            expected = load_expected(fid)
            run = {
                "fixture_id": fid,
                "run_id": snap.run_id,
                "snapshot_source_hash": snap.source_hash,
                "execution": res.to_record(),
                "isolation_findings": isolation_findings(res.observations),
                "verdict": verdict["verdict"],
                "failing_checks": verdict["failing_checks"],
                "unknown_checks": verdict["unknown_checks"],
                "expected_verdict": expected["expected_verdict"],
                "matches_expected": verdict["verdict"] == expected["expected_verdict"]
                and set(expected["intended_failing_checks"]).issubset(verdict["failing_checks"]),
                "checks": verdict["checks"],
            }
        except RunnerUnavailable as e:
            run = {"fixture_id": fid, "error": str(e)}
        finally:
            snap.cleanup()
        out["runs"].append(run)
        print(f"docker {fid:14} verdict={run.get('verdict')} failing={run.get('failing_checks')} "
              f"exit={run.get('execution', {}).get('exit_code')} {run.get('execution', {}).get('duration_ms')}ms")

    # Timeout negative: launcher stalls longer than the budget; container must be killed.
    snap = prepare_snapshot(fixture_dir("clean-service") / "app")
    try:
        res = runner.run_observation(snap, timeout_s=5, launcher_args=["--sleep", "30"])
        still_running = runner.container_running(snap.run_id)
        out["timeout_negative"] = {
            "timed_out": res.timed_out,
            "observations_present": res.observations is not None,
            "container_still_running": still_running,
            "duration_ms": res.duration_ms,
            "ok": res.timed_out and res.observations is None and not still_running,
        }
    finally:
        snap.cleanup()
    print(f"docker timeout negative: {out['timeout_negative']}")

    judged = [r for r in out["runs"] if "verdict" in r]
    iso = [r["isolation_findings"] for r in judged]
    out["isolation_summary"] = {
        "internet_denied_all": all(i.get("internet_denied") is True for i in iso) if iso else None,
        "metadata_denied_all": all(i.get("metadata_denied") is True for i in iso) if iso else None,
        "no_secret_env_all": all(not i.get("secret_env_names") for i in iso) if iso else None,
        "no_trusted_assets_all": all(not i.get("trusted_assets_present") for i in iso) if iso else None,
        "candidate_read_only_all": all(i.get("candidate_writable") is False for i in iso) if iso else None,
        "enforcement_gaps": [
            "host kernel shared (container, not VM); no seccomp profile beyond Docker default",
            "no disk-write quota beyond tmpfs size",
        ],
    }
    all_match = bool(judged) and all(r["matches_expected"] for r in judged)
    out["status"] = "OK" if all_match and out["timeout_negative"]["ok"] else "PARTIAL"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-contree", action="store_true")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()
    load_dotenv(REPO_ROOT / ".env")

    record: dict = {
        "schema_version": "benchproof/v2",
        "kind": "runner_preflight",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if not args.skip_contree:
        record["contree"] = contree_status()
        print(f"sandboxes: {record['contree'].get('status')} — {record['contree'].get('blocker', '')}")
    record["docker"] = docker_route(args.timeout)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = record["timestamp"].replace(":", "").replace("-", "")[:15]
    path = ARTIFACT_DIR / f"runner_{ts}.json"
    path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    print(f"Saved {path.relative_to(REPO_ROOT)}")
    return 0 if record["docker"]["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
