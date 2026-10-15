"""Frozen evaluation configuration (B-19).

The configuration identity pins everything that decides a trial outcome: model and
parameters, prompt and schema hashes, hard budgets and patch limits, evaluator and
contract hashes, graph/fingerprint rules, the candidate image, the suite lock with
its predetermined trial plans, and a hash of the runtime source. Trial records cite
the identity hash; a final run refuses to start when the current identity differs.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchproof.constraints import contract_hash
from benchproof.evaluator.harness import evaluator_hash, required_check_ids
from benchproof.evaluator.observations import WORKER_CALLER_PATH_VERSION
from benchproof.evaluator.smoke import SMOKE_VERSION
from benchproof.execution.docker_runner import DEFAULT_IMAGE
from benchproof.patch import MAX_DIFF_BYTES, MAX_DIFF_LINES, MAX_TARGET_FILES
from benchproof.suites import REPAIR_SUITE, load_lock, load_manifest, load_scope, repair_case_ids
from benchproof.trajectory import FINGERPRINT_RULE_VERSION, STALL_REPEAT_THRESHOLD
from benchproof.trials import DEFAULT_BUDGETS, TrialSpec, build_plan, canonical_hash, plan_hash
from benchproof.trials.systems import PROMPTS, SCHEMAS

BACKEND = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND.parent
CONFIG_SCHEMA = "benchproof/eval-config-v1"
CONFIG_ID = "eval-config-v1"
CONFIG_PATH = BACKEND / "evaluation" / f"{CONFIG_ID}.json"
DEFAULT_MODEL_ID = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
RUNTIME_PATHS: tuple[str, ...] = ("backend/benchproof", "backend/runner/launcher")
R6_SUITE = "repair-r6-v1"

SYSTEM_DESCRIPTIONS: dict[str, dict[str, Any]] = {
    "B0": {
        "name": "visible smoke gate",
        "information": ["original source", "visible-smoke-v1 results"],
        "actions": ["one visible run"],
        "excluded": ["model", "repair"],
    },
    "B1": {
        "name": "same NVIDIA repair agent without assurance orchestration",
        "information": ["task statement", "accepted constraints", "full app source", "probe description",
                        "visible smoke results", "raw probe observation"],
        "actions": ["diagnose", "up to two full-file patches", "submit or withdraw"],
        "excluded": ["graph context", "protected check outcomes", "protected gate", "trajectory stopping",
                     "decision ledger"],
        "final_candidate": "latest applied patch unless the agent withdrew; the agent cannot judge success",
    },
    "B2": {
        "name": "BenchProof runtime",
        "information": ["everything B1 receives", "engineering-state graph context",
                        "protected check observations (contract-level)"],
        "actions": ["diagnose", "up to two full-file patches", "BLOCKED"],
        "policy": ["a finding is CONFIRMED only by a failing protected check",
                   "repair only after a protected failure", "the protected gate alone accepts a candidate",
                   "an identical rejected candidate stops as STALLED before execution"],
        "final_candidate": "gate-verified candidate, otherwise the unchanged source",
        "not_exercised": ["decision ledger (a fresh trial has no decisions)", "recovery replan"],
    },
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def code_hash(*relative_dirs: str) -> str:
    """Hash of every .py file under the given repo-relative directories, LF-normalized."""
    entries: dict[str, str] = {}
    for rel in relative_dirs:
        for path in sorted((REPO_ROOT / rel).rglob("*.py")):
            if "__pycache__" not in path.parts:
                entries[path.relative_to(REPO_ROOT).as_posix()] = _sha(path.read_bytes().replace(b"\r\n", b"\n"))
    return canonical_hash(entries)


def suite_specs(suite_id: str) -> tuple[list[TrialSpec], list[str]]:
    """Predetermined plan and case ids for the selected suite or its predeclared fallback."""
    manifest = load_manifest(REPAIR_SUITE)
    if suite_id == REPAIR_SUITE:
        case_ids = repair_case_ids()
    elif suite_id == R6_SUITE:
        case_ids = list(load_scope()["fallback"]["repair"]["case_ids"])
    else:
        raise ValueError(f"unknown frozen repair suite: {suite_id}")
    specs = build_plan(case_ids, manifest["counts"]["trials_per_case"], manifest["shuffle_seed"])
    return specs, case_ids


def _plans() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for suite_id in (REPAIR_SUITE, R6_SUITE):
        specs, case_ids = suite_specs(suite_id)
        out[suite_id] = {
            "case_ids": sorted(case_ids),
            "trials": {s: sum(1 for x in specs if x.system == s) for s in ("B0", "B1", "B2")},
            "plan_hash": plan_hash(specs),
        }
    return out


def identity(model_id: str = DEFAULT_MODEL_ID, image_ref: str | None = None) -> dict[str, Any]:
    scope = load_scope()
    return {
        "model": {
            "provider": "nebius-token-factory",
            "model_id": model_id,
            "temperature": 0.0,
            "max_output_tokens": DEFAULT_BUDGETS["max_output_tokens_per_call"],
            "response_format": "json_object",
            "format_repairs_per_call": 1,
        },
        "budgets": dict(DEFAULT_BUDGETS),
        "patch_limits": {"max_diff_lines": MAX_DIFF_LINES, "max_diff_bytes": MAX_DIFF_BYTES,
                         "max_target_files": MAX_TARGET_FILES},
        "prompts": {name: _sha(text.encode("utf-8")) for name, text in sorted(PROMPTS.items())},
        "schemas": {name: canonical_hash(model.model_json_schema()) for name, model in sorted(SCHEMAS.items())},
        "evaluator": {
            "evaluator_hash": evaluator_hash(),
            "contract_hash": contract_hash(),
            "required_check_ids": sorted(required_check_ids()),
            "smoke_version": SMOKE_VERSION,
            "worker_caller_path_version": WORKER_CALLER_PATH_VERSION,
        },
        "graph": {"builder_hash": code_hash("backend/benchproof/graph", "backend/benchproof/impact")},
        "trajectory": {"fingerprint_rule": FINGERPRINT_RULE_VERSION, "repeat_threshold": STALL_REPEAT_THRESHOLD},
        "runner": {"executor": "docker-local", "image": DEFAULT_IMAGE, "image_ref": image_ref},
        "suites": {
            "lock_hash": load_lock()["lock_hash"],
            "selected": scope["selected"]["repair"],
            "fallback": R6_SUITE,
            "plans": _plans(),
        },
        "runtime_code_hash": code_hash(*RUNTIME_PATHS),
    }


def runtime_git_state() -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            out = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                                 check=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout

    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--", *RUNTIME_PATHS)
    return {
        "git_head": head.strip() if head else None,
        "runtime_paths": list(RUNTIME_PATHS),
        "runtime_paths_clean": status is not None and not status.strip(),
    }


def worst_case_usage() -> dict[str, Any]:
    assigned = load_scope()["assigned_trials"]
    model_trials = assigned["B1_same_agent_trials"] + assigned["B2_runtime_trials"]
    return {
        "basis": "hard per-trial limits; actual use is reconciled in every trial record",
        "model_trials": model_trials,
        "model_calls": model_trials * DEFAULT_BUDGETS["max_model_calls"],
        "total_tokens": model_trials * DEFAULT_BUDGETS["max_total_tokens"],
        "system_executions": model_trials * DEFAULT_BUDGETS["max_executions"]
        + assigned["B0_visible_smoke_runs"],
        "final_evaluator_executions": model_trials,
    }


def build_config(model_id: str = DEFAULT_MODEL_ID, image_ref: str | None = None) -> dict[str, Any]:
    ident = identity(model_id, image_ref)
    git = runtime_git_state()
    blockers: list[str] = []
    if not git["runtime_paths_clean"]:
        blockers.append("runtime source has uncommitted changes; commit it, then refreeze")
    if not image_ref:
        blockers.append("candidate image reference unavailable (Docker daemon or image not ready)")
    return {
        "schema_version": CONFIG_SCHEMA,
        "config_id": CONFIG_ID,
        "config_hash": canonical_hash(ident),
        "freeze_status": "candidate" if blockers else "frozen",
        "freeze_blockers": blockers,
        "created_at": datetime.now(UTC).isoformat(),
        "runtime": git,
        "identity": ident,
        "systems": SYSTEM_DESCRIPTIONS,
        "worst_case_usage": worst_case_usage(),
        "price_snapshot": {
            "status": "NOT_RECORDED",
            "reason": "no dated Token Factory price was captured; cost is reported as unknown",
        },
    }


def identity_differences(frozen: dict[str, Any], current: dict[str, Any], prefix: str = "") -> list[str]:
    problems: list[str] = []
    for key in sorted(set(frozen) | set(current)):
        a, b = frozen.get(key), current.get(key)
        if isinstance(a, dict) and isinstance(b, dict):
            problems += identity_differences(a, b, f"{prefix}{key}.")
        elif a != b:
            problems.append(f"{prefix}{key} changed")
    return problems


def verify_config(config: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Discrepancies between a stored configuration and the current identity."""
    problems: list[str] = []
    if config.get("schema_version") != CONFIG_SCHEMA:
        problems.append(f"unexpected config schema {config.get('schema_version')!r}")
    if canonical_hash(config.get("identity", {})) != config.get("config_hash"):
        problems.append("config_hash does not match its own identity")
    return problems + identity_differences(config.get("identity", {}), current)


def final_run_problems(
    config: dict[str, Any],
    current: dict[str, Any],
    *,
    executor_name: str,
    provider_mode: str,
    model_id: str,
) -> list[str]:
    """Every reason a final (measured) run must not start. Empty means it may start."""
    problems = verify_config(config, current)
    if config.get("freeze_status") != "frozen":
        problems.append(
            f"configuration is {config.get('freeze_status')!r}, not frozen: {config.get('freeze_blockers')}"
        )
    if executor_name != current["runner"]["executor"]:
        problems.append("final trials require the isolated Docker runner")
    if provider_mode != "live":
        problems.append("final trials require the live NVIDIA provider")
    if model_id != config.get("identity", {}).get("model", {}).get("model_id"):
        problems.append("provider model differs from the frozen model")
    return problems


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
