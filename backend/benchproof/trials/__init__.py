"""Fair baseline trial harness (B-19).

Three systems share the same source, accepted constraints, model configuration
and hard limits:

  B0  the visible smoke gate on the original source; no model, no repair
  B1  the NVIDIA repair agent with visible tests and the raw probe only
  B2  the BenchProof runtime: B1 plus graph context, protected check feedback,
      evidence-based confirmation, the protected acceptance gate and
      repeated-candidate stopping

Every trial writes one sealed, write-once record. The final outcome of a trial
comes from a fresh run of the frozen protected evaluator outside the system's
loop; scoring against trusted truth happens later in `benchproof.trials.summary`.
Nothing in a trial loop reads `expected.json` or a reference repair.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from benchproof.evaluator.harness import collect_observations_in_process, judge
from benchproof.evaluator.smoke import evaluate_smoke, smoke_verdict
from benchproof.execution.base import prepare_snapshot
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import assert_no_trusted_assets, source_hash_for_dir

RECORD_SCHEMA = "benchproof/trial-record-v1"
PLAN_SCHEMA = "benchproof/trial-plan-v1"
FINAL_EVALUATOR = "frozen-protected-evaluator"
SYSTEMS: tuple[str, ...] = ("B0", "B1", "B2")
MODEL_SYSTEMS: tuple[str, ...] = ("B1", "B2")

# Hard limits shared by B1 and B2. Token use is reserved conservatively before each call
# (prompt characters / 3 plus the output cap) and reconciled with reported usage afterwards.
DEFAULT_BUDGETS: dict[str, int] = {
    "max_model_calls": 6,
    "max_output_tokens_per_call": 1536,
    "max_prompt_chars": 24_000,
    "max_total_tokens": 24_000,
    "max_executions": 12,
    "max_patches": 2,
    "max_wall_s": 300,
    "execution_timeout_s": 30,
}


class BudgetExhausted(Exception):
    def __init__(self, limit: str) -> None:
        super().__init__(f"trial budget exhausted: {limit}")
        self.limit = limit


class TrialBudget:
    """Per-trial hard limits. Counters only grow; nothing resets them."""

    def __init__(self, limits: dict[str, int]) -> None:
        self.limits = dict(limits)
        self.used = {"model_calls": 0, "total_tokens": 0, "executions": 0, "patches": 0}
        self._started = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._started) * 1000)

    def _check_wall(self) -> None:
        if self.elapsed_ms() > self.limits["max_wall_s"] * 1000:
            raise BudgetExhausted("max_wall_s")

    def reserve_call(self, prompt_chars: int) -> int:
        """Reserve an upper bound for one model call; returns the reserved token estimate."""
        self._check_wall()
        if self.used["model_calls"] >= self.limits["max_model_calls"]:
            raise BudgetExhausted("max_model_calls")
        if prompt_chars > self.limits["max_prompt_chars"]:
            raise BudgetExhausted("max_prompt_chars")
        reserved = prompt_chars // 3 + self.limits["max_output_tokens_per_call"]
        if self.used["total_tokens"] + reserved > self.limits["max_total_tokens"]:
            raise BudgetExhausted("max_total_tokens")
        self.used["model_calls"] += 1
        return reserved

    def settle_call(self, usage: dict[str, Any] | None, reserved: int) -> None:
        """Charge reported tokens; unknown usage (including a failed call) keeps the reservation."""
        total = (usage or {}).get("total_tokens")
        self.used["total_tokens"] += total if isinstance(total, int) and total >= 0 else reserved

    def reserve_execution(self) -> None:
        self._check_wall()
        if self.used["executions"] >= self.limits["max_executions"]:
            raise BudgetExhausted("max_executions")
        self.used["executions"] += 1

    def reserve_patch(self) -> None:
        if self.used["patches"] >= self.limits["max_patches"]:
            raise BudgetExhausted("max_patches")
        self.used["patches"] += 1

    def snapshot(self) -> dict[str, Any]:
        return {"limits": dict(self.limits), "used": dict(self.used), "elapsed_ms": self.elapsed_ms()}


# ── Execution ────────────────────────────────────────────────────────────


class Executor(Protocol):
    name: str
    isolated: bool

    def observe(self, app_dir: Path, timeout_s: int) -> tuple[dict[str, Any] | None, dict[str, Any]]: ...


class InProcessExecutor:
    """DEVELOPMENT ONLY: imports candidate code on this machine. Refused for final trials."""

    name = "development-in-process"
    isolated = False

    def observe(self, app_dir: Path, timeout_s: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        started = time.perf_counter()
        obs = collect_observations_in_process(app_dir)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return obs, {"executor": self.name, "isolated": False, "image_ref": "local-in-process",
                     "elapsed_ms": elapsed_ms}


class DockerExecutor:
    """The isolated runner. `RunnerUnavailable` propagates to the caller unchanged."""

    name = "docker-local"
    isolated = True

    def __init__(self, runner: DockerRunner | None = None) -> None:
        self.runner = runner or DockerRunner()

    def observe(self, app_dir: Path, timeout_s: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        snapshot = prepare_snapshot(app_dir)
        try:
            res = self.runner.run_observation(snapshot, timeout_s=timeout_s)
        finally:
            snapshot.cleanup()
        return res.observations, {
            "executor": self.name,
            "isolated": True,
            "image_ref": res.image_ref,
            "operation_id": res.operation_id,
            "elapsed_ms": res.duration_ms,
            "timed_out": res.timed_out,
            "error": res.error,
        }


def visible_observation(obs: dict[str, Any] | None) -> dict[str, Any]:
    """What a developer could see from the probe: responses, worker receipts and load errors.

    Launcher metadata (child process, environment probes) never reaches a prompt.
    """
    if not isinstance(obs, dict):
        return {"error": "no observation produced", "route": {}, "worker": {}}
    return {"error": obs.get("error"), "route": obs.get("route") or {}, "worker": obs.get("worker") or {}}


def copy_candidate_tree(case_dir: Path, dest: Path) -> Path:
    """Copy only the agent-visible `app/` tree of a case into a fresh workspace."""
    app = dest / "app"
    shutil.copytree(Path(case_dir) / "app", app, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    assert_no_trusted_assets(app)
    return app


def final_evaluate(
    original_app: Path, final_app: Path, executor: Executor, timeout_s: int
) -> dict[str, Any]:
    """Fresh, independent run of the frozen protected evaluator on a trial's final candidate."""
    from benchproof.execution.base import RunnerUnavailable

    original_hash = source_hash_for_dir(original_app)
    candidate_hash = source_hash_for_dir(final_app)
    base: dict[str, Any] = {
        "evaluator": FINAL_EVALUATOR,
        "original_source_hash": original_hash,
        "candidate_source_hash": candidate_hash,
        "changed": candidate_hash != original_hash,
    }
    try:
        obs, meta = executor.observe(final_app, timeout_s)
    except RunnerUnavailable as exc:
        return {**base, "verdict": "NOT_EVALUATED", "error": str(exc)}
    judged = judge(obs, final_app)
    return {
        **base,
        "verdict": judged["verdict"],
        "failing_checks": judged["failing_checks"],
        "unknown_checks": judged["unknown_checks"],
        "evaluator_hash": judged["evaluator_hash"],
        "contract_hash": judged["contract_hash"],
        "smoke_verdict": smoke_verdict(evaluate_smoke(obs)),
        "execution": meta,
    }


