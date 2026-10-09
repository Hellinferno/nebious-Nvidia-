"""Tests for Day 4 and Day 5 API endpoints (graph, impact, diagnose, actions)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api.main import app, settings
from benchproof.storage import migrate
from benchproof.storage.lifecycle import migrate_lifecycle


@pytest.fixture
def client(tmp_path: Path):
    db = tmp_path / "test.db"
    settings.database_path = str(db)
    migrate(db)
    migrate_lifecycle(db)
    with TestClient(app) as c:
        yield c


def test_api_graph_and_impact_endpoints(client: TestClient):
    # 1. Create audit
    r = client.post("/api/v1/audits", json={"fixture_id": "MC-01", "mode": "mock"})
    assert r.status_code == 201
    audit_id = r.json()["audit_id"]

    # 2. GET /graph
    r_graph = client.get(f"/api/v1/audits/{audit_id}/graph")
    assert r_graph.status_code == 200
    g_data = r_graph.json()
    assert "graph_hash" in g_data
    assert len(g_data["graph_hash"]) == 64
    assert g_data["coverage"]["status"] == "COMPLETE_FOR_DECLARED_SCOPE"

    # 3. GET /impact
    r_imp = client.get(f"/api/v1/audits/{audit_id}/impact")
    assert r_imp.status_code == 200
    imp_data = r_imp.json()
    assert imp_data["risk_severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert "amount-boundary" in imp_data["selected_checks"]
    assert len(imp_data["risk_reasons"]) > 0


def test_api_diagnose_and_actions_endpoints(client: TestClient):
    # 1. Create audit
    r = client.post("/api/v1/audits", json={"fixture_id": "clean-service", "mode": "mock"})
    assert r.status_code == 201
    audit_id = r.json()["audit_id"]

    # 2. POST /diagnose
    r_diag = client.post(f"/api/v1/audits/{audit_id}/diagnose")
    assert r_diag.status_code == 200
    d_data = r_diag.json()
    assert d_data["action_id"].startswith("act-")
    assert "hypotheses_evaluation" in d_data
    assert len(d_data["hypotheses_evaluation"]) >= 1

    # 3. GET /actions
    r_act = client.get(f"/api/v1/audits/{audit_id}/actions")
    assert r_act.status_code == 200
    actions = r_act.json()
    assert len(actions) >= 1
    assert actions[0]["action_id"] == d_data["action_id"]
    assert actions[0]["role"] == "investigator"
