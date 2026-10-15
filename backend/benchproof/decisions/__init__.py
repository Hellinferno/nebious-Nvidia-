"""Dependency-aware decision ledger and current-context reconstruction (B-14)."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchproof.domain import (
    Decision,
    DecisionDependency,
    DecisionDependencyStatus,
    DecisionReviewStatus,
    DecisionStatus,
)
from benchproof.fixtures import canonical_source_bytes, source_hash_for_dir
from benchproof.storage import (
    get_decision,
    list_decisions,
    save_decision,
    update_decision_freshness,
)


class DecisionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _candidate_path(app_dir: Path, requested: str) -> tuple[str, Path]:
    normalized = requested.replace("\\", "/").removeprefix("./")
    normalized = normalized.removeprefix("app/")
    candidate = (app_dir / normalized).resolve()
    root = app_dir.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DecisionError("INVALID_INPUT", f"Decision dependency escapes app/: {requested}") from exc
    if not normalized or normalized == ".":
        raise DecisionError("INVALID_INPUT", "Decision dependency must name a file under app/")
    return f"app/{candidate.relative_to(root).as_posix()}", candidate


def _file_hash(path: Path) -> str | None:
    # LF-normalized so a declared dependency stays CURRENT across CRLF/LF checkouts.
    return hashlib.sha256(canonical_source_bytes(path)).hexdigest() if path.is_file() else None


def create_decision(
    *,
    audit_id: str,
    app_dir: Path,
    statement: str,
    owner: str,
    review_status: DecisionReviewStatus,
    current_contract_hash: str,
    dependency_paths: list[str] | None = None,
    include_source: bool = False,
    include_contract: bool = True,
    include_graph: bool = False,
    evidence_ids: list[str] | None = None,
    revisit_condition: str | None = None,
    supersedes: str | None = None,
    db_path: Path | None = None,
) -> Decision:
    """Create a proposed or human-reviewed record from server-computed hashes."""
    if not statement.strip():
        raise DecisionError("INVALID_INPUT", "Decision statement is required")

    dependencies: list[DecisionDependency] = []
    for requested in sorted(set(dependency_paths or [])):
        key, path = _candidate_path(app_dir, requested)
        digest = _file_hash(path)
        if digest is None:
            raise DecisionError("INVALID_INPUT", f"Decision dependency does not exist: {key}")
        dependencies.append(
            DecisionDependency(
                dependency_type="file",
                dependency_key=key,
                expected_hash=digest,
                current_hash=digest,
            )
        )

    if include_source:
        digest = source_hash_for_dir(app_dir)
        dependencies.append(
            DecisionDependency(
                dependency_type="source",
                dependency_key="candidate-source",
                expected_hash=digest,
                current_hash=digest,
            )
        )
    if include_contract:
        dependencies.append(
            DecisionDependency(
                dependency_type="contract",
                dependency_key="accepted-contract",
                expected_hash=current_contract_hash,
                current_hash=current_contract_hash,
            )
        )
    if include_graph:
        from benchproof.graph.builder import build_state_graph

        digest = build_state_graph(app_dir, current_contract_hash).graph_hash
        dependencies.append(
            DecisionDependency(
                dependency_type="graph",
                dependency_key="engineering-graph",
                expected_hash=digest,
                current_hash=digest,
            )
        )
    if not dependencies:
        raise DecisionError("INVALID_INPUT", "At least one dependency is required")

    now = datetime.now(UTC)
    decision = Decision(
        decision_id=f"decision-{uuid.uuid4().hex[:12]}",
        statement=statement.strip(),
        review_status=review_status,
        dependencies=dependencies,
        dependency_hashes=[item.expected_hash for item in dependencies],
        evidence_ids=evidence_ids or [],
        owner=owner,
        role="reviewer" if review_status == DecisionReviewStatus.REVIEWED else "agent",
        timestamp=now,
        supersedes=supersedes,
        revisit_condition=revisit_condition,
        current_versions={
            f"{item.dependency_type}:{item.dependency_key}": item.expected_hash
            for item in dependencies
        },
        reviewed_at=now if review_status == DecisionReviewStatus.REVIEWED else None,
    )
    save_decision(audit_id, decision, db_path)
    if supersedes:
        prior = get_decision(supersedes, db_path)
        if prior is not None and prior["status"] != DecisionStatus.SUPERSEDED.value:
            update_decision_freshness(
                prior["decision_id"],
                DecisionStatus.SUPERSEDED.value,
                prior["dependencies"],
                prior["current_versions"],
                prior.get("stale_reason") or f"Superseded by {decision.decision_id}",
                db_path,
            )
    return decision


def _current_dependency_hash(
    dependency: dict[str, Any],
    app_dir: Path,
    current_contract_hash: str,
) -> str | None:
    dep_type = dependency["dependency_type"]
    if dep_type == "source":
        return source_hash_for_dir(app_dir)
    if dep_type == "contract":
        return current_contract_hash
    if dep_type == "graph":
        from benchproof.graph.builder import build_state_graph

        return build_state_graph(app_dir, current_contract_hash).graph_hash
    if dep_type == "file":
        _, path = _candidate_path(app_dir, dependency["dependency_key"])
        return _file_hash(path)
    raise DecisionError("INVALID_INPUT", f"Unsupported dependency type: {dep_type}")


def refresh_decisions(
    audit_id: str,
    app_dir: Path,
    current_contract_hash: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Invalidate changed/deleted dependencies. Staleness is sticky until re-review."""
    started = time.perf_counter()
    refreshed: list[dict[str, Any]] = []
    invalidated: list[str] = []

    for decision in list_decisions(audit_id, db_path):
        dependencies: list[dict[str, Any]] = []
        reasons: list[str] = []
        versions: dict[str, str | None] = {}
        for dependency in decision["dependencies"]:
            current = _current_dependency_hash(dependency, app_dir, current_contract_hash)
            key = f"{dependency['dependency_type']}:{dependency['dependency_key']}"
            versions[key] = current
            updated = dict(dependency)
            updated["current_hash"] = current
            if current is None:
                updated["status"] = DecisionDependencyStatus.DELETED.value
                updated["reason"] = f"{dependency['dependency_key']} was deleted"
                reasons.append(updated["reason"])
            elif current != dependency["expected_hash"]:
                updated["status"] = DecisionDependencyStatus.CHANGED.value
                updated["reason"] = (
                    f"{dependency['dependency_key']} changed from "
                    f"{dependency['expected_hash'][:12]} to {current[:12]}"
                )
                reasons.append(updated["reason"])
            else:
                updated["status"] = DecisionDependencyStatus.CURRENT.value
                updated["reason"] = None
            dependencies.append(updated)

        was_current = decision["status"] == DecisionStatus.CURRENT.value
        if decision["status"] == DecisionStatus.SUPERSEDED.value:
            status = DecisionStatus.SUPERSEDED.value
            stale_reason = decision["stale_reason"]
        elif decision["status"] == DecisionStatus.STALE.value:
            status = DecisionStatus.STALE.value
            stale_reason = decision["stale_reason"] or "Previously invalidated; re-review required"
        elif reasons:
            status = DecisionStatus.STALE.value
            stale_reason = "; ".join(reasons)
            if was_current:
                invalidated.append(decision["decision_id"])
        else:
            status = decision["status"]
            stale_reason = decision["stale_reason"]

        update_decision_freshness(
            decision["decision_id"],
            status,
            dependencies,
            versions,
            stale_reason,
            db_path,
        )
        decision.update(
            status=status,
            dependencies=dependencies,
            current_versions=versions,
            stale_reason=stale_reason,
        )
        refreshed.append(decision)

    current_ids = [
        decision["decision_id"]
        for decision in refreshed
        if decision["status"] == DecisionStatus.CURRENT.value
        and decision["review_status"] == DecisionReviewStatus.REVIEWED.value
    ]
    return {
        "decisions": refreshed,
        "current_decision_ids": current_ids,
        "invalidated_decision_ids": invalidated,
        "refresh_overhead_ms": int((time.perf_counter() - started) * 1000),
    }


def build_current_context(
    audit_id: str,
    app_dir: Path,
    current_contract_hash: str,
    *,
    target_symbols: list[str] | None = None,
    remaining_budget: dict[str, int] | None = None,
    db_path: Path | None = None,
) -> tuple[Any, Any, Any, dict[str, Any]]:
    """Rebuild graph, impact and context from reviewed, current decisions only."""
    from benchproof.graph.builder import build_state_graph
    from benchproof.impact import analyze_impact
    from benchproof.impact.context import build_context_packet

    ledger = refresh_decisions(audit_id, app_dir, current_contract_hash, db_path)
    graph = build_state_graph(app_dir, current_contract_hash)
    impact = analyze_impact(graph, changed_symbols=target_symbols)
    context = build_context_packet(
        app_dir,
        graph,
        impact,
        current_decision_ids=ledger["current_decision_ids"],
        remaining_budget=remaining_budget,
        contract_hash_override=current_contract_hash,
    )
    return graph, impact, context, ledger
