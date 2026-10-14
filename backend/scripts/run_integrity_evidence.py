"""Generate versioned B-17 trust-boundary evidence without exposing secrets."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from benchproof.bundle.exporter import SecurityExclusionError, scan_for_secrets
from benchproof.evaluator import run_gate
from benchproof.evaluator.harness import collect_observations_in_process, required_check_ids
from benchproof.evaluator.observations import evaluate_observations, isolation_findings
from benchproof.execution import prepare_snapshot
from benchproof.execution.docker_runner import (
    MAX_ARTIFACT_FILES,
    MAX_ARTIFACT_TOTAL_BYTES,
    MAX_CAPTURE_BYTES,
    MAX_OBSERVATION_BYTES,
    DockerRunner,
)
from benchproof.fixtures import fixture_dir


def _exclusion_check(value: str) -> bool:
    try:
        scan_for_secrets(value, "integrity-probe.txt")
    except SecurityExclusionError:
        return True
    return False


def build_evidence() -> dict[str, object]:
    clean = fixture_dir("clean-service") / "app"
    faulty = fixture_dir("MC-01") / "app"

    forged = collect_observations_in_process(faulty)
    forged["verdict"] = "VERIFIED"
    forged["checks"] = [{"check_id": "amount-boundary", "outcome": "PASS"}]
    forged_results = evaluate_observations(forged, (faulty / "worker.py").read_text(encoding="utf-8"))
    forged_verdict = run_gate(forged_results, required_check_ids())

    missing_results = evaluate_observations(None, None)
    missing_verdict = run_gate(missing_results, required_check_ids())

    docker = DockerRunner()
    docker_available, docker_detail = docker.available()
    runtime: dict[str, object] = {
        "status": "BLOCKED",
        "reason": docker_detail,
        "public_capabilities": ["verification", "mutation assessment", "bundle replay"],
    }
    if docker_available:
        snapshot = prepare_snapshot(clean)
        try:
            execution = docker.run_observation(snapshot, timeout_s=90)
            findings = isolation_findings(execution.observations)
            passed = (
                not execution.timed_out
                and execution.error is None
                and findings["internet_denied"] is True
                and findings["metadata_denied"] is True
                and findings["secret_env_names"] == []
                and findings["trusted_assets_present"] == []
                and findings["candidate_writable"] is False
            )
            runtime = {
                "status": "PASS" if passed else "FAIL_BLOCKED",
                "runner": execution.runner,
                "image_ref": execution.image_ref,
                "isolation": execution.isolation,
                "findings": findings,
                "error": execution.error,
            }
        finally:
            snapshot.cleanup()

    return {
        "schema_version": "benchproof/integrity-report-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "B-17 runtime trust-boundary development evidence",
        "controls": {
            "forged_pass": {
                "status": "PASS" if forged_verdict == "REJECTED" else "FAIL_BLOCKED",
                "authoritative_verdict": forged_verdict,
            },
            "missing_output": {
                "status": "PASS" if missing_verdict == "INCONCLUSIVE" else "FAIL_BLOCKED",
                "authoritative_verdict": missing_verdict,
            },
            "secret_exclusion": {
                "status": "PASS" if _exclusion_check("NEBIUS_API_KEY=abcdefghijklmnop1234") else "FAIL_BLOCKED",
            },
            "hidden_truth_exclusion": {
                "status": "PASS" if _exclusion_check("../reference/repair.py") else "FAIL_BLOCKED",
            },
            "runtime_isolation": runtime,
        },
        "resource_caps": {
            "stdout_or_stderr_retained_bytes_each": MAX_CAPTURE_BYTES,
            "observation_bytes": MAX_OBSERVATION_BYTES,
            "artifact_files": MAX_ARTIFACT_FILES,
            "artifact_total_bytes": MAX_ARTIFACT_TOTAL_BYTES,
            "docker_memory": "256m",
            "docker_pids": 64,
            "docker_cpus": 1,
            "docker_tmpfs": "64m",
        },
        "limitations": [
            "The owner header is an opaque local/demo capability, not production authentication.",
            "In-process evaluation remains an explicit development library harness and is not reachable from public verify or replay endpoints.",
            "Hosted Nebius sandbox execution remains unavailable; no hosted isolation claim is made.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "integrity" / "day13_integrity.json",
    )
    args = parser.parse_args()
    evidence = build_evidence()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "controls": evidence["controls"]}, sort_keys=True))
    required = [
        item["status"]
        for name, item in evidence["controls"].items()
        if name != "runtime_isolation"
    ]
    return 0 if all(status == "PASS" for status in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
