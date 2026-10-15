"""Bounded skill catalog (B-22).

A *skill* is a named, versioned capability the runtime can perform for one
audit, exactly like the slash commands of a coding agent: `/diagnose`,
`/repair`, `/verify`, `/strength`, `/export`, `/replay`, …  The catalog is the
single source of truth for what an action costs (model call, isolated
execution, nothing) and why it is currently unavailable.  Availability is
computed server-side from the audit record, the runtime readiness snapshot
and the remaining budgets, so the interface never has to guess.

Skills do not add new behaviour: each one maps to an existing owner-scoped
endpoint.  Invoking a skill never bypasses that endpoint's checks.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from benchproof.domain import RunState
from benchproof.storage.lifecycle import TERMINAL_STATES

SKILLS_VERSION = "skills-v1"

# Fixtures with an owner-approved curated repair diff (mirrors the UI's canonical diffs).
CURATED_REPAIR_FIXTURES: frozenset[str] = frozenset({"MC-01", "AC-01"})


@dataclass(frozen=True)
class Skill:
    skill_id: str
    slash: str
    title: str
    description: str
    category: str  # session | run | investigate | repair | evidence
    method: str
    endpoint: str  # template with {audit_id}
    needs_audit: bool = True
    costs: tuple[str, ...] = field(default_factory=tuple)  # "model-call" | "isolated-execution" | "none"
    keywords: tuple[str, ...] = field(default_factory=tuple)
    shortcut: str | None = None


SKILLS: tuple[Skill, ...] = (
    Skill("start", "/start", "Start assurance run",
          "Create a curated audit for the selected example in the chosen mode (idempotent).",
          "session", "POST", "/api/v1/audits", needs_audit=False, costs=("none",),
          keywords=("new", "create", "audit", "begin"), shortcut="n"),
    Skill("refresh-readiness", "/ready", "Refresh runtime readiness",
          "Re-probe the provider, isolated runner and worker without billing a model call.",
          "session", "GET", "/api/v1/ready?refresh=true", needs_audit=False, costs=("none",),
          keywords=("docker", "runner", "provider", "worker", "health")),
    Skill("diagnose", "/diagnose", "Run bounded investigation",
          "Ask the NVIDIA model for at most two falsifiable hypotheses and run the approved probe.",
          "investigate", "POST", "/api/v1/audits/{audit_id}/diagnose",
          costs=("model-call", "isolated-execution"), keywords=("investigate", "hypothesis", "probe"), shortcut="d"),
    Skill("recover", "/recover", "Run one fresh-context recovery",
          "After a stall, rebuild current context and retry once with the narrow failure-probe strategy.",
          "investigate", "POST", "/api/v1/audits/{audit_id}/recover",
          costs=("model-call", "isolated-execution"), keywords=("stall", "retry", "strategy")),
    Skill("decision", "/decision", "Record reviewed decision",
          "Pin a reviewed architecture decision to current file, contract and graph hashes.",
          "investigate", "POST", "/api/v1/audits/{audit_id}/decisions", costs=("none",),
          keywords=("ledger", "review", "freshness", "stale")),
    Skill("repair", "/repair", "Propose bounded repair",
          "Submit the curated minimal diff against the current source hash and context hash.",
          "repair", "POST", "/api/v1/audits/{audit_id}/patch", costs=("none",),
          keywords=("patch", "diff", "fix"), shortcut="p"),
    Skill("verify", "/verify", "Verify independently",
          "Run the protected acceptance gate in the isolated Docker runner; the candidate never writes a verdict.",
          "repair", "POST", "/api/v1/audits/{audit_id}/verify", costs=("isolated-execution",),
          keywords=("gate", "accept", "check", "oracle"), shortcut="v"),
    Skill("strength", "/strength", "Assess test strength",
          "Run up to three trusted semantic mutants in fresh branches; optional and separate from the gate.",
          "repair", "POST", "/api/v1/audits/{audit_id}/mutations", costs=("isolated-execution",),
          keywords=("mutation", "mutant", "adequacy", "weak")),
    Skill("export", "/export", "Build evidence bundle",
          "Export the immutable ZIP with manifest, checks, diff, actions and hashes.",
          "evidence", "POST", "/api/v1/audits/{audit_id}/bundle", costs=("none",),
          keywords=("bundle", "zip", "download", "evidence"), shortcut="e"),
    Skill("validate", "/validate", "Validate bundle hashes",
          "Re-hash the exported bundle without executing anything.",
          "evidence", "POST", "/api/v1/audits/{audit_id}/bundle/validate", costs=("none",),
          keywords=("integrity", "tamper", "hash")),
    Skill("replay", "/replay", "Replay checks in isolation",
          "Re-run the recorded checks from the bundle in a fresh isolated environment and compare.",
          "evidence", "POST", "/api/v1/audits/{audit_id}/replay", costs=("isolated-execution",),
          keywords=("reproduce", "independent", "fresh"), shortcut="r"),
    Skill("cancel", "/cancel", "Cancel run",
          "Request cancellation; a remote reservation stays CANCEL_PENDING until reconciled.",
          "run", "POST", "/api/v1/audits/{audit_id}/cancel", costs=("none",),
          keywords=("stop", "abort")),
)


def catalog() -> list[dict[str, Any]]:
    return [{**asdict(skill), "costs": list(skill.costs), "keywords": list(skill.keywords)} for skill in SKILLS]


def _limits(audit: dict[str, Any]) -> dict[str, int]:
    raw = audit.get("limits_json") or audit.get("limits") or "{}"
    return json.loads(raw) if isinstance(raw, str) else dict(raw)


def _reservations(audit: dict[str, Any]) -> dict[str, Any]:
    raw = audit.get("reservations") or "{}"
    return json.loads(raw) if isinstance(raw, str) else dict(raw)


def evaluate_availability(
    skill: Skill,
    *,
    audit: dict[str, Any] | None,
    runtime: dict[str, Any],
    recovery: dict[str, Any] | None = None,
    action_count: int = 0,
    patch_count: int = 0,
    has_bundle: bool = False,
) -> tuple[bool, str | None]:
    """Return (available, blocked_reason). Reasons are plain sentences for the interface."""
    runner_ok = bool((runtime.get("runner") or {}).get("isolated_execution_available"))
    provider_ok = bool((runtime.get("provider") or {}).get("configured"))

    if skill.skill_id == "refresh-readiness":
        return True, None
    if skill.skill_id == "start":
        return True, None
    if audit is None:
        return False, "Start or restore an audit first."

    state = audit.get("run_state")
    verdict = audit.get("gate_verdict")
    mode = audit.get("mode", "mock")
    limits = _limits(audit)
    reservations = _reservations(audit)
    terminal = state in TERMINAL_STATES

    if skill.skill_id == "cancel":
        if terminal:
            return False, f"The run is already {state}."
        if state == RunState.CANCEL_PENDING.value:
            return False, "Cancellation is pending remote reconciliation."
        return True, None

    if skill.skill_id in {"export", "validate"}:
        if skill.skill_id == "validate" and not has_bundle:
            return False, "Build the evidence bundle first."
        return True, None

    if skill.skill_id == "replay":
        if not runner_ok:
            return False, "Replay needs the isolated Docker runner; refresh readiness once Docker is up."
        return True, None

    if terminal and skill.skill_id != "export":
        return False, f"The run is {state}; preserved evidence can still be exported."
    if state == RunState.CANCEL_PENDING.value:
        return False, "Wait for cancellation reconciliation; no new work may start."

    if skill.skill_id == "diagnose":
        if state == RunState.STALLED.value:
            return False, "The same attempt repeated without progress; use the single recovery."
        if state == RunState.BLOCKED.value:
            return False, "The recovery also stalled; the audit is terminally blocked."
        if action_count >= int(limits.get("max_actions", 15)):
            return False, "The original action budget is exhausted."
        if mode == "live" and not provider_ok:
            return False, "Live mode needs the configured NVIDIA provider; no mock fallback is used."
        return True, None

    if skill.skill_id == "recover":
        if state != RunState.STALLED.value:
            return False, "Recovery is only offered after a STALLED run."
        if int((recovery or {}).get("recovery_count", 0)) >= 1:
            return False, "The single recovery has been used."
        if mode == "live" and not provider_ok:
            return False, "Live mode needs the configured NVIDIA provider."
        return True, None

    if skill.skill_id == "decision":
        return True, None

    if skill.skill_id == "repair":
        if audit.get("fixture_id") not in CURATED_REPAIR_FIXTURES:
            return False, "No owner-approved repair diff exists for this example; verification stays available."
        if patch_count >= int(limits.get("max_patches", 5)):
            return False, "The patch budget is exhausted."
        return True, None

    if skill.skill_id == "verify":
        if not runner_ok:
            return False, "Verification needs the isolated Docker runner; refresh readiness once Docker is up."
        return True, None

    if skill.skill_id == "strength":
        if verdict != "VERIFIED":
            return False, "Mutation strength is assessed only after a VERIFIED gate verdict."
        if not runner_ok:
            return False, "Mutation assessment needs the isolated Docker runner."
        remaining = int(limits.get("max_executions", 12)) - int(reservations.get("mutation_executions", 0))
        if remaining < 2:
            return False, "Not enough execution budget remains for a baseline plus one mutant."
        return True, None

    return False, "Unknown skill."


def describe(
    *,
    audit: dict[str, Any] | None,
    runtime: dict[str, Any],
    recovery: dict[str, Any] | None = None,
    action_count: int = 0,
    patch_count: int = 0,
    has_bundle: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for skill in SKILLS:
        available, reason = evaluate_availability(
            skill,
            audit=audit,
            runtime=runtime,
            recovery=recovery,
            action_count=action_count,
            patch_count=patch_count,
            has_bundle=has_bundle,
        )
        entry = {**asdict(skill), "costs": list(skill.costs), "keywords": list(skill.keywords)}
        entry.update(available=available, blocked_reason=reason)
        if audit is not None:
            entry["endpoint"] = skill.endpoint.format(audit_id=audit["audit_id"])
        out.append(entry)
    return out
