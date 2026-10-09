"""Tests for blast radius, reverse traversal and deterministic risk (B-08)."""


from benchproof.constraints import contract_hash
from benchproof.fixtures import fixture_dir
from benchproof.graph.builder import build_state_graph
from benchproof.impact import RiskSeverity, analyze_impact
from benchproof.impact.context import build_context_packet


def test_impact_analysis_money_symbol():
    app_dir = fixture_dir("clean-service") / "app"
    graph = build_state_graph(app_dir, contract_hash())

    # If app.money:compute_total changed
    report = analyze_impact(graph, changed_symbols=["app.money:compute_total"])

    # Reverse callers must include process_invoice and routes/worker
    assert "app.money:compute_total" in report.changed_symbols
    assert "app.services:process_invoice" in report.impacted_symbols
    assert "app.routes:submit_invoice" in report.impacted_symbols

    # Contracts and checks
    assert "C-AMOUNT" in report.impacted_contracts
    assert "amount-boundary" in report.selected_checks

    # Mandatory global integrity checks
    assert "api-field-presence" in report.selected_checks
    assert "caller-consistency" in report.selected_checks

    # Risk level must be HIGH because money rule changed
    assert report.risk_severity == RiskSeverity.HIGH
    assert any("Financial arithmetic rule modified" in r for r in report.risk_reasons)
    assert any("Shared component impacts multiple entry paths" in r for r in report.risk_reasons)


def test_impact_analysis_critical_path():
    app_dir = fixture_dir("clean-service") / "app"
    graph = build_state_graph(app_dir, contract_hash())

    report = analyze_impact(graph, changed_files=["launcher/observe_invoice.py"])
    assert report.risk_severity == RiskSeverity.CRITICAL
    assert any("Protected evaluator/launcher file modified" in r for r in report.risk_reasons)


def test_build_context_packet():
    app_dir = fixture_dir("clean-service") / "app"
    graph = build_state_graph(app_dir, contract_hash())
    report = analyze_impact(graph, changed_symbols=["app.money:compute_total"])

    packet = build_context_packet(app_dir, graph, report)
    assert len(packet.context_hash) == 64
    assert packet.source_hash == graph.source_hash
    assert packet.contract_hash == graph.contract_hash
    assert packet.graph_hash == graph.graph_hash
    assert "app/money.py" in packet.excerpts
    assert "amount-boundary" in packet.selected_checks