# ── Plan ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TrialSpec:
    order: int
    system: str
    case_id: str
    trial_index: int

    @property
    def trial_id(self) -> str:
        return f"{self.system}-{self.case_id}-t{self.trial_index}"

    def to_dict(self) -> dict[str, Any]:
        return {"order": self.order, "trial_id": self.trial_id, "system": self.system,
                "case_id": self.case_id, "trial_index": self.trial_index}


def _rank(seed: str, *parts: str) -> str:
    return hashlib.sha256(":".join((seed, *parts)).encode("utf-8")).hexdigest()


def build_plan(
    case_ids: list[str],
    trials_per_case: int,
    seed: str,
    systems: tuple[str, ...] = SYSTEMS,
) -> list[TrialSpec]:
    """Predetermined, balanced order.

    B0 runs once per case first (deterministic, no model). Then each trial index is a
    block that visits every case in a seeded order; B1 and B2 alternate which goes
    first, so each system leads in half of every block.
    """
    rows: list[tuple[str, str, int]] = []
    if "B0" in systems:
        rows.extend(("B0", case, 1) for case in sorted(case_ids, key=lambda c: _rank(seed, "B0", c)))
    paired = [s for s in MODEL_SYSTEMS if s in systems]
    for t in range(1, trials_per_case + 1):
        block = sorted(case_ids, key=lambda c: _rank(seed, str(t), c))
        for position, case in enumerate(block):
            ordered = paired if (position + t) % 2 == 0 else list(reversed(paired))
            rows.extend((system, case, t) for system in ordered)
    return [TrialSpec(order=i, system=s, case_id=c, trial_index=t) for i, (s, c, t) in enumerate(rows, 1)]


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def plan_hash(specs: list[TrialSpec]) -> str:
    return canonical_hash([spec.to_dict() for spec in specs])


# ── Immutable records ────────────────────────────────────────────────────


def record_hash(record: dict[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k != "record_hash"})


def seal(record: dict[str, Any]) -> dict[str, Any]:
    record["record_hash"] = record_hash(record)
    return record


def write_once(path: Path, payload: dict[str, Any]) -> None:
    """Exclusive create: an existing record is never overwritten or replaced."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")


def load_records(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run_dir / "records").glob("*.json"))]
