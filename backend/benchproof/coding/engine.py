"""Bounded, source-pinned coding actions for the curated invoice profile."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from benchproof.coding.contracts import CodingStoreError
from benchproof.coding.extensions import harness_policy
from benchproof.coding.generation import (
    MAX_CONTEXT_BYTES,
    CodingBrief,
    CodingPlan,
    CompletionClient,
    GenerationError,
    generate_edits,
)
from benchproof.coding.prompts import (
    PLAN_SYSTEM_PROMPT,
    coding_runtime_identity,
    generation_policy,
)
from benchproof.constraints import contract_hash, list_constraints
from benchproof.evaluator import run_gate
from benchproof.evaluator.harness import evaluator_hash, required_check_ids
from benchproof.evaluator.observations import evaluate_observations
from benchproof.execution.base import RunnerUnavailable, prepare_snapshot
from benchproof.execution.docker_runner import DockerRunner
from benchproof.execution.project_runner import ProjectExecutor
from benchproof.fixtures import fixture_dir, load_manifest, source_hash_for_dir
from benchproof.patch import PatchProposal, apply_patch_to_dir, validate_patch
from benchproof.providers import ProviderError
from benchproof.providers.structured import (
    ModelOutputError,
    completion_metadata,
    validate_completion,
)

_SOURCE_PATH = re.compile(r"^(?:app|tests)/(?:[A-Za-z_][A-Za-z0-9_]*/)*[A-Za-z_][A-Za-z0-9_]*\.py$")


class CheckExecutor(Protocol):
    def run(
        self,
        app_dir: Path,
        *,
        operation_id: str,
        timeout_s: int,
        should_cancel: Callable[[], bool] | None = None,
    ) -> dict[str, Any]: ...

    def cancel(self, operation_id: str) -> bool: ...


class InvoiceExecutor:
    """Only an isolated Docker collector feeds the trusted invoice evaluator."""

    def __init__(self, runner: DockerRunner | None = None) -> None:
        self.runner = runner or DockerRunner()
        self._cancelled: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def run(
        self,
        app_dir: Path,
        *,
        operation_id: str,
        timeout_s: int = 30,
        should_cancel: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            cancelled = self._cancelled.setdefault(operation_id, threading.Event())
        snapshot = prepare_snapshot(app_dir)
        snapshot.run_id = operation_id
        try:
            result = self.runner.run_observation(
                snapshot,
                timeout_s=timeout_s,
                operation_id=operation_id,
                should_cancel=lambda: cancelled.is_set() or bool(should_cancel and should_cancel()),
            )
            if not result.isolation.get("enforced"):
                raise GenerationError(
                    "RUNNER_UNAVAILABLE", "The isolated runner controls were not enforced"
                )
            checks = evaluate_observations(
                result.observations, (snapshot.app_dir / "worker.py").read_text(encoding="utf-8")
            )
            source_hash = source_hash_for_dir(snapshot.app_dir)
            evaluator = evaluator_hash()
            for check in checks:
                check.source_hash = source_hash
                check.contract_hash = contract_hash()
                check.evaluator_hash = evaluator
                check.image_hash = result.image_ref or "UNKNOWN"
            required = required_check_ids()
            verdict = run_gate(checks, required)
            if result.error or result.timed_out or result.exit_code != 0:
                verdict = "INCONCLUSIVE"
            execution = result.to_record()
            observation = execution.pop("observations", None)
            execution["observation_sha256"] = hashlib.sha256(
                json.dumps(observation, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            ).hexdigest()
            return {
                "profile": "invoice-observation-v1",
                "source_hash": source_hash,
                "contract_hash": contract_hash(),
                "evaluator_hash": evaluator,
                "required_check_ids": sorted(required),
                "verdict": verdict,
                "checks": [check.model_dump(mode="json") for check in checks],
                "execution": execution,
            }
        except RunnerUnavailable as exc:
            raise GenerationError(
                "RUNNER_UNAVAILABLE", "The isolated Docker runner is unavailable"
            ) from exc
        finally:
            snapshot.cleanup()
            with self._lock:
                self._cancelled.pop(operation_id, None)

    def cancel(self, operation_id: str) -> bool:
        with self._lock:
            self._cancelled.setdefault(operation_id, threading.Event()).set()
        return self.runner.cancel_operation(operation_id)


class DispatchingExecutor:
    """Dispatches to InvoiceExecutor or ProjectExecutor based on candidate structure."""

    def __init__(self, invoice: InvoiceExecutor, project: ProjectExecutor) -> None:
        self.invoice = invoice
        self.project = project

    def run(
        self,
        app_dir: Path,
        *,
        operation_id: str,
        timeout_s: int = 30,
        should_cancel: Callable[[], bool] | None = None,
        check_profile: str | None = None,
    ) -> dict[str, Any]:
        if check_profile not in {"invoice-observation-v1", "project-unittest-v1"}:
            raise GenerationError("STALE_CHECKS", "An explicit approved check profile is required")
        if check_profile == "invoice-observation-v1":
            return self.invoice.run(
                app_dir,
                operation_id=operation_id,
                timeout_s=timeout_s,
                should_cancel=should_cancel,
            )
        return self.project.run(
            app_dir,
            operation_id=operation_id,
            timeout_s=timeout_s,
            should_cancel=should_cancel,
        )

    def cancel(self, operation_id: str) -> bool:
        c1 = self.invoice.cancel(operation_id)
        c2 = self.project.cancel(operation_id)
        return c1 and c2


@dataclass(frozen=True)
class ActionOutcome:
    result: dict[str, Any]
    checkpoint: dict[str, Any]
    next_stage: str
    state: str = "QUEUED"
    usage: dict[str, Any] | None = None


class _GuardedClient:
    def __init__(self, client: CompletionClient, guard: Callable[[], Any]) -> None:
        self.client = client
        self.guard = guard

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        current = self.guard()
        remaining = int(current["limits"]["active_seconds"] - current["counters"]["active_seconds"])
        if remaining < 1:
            raise GenerationError("BUDGET_EXHAUSTED", "The active-time allowance is exhausted")
        kwargs["timeout_s"] = min(30, remaining)
        return self.client.complete(**kwargs)


def _files_hash(source_files: dict[str, str]) -> str:
    manifest = {
        path: hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()
        for path, content in source_files.items()
    }
    return hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _write_source(root: Path, source_files: dict[str, str]) -> Path:
    for path, content in source_files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    return root / "app"


def _feedback(report: dict[str, Any]) -> dict[str, Any]:
    execution = report.get("execution") or {}
    return {
        "source_hash": report.get("source_hash"),
        "verdict": report.get("verdict"),
        "checks": [
            {"check_id": check.get("check_id"),
             "outcome": check.get("outcome") or check.get("status"),
             "reason": check.get("reason") or check.get("detail")}
            for check in report.get("checks", [])
        ],
        "execution": {key: execution.get(key) for key in ("exit_code", "timed_out", "error")},
    }


class CodingEngine:
    def __init__(
        self,
        *,
        client: CompletionClient,
        model_id: str,
        executor: CheckExecutor,
        max_output_tokens: int = 2_048,
        synthetic: bool = False,
    ) -> None:
        if not model_id.strip() or not 256 <= max_output_tokens <= 4_096:
            raise ValueError("A model and bounded output allowance are required")
        self.client = client
        self.model_id = model_id
        self.executor = executor
        self.max_output_tokens = max_output_tokens
        self.synthetic = synthetic

    def validate(self, task: dict[str, Any]) -> CodingBrief:
        if not self.synthetic and task.get("runtime_config") != coding_runtime_identity(
            self.model_id, self.max_output_tokens,
        ):
            raise GenerationError(
                "STALE_RUNTIME",
                "The task must be reviewed against the current model, output limits and generation policy",
            )
        brief = CodingBrief.model_validate(task["brief"])
        if brief.preferences is not None and brief.preferences.mode == "plan_only" and task["next_stage"] != "PLAN":
            raise GenerationError(
                "PLAN_ONLY", "This task allows planning only; edits and test execution are disabled",
            )
        files = task["source_files"]
        if not isinstance(files, dict) or not files or len(files) > 20:
            raise GenerationError("SOURCE_LIMIT", "The curated source snapshot is invalid")
        if any(
            not isinstance(path, str)
            or not _SOURCE_PATH.fullmatch(path)
            or not isinstance(content, str)
            for path, content in files.items()
        ):
            raise GenerationError(
                "UNSUPPORTED_SOURCE", "The snapshot contains an unsupported source path or value"
            )
        if len({path.casefold() for path in files}) != len(files):
            raise GenerationError(
                "UNSUPPORTED_SOURCE", "The snapshot contains case-colliding source paths"
            )
        if (
            any(
                "\x00" in content or len(content.encode("utf-8")) > 24_576
                for content in files.values()
            )
            or sum(len(content.encode("utf-8")) for content in files.values()) > 131_072
        ):
            raise GenerationError("SOURCE_LIMIT", "The curated source snapshot exceeds its limits")
        if not set(brief.editable_paths) <= set(files) or _files_hash(files) != brief.source_hash:
            raise GenerationError(
                "STALE_SOURCE", "The task source snapshot no longer matches its brief"
            )
        is_project = task["fixture_id"].startswith("proj-")
        if not is_project:
            manifest = load_manifest(task["fixture_id"])
            if manifest.get("visibility", "development") != "development":
                raise GenerationError(
                    "UNSUPPORTED_PROFILE", "Only public development examples are supported"
                )
            if source_hash_for_dir(fixture_dir(task["fixture_id"]) / "app") != brief.source_hash:
                raise GenerationError("STALE_SOURCE", "The curated example changed after task creation")
            if task["contract_hash"] != contract_hash():
                raise GenerationError(
                    "STALE_CONTRACT", "The protected check contract changed after task creation"
                )
        if task["next_stage"] != "PLAN":
            plan = CodingPlan.model_validate(task["plan"])
            if (
                plan.identity() != task["approved_plan_hash"]
                or plan.brief_hash != brief.identity()
                or plan.source_hash != brief.source_hash
                or not set(plan.target_files) <= set(brief.editable_paths)
            ):
                raise GenerationError(
                    "PLAN_UNAPPROVED", "The approved plan no longer matches this task"
                )
        return brief

    def _metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        if self.synthetic:
            metadata.update(mode="synthetic", provider="synthetic-test-client")
        return metadata

    def _plan(
        self, task: dict[str, Any], brief: CodingBrief, client: CompletionClient
    ) -> ActionOutcome:
        is_project = task["fixture_id"].startswith("proj-")
        payload = {
            "brief": brief.model_dump(exclude={"preferences"}),
            "source_hash": brief.source_hash,
            "brief_hash": brief.identity(),
            "check_profile": "project-unittest-v1" if is_project else "invoice-observation-v1",
            "source": {path: task["source_files"][path] for path in brief.editable_paths},
            "protected_requirements": (
                ["All project unittests in tests/ must pass without modification"]
                if is_project
                else [constraint.statement for constraint in list_constraints()]
            ),
            "response_schema": CodingPlan.model_json_schema(),
        }
        if brief.preferences is not None:
            payload["preferences"] = brief.preferences.prompt_context()
        prompt = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        if len((PLAN_SYSTEM_PROMPT + prompt).encode("utf-8")) > MAX_CONTEXT_BYTES:
            raise GenerationError(
                "SOURCE_LIMIT", "The selected planning context exceeds the prompt byte limit"
            )
        metadata = self._metadata(completion_metadata({}, self.model_id))
        metadata["max_output_tokens"] = self.max_output_tokens
        metadata["generation_policy"] = generation_policy()
        try:
            response = client.complete(
                model=self.model_id,
                system_prompt=PLAN_SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=self.max_output_tokens,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
        except ProviderError as exc:
            raise GenerationError(
                exc.code, "Planning provider request failed; no retry was made", metadata
            ) from exc
        metadata.update(self._metadata(completion_metadata(response, self.model_id)))
        try:
            plan = validate_completion(response, CodingPlan)
        except ModelOutputError as exc:
            raise GenerationError(exc.code, exc.message, metadata) from exc
        self.validate(task)
        if (
            plan.source_hash != brief.source_hash
            or plan.brief_hash != brief.identity()
            or not set(plan.target_files) <= set(brief.editable_paths)
        ):
            raise GenerationError(
                "STALE_CONTEXT",
                "The plan exceeds or does not match the task's pinned scope",
                metadata,
            )
        return ActionOutcome(
            result={"plan": plan.model_dump(), "provider": metadata},
            checkpoint={},
            next_stage="BASELINE",
            state="AWAITING_APPROVAL",
            usage=metadata,
        )

    def perform(
        self,
        task: dict[str, Any],
        *,
        operation_id: str,
        before_external: Callable[[], Any] | None = None,
    ) -> ActionOutcome:
        brief = self.validate(task)
        stage = task["next_stage"]
        checkpoint = dict(task.get("checkpoint") or {})
        client = _GuardedClient(self.client, before_external) if before_external else self.client
        if stage == "PLAN":
            return self._plan(task, brief, client)
        with tempfile.TemporaryDirectory(prefix="bp-coding-") as directory:
            root = Path(directory)
            app_dir = _write_source(root / "base", task["source_files"])
            if stage == "EDIT":
                plan = CodingPlan.model_validate(task["plan"])
                feedback = {"baseline": _feedback(checkpoint["baseline"])}
                if checkpoint.get("last_candidate"):
                    feedback["previous_candidate"] = _feedback(checkpoint["last_candidate"])
                    feedback["previous_patch"] = checkpoint["patch"]["diff"]
                try:
                    patch, metadata = generate_edits(
                        brief,
                        plan,
                        task["approved_plan_hash"],
                        app_dir,
                        client=client,
                        model_id=self.model_id,
                        max_tokens=self.max_output_tokens,
                        observations=feedback,
                    )
                except GenerationError as exc:
                    self._metadata(exc.metadata)
                    raise
                self._metadata(metadata)
                if self.synthetic:
                    patch.author = "synthetic-test-coding-agent"
                _, candidate_hash = apply_patch_to_dir(app_dir, patch, root / "candidate" / "app")
                seen = checkpoint.get("candidate_hashes", [])
                checkpoint.update(patch=patch.model_dump(), candidate_hash=candidate_hash)
                if candidate_hash in seen:
                    return ActionOutcome(
                        {"code": "REPEATED_CANDIDATE", "provider": metadata},
                        checkpoint,
                        "EDIT",
                        "STALLED",
                        metadata,
                    )
                checkpoint["candidate_hashes"] = [*seen, candidate_hash]
                return ActionOutcome(
                    {
                        "patch": patch.model_dump(),
                        "candidate_hash": candidate_hash,
                        "provider": metadata,
                    },
                    checkpoint,
                    "CANDIDATE",
                    usage=metadata,
                )
            if stage not in {"BASELINE", "CANDIDATE", "FINAL"}:
                raise GenerationError(
                    "INVALID_STAGE", "The coding task has an unsupported next action"
                )
            if stage != "BASELINE":
                patch = PatchProposal.model_validate(checkpoint["patch"])
                validate_patch(patch, brief.source_hash)
                if not set(patch.target_files) <= set(task["plan"]["target_files"]):
                    raise GenerationError(
                        "PLAN_UNAPPROVED", "The saved patch exceeds the approved plan"
                    )
                app_dir, candidate_hash = apply_patch_to_dir(
                    app_dir, patch, root / "candidate" / "app"
                )
                if candidate_hash != checkpoint["candidate_hash"]:
                    raise GenerationError(
                        "STALE_SOURCE", "The saved patch no longer reproduces its candidate"
                    )
            timeout_s = 30
            if before_external:
                current = before_external()
                remaining = int(
                    current["limits"]["active_seconds"] - current["counters"]["active_seconds"]
                )
                if remaining < 1:
                    raise GenerationError(
                        "BUDGET_EXHAUSTED", "The active-time allowance is exhausted"
                    )
                timeout_s = min(timeout_s, remaining)

            def should_cancel() -> bool:
                if before_external:
                    try:
                        current = before_external()
                    except CodingStoreError:
                        return True
                    return current["counters"]["active_seconds"] >= current["limits"]["active_seconds"]
                return False

            report = self.executor.run(
                app_dir,
                operation_id=operation_id,
                timeout_s=timeout_s,
                should_cancel=should_cancel,
                **({"check_profile": task["plan"]["check_profile"]}
                   if isinstance(self.executor, DispatchingExecutor) else {}),
            )
            is_project = task["fixture_id"].startswith("proj-")
            if is_project:
                if report.get("contract_hash") != task["contract_hash"] or report.get("source_hash") != source_hash_for_dir(app_dir):
                    raise GenerationError(
                        "STALE_CHECKS", "The check report does not match the candidate and contract"
                    )
            else:
                if (
                    report.get("source_hash") != source_hash_for_dir(app_dir)
                    or report.get("contract_hash") != task["contract_hash"]
                ):
                    raise GenerationError(
                        "STALE_CHECKS", "The check report does not match the candidate and contract"
                    )
            passed = report.get("verdict") == "VERIFIED"
            if stage == "BASELINE":
                checkpoint["baseline"] = report
                if passed:
                    if brief.preferences and brief.preferences.workflow in {"feature", "refactor"}:
                        return ActionOutcome(
                            {"code": "BASELINE_PASSED_WORKFLOW_CONTINUES", "report": report},
                            checkpoint,
                            "EDIT",
                        )
                    return ActionOutcome(
                        {"code": "BASELINE_ALREADY_PASSES", "report": report},
                        checkpoint,
                        "BASELINE",
                        "BLOCKED",
                    )
                if report.get("verdict") != "REJECTED":
                    return ActionOutcome(
                        {"code": "CHECKS_INCONCLUSIVE", "report": report},
                        checkpoint,
                        "BASELINE",
                        "BLOCKED",
                    )
                return ActionOutcome({"report": report}, checkpoint, "EDIT")
            checkpoint["last_candidate"] = report
            if stage == "FINAL":
                checkpoint["final"] = report
                state = "REVIEW_READY" if passed else "BLOCKED"
                return ActionOutcome(
                    {
                        "code": "CHECKS_PASSED" if passed else "FRESH_CHECK_FAILED",
                        "report": report,
                        "diff": patch.diff,
                    },
                    checkpoint,
                    "FINAL",
                    state,
                )
            if passed:
                return ActionOutcome({"report": report}, checkpoint, "FINAL")
            if report.get("verdict") != "REJECTED":
                return ActionOutcome(
                    {"code": "CHECKS_INCONCLUSIVE", "report": report},
                    checkpoint,
                    "CANDIDATE",
                    "BLOCKED",
                )
            if brief.preferences and not harness_policy(brief.preferences.harness).allows_revision(task["counters"]["patch_attempts"]):
                code = "HARNESS_STOPPED" if brief.preferences.harness == "single-pass-v1" else "PATCH_ATTEMPT_LIMIT"
                return ActionOutcome(
                    {"code": code, "report": report}, checkpoint, "CANDIDATE", "BLOCKED",
                )
            if task["counters"]["patch_attempts"] >= task.get("limits", {}).get("patch_attempts", 2):
                return ActionOutcome(
                    {"code": "PATCH_ATTEMPT_LIMIT", "report": report},
                    checkpoint,
                    "CANDIDATE",
                    "BLOCKED",
                )
            return ActionOutcome({"report": report}, checkpoint, "EDIT")

    def cancel(self, operation_id: str) -> bool:
        return self.executor.cancel(operation_id)
