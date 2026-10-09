"""Bounded hash-linked context packet builder (B-08).

Extracts source excerpts, selected checks, unresolved coverage gaps,
active decisions and budgets, and computes the canonical context hash.
"""

from __future__ import annotations

from pathlib import Path

from benchproof.constraints import contract_hash
from benchproof.domain import ContextPacket, GraphSnapshot
from benchproof.fixtures import source_hash_for_dir
from benchproof.impact import ImpactReport

MAX_EXCERPT_LINES = 100


def build_context_packet(
    app_dir: Path,
    graph: GraphSnapshot,
    impact: ImpactReport,
    current_decision_ids: list[str] | None = None,
    remaining_budget: dict[str, int] | None = None,
) -> ContextPacket:
    """Construct a bounded, hash-linked context packet."""
    shash = source_hash_for_dir(app_dir)
    chash = contract_hash()

    # Build excerpts for impacted files
    excerpts: dict[str, str] = {}
    py_files = sorted(p for p in app_dir.rglob("*.py") if "__pycache__" not in p.parts)

    for fpath in py_files:
        rel = fpath.relative_to(app_dir.parent).as_posix()
        # Check if file defines any of the impacted symbols
        file_node = f"file:{rel}"
        defines_impacted = any(
            edge.edge_type == "defines"
            and edge.from_node == file_node
            and edge.to_node.replace("symbol:", "") in impact.impacted_symbols
            for edge in graph.edges
        )
        if defines_impacted or rel in impact.changed_symbols:
            lines = fpath.read_text(encoding="utf-8").splitlines()
            excerpt_text = "\n".join(lines[:MAX_EXCERPT_LINES])
            excerpts[rel] = excerpt_text

    budget = remaining_budget or {
        "max_actions": 15,
        "max_patches": 5,
        "process_timeout_s": 60,
    }

    packet = ContextPacket(
        source_hash=shash,
        contract_hash=chash,
        graph_hash=graph.graph_hash,
        current_decision_ids=current_decision_ids or [],
        excerpts=excerpts,
        selected_checks=impact.selected_checks,
        unresolved_coverage=graph.unresolved_items,
        remaining_budget=budget,
    )
    packet.compute_hash()
    return packet
