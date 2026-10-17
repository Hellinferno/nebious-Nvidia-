"""Opt-in, single-call coding acceptance check on the public MC-01 sample."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from benchproof.coding.generation import (
    CodingBrief,
    CodingPlan,
    EditProposal,
    GenerationError,
    generate_edits,
)
from benchproof.evaluator.harness import judge
from benchproof.execution import prepare_snapshot
from benchproof.execution.base import RunnerUnavailable
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.patch import PatchValidationError, apply_patch_to_dir
from benchproof.providers import NebiusAdapter, ProviderError
from benchproof.providers.structured import ModelOutputError, validate_completion

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_new(path: Path, payload: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def reproduce_retained_truncation() -> list[dict[str, Any]]:
    path = REPO_ROOT / "artifacts/trials/dev-live-release-20261016-1/records/B2-AC-01-t1.json"
    if not path.is_file():
        return [{"status": "NOT_AVAILABLE", "reason": "Retained local development record is absent"}]
    original = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for step in original["steps"]:
        if step.get("finish_reason") != "length":
            continue
        try:
            validate_completion({"content": step["response"], "finish_reason": "length"}, EditProposal)
        except ModelOutputError as exc:
            results.append({
                "source_record": str(path.relative_to(REPO_ROOT)),
                "step_index": step["index"], "code": exc.code,
                "response_id": step.get("response_id"), "usage": step.get("usage"),
            })
    return results


def _observe(app_dir: Path, runner: DockerRunner) -> dict[str, Any]:
    snapshot = prepare_snapshot(app_dir)
    try:
        result = runner.run_observation(snapshot, timeout_s=30)
    finally:
        snapshot.cleanup()
    judgment = judge(result.observations, app_dir)
    return {
        "verdict": judgment["verdict"], "failing_checks": judgment["failing_checks"],
        "unknown_checks": judgment["unknown_checks"], "source_hash": source_hash_for_dir(app_dir),
        "execution": result.to_record(),
    }


class RecordingClient:
    def __init__(self, adapter: Any, output: Path) -> None:
        self.adapter = adapter
        self.output = output
        self.calls = 0

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        if self.calls:
            raise GenerationError("BUDGET_EXHAUSTED", "Only one model call is permitted")
        _write_new(self.output / "call-reservation.json", {
            "status": "IN_FLIGHT", "usage_status": "UNKNOWN",
            "created_at": datetime.now(UTC).isoformat(), "model": kwargs["model"],
            "max_output_tokens": kwargs["max_tokens"], "max_calls": 1, "automatic_retries": 0,
        })
        self.calls += 1
        response = self.adapter.complete(**kwargs)
        _write_new(self.output / "provider-response.json", {
            key: response.get(key) for key in (
                "content", "finish_reason", "response_id", "response_model", "usage", "elapsed_ms",
            )
        })
        return response


def run_live_check(output: Path, adapter: Any, model_id: str, runner: DockerRunner | None = None) -> dict[str, Any]:
    app_dir = fixture_dir("MC-01") / "app"
    base_hash = source_hash_for_dir(app_dir)
    brief = CodingBrief(
        task="Fix compute_total so it sums exact Decimal line amounts and rounds only the invoice total"
             " to two places with ROUND_HALF_UP. Preserve the function interface and the empty-input result.",
        source_hash=base_hash, editable_paths=["app/money.py"],
    )
    plan = CodingPlan(
        source_hash=base_hash, brief_hash=brief.identity(), target_files=["app/money.py"],
        steps=["Accumulate unrounded Decimal line amounts", "Keep final ROUND_HALF_UP quantization"],
    )
    _write_new(output / "approved-task.json", {
        "brief": brief.model_dump(), "plan": plan.model_dump(), "plan_hash": plan.identity(),
        "plan_provenance": "operator-scoped development acceptance plan; not model-generated",
    })
    report: dict[str, Any] = {
        "schema": "benchproof/coding-acceptance-v1", "fixture_id": "MC-01",
        "source_hash": base_hash, "plan_hash": plan.identity(), "model_calls": 0,
        "max_output_tokens": 2_048, "max_executions": 2, "monetary_cost": "UNKNOWN",
        "execution_status": "NOT_RUN", "measurement": False,
    }
    recording = RecordingClient(adapter, output)
    try:
        if runner:
            available, _detail = runner.available()
            if not available:
                raise GenerationError("RUNNER_UNAVAILABLE", "Docker is unavailable; no host fallback is allowed")
            report["baseline"] = _observe(app_dir, runner)
            if report["baseline"]["verdict"] != "REJECTED":
                raise GenerationError("BASELINE_UNEXPECTED", "The sample did not reproduce its baseline failure")
        patch, metadata = generate_edits(
            brief, plan, plan.identity(), app_dir, client=recording, model_id=model_id,
            max_tokens=2_048,
        )
        report.update(provider=metadata, status="GENERATED_POLICY_VALIDATED")
        with (output / "candidate.diff").open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(patch.diff)
        if runner:
            destination = (output / "candidate" / "app").resolve()
            if not destination.is_relative_to(output.resolve()) or destination.exists():
                raise GenerationError("INVALID_STATE", "Candidate destination must be fresh and inside this run")
            destination.parent.mkdir()
            candidate, candidate_hash = apply_patch_to_dir(app_dir, patch, destination)
            report["candidate_source_hash"] = candidate_hash
            report["candidate"] = _observe(candidate, runner)
            report["execution_status"] = report["candidate"]["verdict"]
            report["status"] = "PASSED" if report["candidate"]["verdict"] == "VERIFIED" else "CHECKS_FAILED"
    except GenerationError as exc:
        report.update(status="FAILED", code=exc.code, provider=exc.metadata)
    except (OSError, ValueError, RuntimeError, RunnerUnavailable, PatchValidationError) as exc:
        report.update(status="FAILED", code="ACCEPTANCE_CHECK_FAILED", error_type=type(exc).__name__)
    finally:
        report["model_calls"] = recording.calls
        report["original_source_unchanged"] = source_hash_for_dir(app_dir) == base_hash
        _write_new(output / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--live-once", action="store_true", help="Authorize exactly one paid inference attempt")
    parser.add_argument("--verify", action="store_true", help="Run baseline and generated candidate in Docker only")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id):
        parser.error("run-id must be a plain portable token")
    if args.verify and not args.live_once:
        parser.error("--verify requires --live-once")
    output = REPO_ROOT / "artifacts" / "coding" / args.run_id
    output.mkdir(parents=True, exist_ok=False)
    _write_new(output / "retained-failures.json", {
        "truncation_reproductions": reproduce_retained_truncation(),
        "original_public_422_cause": "NOT_CAPTURED; synthetic schema regressions do not establish its cause",
    })
    if not args.live_once:
        print(json.dumps({"status": "OFFLINE_REPRODUCTION", "model_calls": 0, "output": str(output)}))
        return 0
    load_dotenv(REPO_ROOT / ".env")
    model_id = os.getenv("NEBIUS_MODEL_ID", "").strip()
    if not model_id:
        print(json.dumps({"status": "BLOCKED", "code": "MODEL_NOT_CONFIGURED"}))
        return 2
    try:
        adapter = NebiusAdapter(timeout_s=45)
    except ProviderError as exc:
        print(json.dumps({"status": "BLOCKED", "error_type": type(exc).__name__}))
        return 2
    report = run_live_check(output, adapter, model_id, DockerRunner() if args.verify else None)
    print(json.dumps({key: report.get(key) for key in (
        "status", "code", "model_calls", "execution_status", "original_source_unchanged",
    )} | {"output": str(output)}))
    return 0 if report["status"] in {"PASSED", "GENERATED_POLICY_VALIDATED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
