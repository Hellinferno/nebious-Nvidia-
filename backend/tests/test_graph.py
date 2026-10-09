"""Tests for engineering-state graph building, coverage and hashing (B-07)."""

from pathlib import Path

from benchproof.constraints import contract_hash
from benchproof.fixtures import fixture_dir
from benchproof.graph.builder import build_state_graph


def test_clean_service_graph():
    app_dir = fixture_dir("clean-service") / "app"
    chash = contract_hash()
    graph = build_state_graph(app_dir, chash)

    assert graph.builder_version == "0.2.0"
    assert graph.coverage["status"] == "COMPLETE_FOR_DECLARED_SCOPE"
    assert graph.coverage["missing_mappings"] == 0
    assert len(graph.nodes) > 20
    assert len(graph.edges) > 20

    # Verify key nodes exist
    assert "file:app/routes.py" in graph.nodes
    assert "symbol:app.money:compute_total" in graph.nodes
    assert "symbol:app.services:process_invoice" in graph.nodes
    assert "contract:C-AMOUNT" in graph.nodes
    assert "test:amount-boundary" in graph.nodes

    # Verify key edges exist
    edge_types = {(e.from_node, e.to_node, e.edge_type) for e in graph.edges}
    assert ("file:app/money.py", "symbol:app.money:compute_total", "defines") in edge_types
    assert ("symbol:app.services:process_invoice", "symbol:app.money:compute_total", "calls") in edge_types
    assert ("symbol:app.money:compute_total", "contract:C-AMOUNT", "implements") in edge_types
    assert ("contract:C-AMOUNT", "test:amount-boundary", "protected_by") in edge_types


def test_graph_hash_deterministic():
    app_dir = fixture_dir("clean-service") / "app"
    chash = contract_hash()
    g1 = build_state_graph(app_dir, chash)
    g2 = build_state_graph(app_dir, chash)
    assert g1.graph_hash == g2.graph_hash
    assert len(g1.graph_hash) == 64


def test_dynamic_feature_yields_partial_coverage(tmp_path: Path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "dynamic.py").write_text("import importlib\ndef run(name):\n    return eval(name)\n", encoding="utf-8")

    graph = build_state_graph(app_dir, contract_hash())
    assert graph.coverage["status"] == "PARTIAL"
    assert any("Dynamic call: eval" in item for item in graph.unresolved_items)
    assert any("Dynamic module import: importlib" in item for item in graph.unresolved_items)


def test_missing_declared_symbol_flagged(tmp_path: Path):
    # App missing compute_total
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "dummy.py").write_text("def foo(): return 1\n", encoding="utf-8")

    graph = build_state_graph(app_dir, contract_hash())
    assert graph.coverage["status"] == "PARTIAL"
    assert any("Missing declared symbol for contract C-AMOUNT: app.money:compute_total" in item for item in graph.unresolved_items)
