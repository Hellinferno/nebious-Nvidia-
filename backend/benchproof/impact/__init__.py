"""Impact analysis and deterministic risk scoring (B-08).

Reverse-traverses changed callers, contracts, and checks from the engineering graph.
Calculates deterministic ordinal risk levels (CRITICAL, HIGH, MEDIUM, LOW) with
human-readable reasons. Always includes global integrity checks.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from benchproof.constraints import list_constraints
from benchproof.domain import GraphSnapshot


class RiskSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


_SEVERITY_ORDER = {
    RiskSeverity.LOW: 1,
    RiskSeverity.MEDIUM: 2,
    RiskSeverity.HIGH: 3,
    RiskSeverity.CRITICAL: 4,
}

CRITICAL_PATHS = {"observe_invoice.py", "expected.json", "launcher", "conftest.py"}
HIGH_RISK_SYMBOLS = {
    "app.schemas:ReceiptResponse",
    "app.schemas:InvoiceRequest",
    "app.money:compute_total",
    "app.repository:save_receipt",
    "app.repository:get_receipt",
}


class ImpactReport:
    def __init__(
        self,
        changed_symbols: list[str],
        impacted_symbols: list[str],
        impacted_contracts: list[str],
        selected_checks: list[str],
        risk_severity: RiskSeverity,
        risk_reasons: list[str],
        coverage_status: str,
    ) -> None:
        self.changed_symbols = changed_symbols
        self.impacted_symbols = impacted_symbols
        self.impacted_contracts = impacted_contracts
        self.selected_checks = selected_checks
        self.risk_severity = risk_severity
        self.risk_reasons = risk_reasons
        self.coverage_status = coverage_status

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_symbols": self.changed_symbols,
            "impacted_symbols": self.impacted_symbols,
            "impacted_contracts": self.impacted_contracts,
            "selected_checks": self.selected_checks,
            "risk_severity": self.risk_severity.value,
            "risk_reasons": self.risk_reasons,
            "coverage_status": self.coverage_status,
        }


def analyze_impact(
    graph: GraphSnapshot,
    changed_symbols: list[str] | None = None,
    changed_files: list[str] | None = None,
) -> ImpactReport:
    """Analyze blast radius and compute deterministic risk reasons."""
    changed_syms = set(changed_symbols or [])
    changed_fls = set(changed_files or [])

    # If changed files passed without symbols, map file -> symbols
    if changed_fls and not changed_syms:
        for edge in graph.edges:
            if edge.edge_type == "defines" and edge.from_node in {f"file:{f}" for f in changed_fls}:
                sym_name = edge.to_node.replace("symbol:", "")
                changed_syms.add(sym_name)

    # 1. Reverse Traversal: find callers and importers
    impacted_symbols: set[str] = set(changed_syms)
    to_explore = list(changed_syms)
    visited = set(changed_syms)

    while to_explore:
        curr = to_explore.pop(0)
        curr_node = f"symbol:{curr}"
        for edge in graph.edges:
            if edge.edge_type in {"calls", "imports"} and edge.to_node == curr_node:
                caller = edge.from_node.replace("symbol:", "").replace("file:", "")
                impacted_symbols.add(caller)
                if caller not in visited:
                    visited.add(caller)
                    to_explore.append(caller)

    # 2. Map impacted symbols to contracts (implements)
    impacted_contracts: set[str] = set()
    for sym in impacted_symbols:
        sym_node = f"symbol:{sym}"
        for edge in graph.edges:
            if edge.edge_type == "implements" and edge.from_node == sym_node:
                contract_id = edge.to_node.replace("contract:", "")
                impacted_contracts.add(contract_id)

    # 3. Map contracts to protected checks (protected_by)
    selected_checks: set[str] = set()
    for contract_id in impacted_contracts:
        c_node = f"contract:{contract_id}"
        for edge in graph.edges:
            if edge.edge_type == "protected_by" and edge.from_node == c_node:
                test_id = edge.to_node.replace("test:", "")
                selected_checks.add(test_id)

    # 4. Mandatory Global Integrity Checks
    # The specification requires C-INTEGRITY and global checks always be included
    for c in list_constraints():
        if c.constraint_id == "C-INTEGRITY" or c.required:
            for check_id in c.protected_check_ids:
                selected_checks.add(check_id)

    # 5. Deterministic Ordinal Risk Evaluation
    reasons: list[str] = []
    severities: list[RiskSeverity] = [RiskSeverity.LOW]

    # Check for Critical paths
    for f in changed_fls:
        if any(cp in f for cp in CRITICAL_PATHS):
            severities.append(RiskSeverity.CRITICAL)
            reasons.append(f"Protected evaluator/launcher file modified: {f}")

    # Check for High risk symbols
    for s in changed_syms:
        if s in HIGH_RISK_SYMBOLS:
            severities.append(RiskSeverity.HIGH)
            if "schemas" in s:
                reasons.append(f"Public schema definition modified: {s}")
            elif "money" in s:
                reasons.append(f"Financial arithmetic rule modified: {s}")
            elif "repository" in s:
                reasons.append(f"Persistence and idempotency store modified: {s}")

    # Check for coverage gaps or unresolved edges
    if graph.unresolved_items:
        severities.append(RiskSeverity.HIGH)
        reasons.append(f"Unresolved dynamic features or coverage gaps: {len(graph.unresolved_items)}")

    # Check for shared helpers affecting multiple entry points
    entry_callers = {s for s in impacted_symbols if "routes:" in s or "worker:" in s}
    if len(entry_callers) > 1:
        severities.append(RiskSeverity.MEDIUM)
        reasons.append(
            f"Shared component impacts multiple entry paths: {sorted(entry_callers)}"
        )

    # Mandatory reason for global integrity checks
    reasons.append("Mandatory global integrity checks included per runtime policy")

    max_severity = max(severities, key=lambda s: _SEVERITY_ORDER[s])

    return ImpactReport(
        changed_symbols=sorted(changed_syms),
        impacted_symbols=sorted(impacted_symbols),
        impacted_contracts=sorted(impacted_contracts),
        selected_checks=sorted(selected_checks),
        risk_severity=max_severity,
        risk_reasons=reasons,
        coverage_status=graph.coverage.get("status", "PARTIAL"),
    )
