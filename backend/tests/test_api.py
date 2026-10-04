from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api import main as api_main
from benchproof.constraints import contract_hash
from benchproof.storage.heartbeat import record_heartbeat


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["runner"] == "mock"
    assert "nebius" not in str(body).lower()  # no credentials or provider detail


def test_ready_reports_unconfigured_provider_without_billing(client: TestClient) -> None:
    r = client.get("/api/v1/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] is True
    assert body["contract_hash"] == contract_hash()
    assert body["provider"]["configured"] is False
    assert body["provider"]["model_id"] is None
    assert body["runner"]["isolated_execution_available"] is False
    assert body["worker"]["alive"] is False
    assert body["fixtures"] == 5


def test_ready_sees_worker_heartbeat(client: TestClient) -> None:
    record_heartbeat("worker-test", "mock", Path(api_main.settings.database_path))
    body = client.get("/api/v1/ready").json()
    assert body["worker"]["alive"] is True
    assert body["worker"]["heartbeat"]["worker_id"] == "worker-test"


def test_examples_expose_public_fields_only(client: TestClient) -> None:
    r = client.get("/api/v1/examples")
    assert r.status_code == 200
    examples = r.json()
    ids = {e["id"] for e in examples}
    assert ids == {"AC-01", "MC-01", "CI-01", "ID-01", "clean-service"}
    for e in examples:
        assert len(e["source_hash"]) == 64
        assert e["synthetic"] is True
        # trusted evaluator fields must never be served
        assert "intended_failing_checks" not in e
        assert "expected_verdict" not in e
        assert "reference_repair" not in e


def test_constraints_listed_and_fetchable(client: TestClient) -> None:
    listed = client.get("/api/v1/constraints").json()
    assert {c["constraint_id"] for c in listed} == {"C-API", "C-AMOUNT", "C-INTEGRITY"}
    one = client.get("/api/v1/constraints/C-AMOUNT")
    assert one.status_code == 200
    assert one.json()["hash"]
    alias = client.get("/api/v1/contracts/C-AMOUNT")
    assert alias.json() == one.json()
    assert client.get("/api/v1/constraints/C-NOPE").status_code == 404


def test_create_audit_mock_mode_pins_hashes(client: TestClient) -> None:
    example = next(e for e in client.get("/api/v1/examples").json() if e["id"] == "MC-01")
    r = client.post("/api/v1/audits", json={"fixture_id": "MC-01", "mode": "mock"})
    assert r.status_code == 201
    audit = r.json()
    assert audit["source_hash"] == example["source_hash"]
    assert audit["contract_hash"] == contract_hash()
    assert audit["run_state"] == "QUEUED"
    assert audit["gate_verdict"] == "PENDING"
    assert audit["mode"] == "mock"

    fetched = client.get(f"/api/v1/audits/{audit['audit_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["fixture_id"] == "MC-01"
    assert any(a["audit_id"] == audit["audit_id"] for a in client.get("/api/v1/audits").json())


def test_live_mode_refused_without_provider(client: TestClient) -> None:
    r = client.post("/api/v1/audits", json={"fixture_id": "MC-01", "mode": "live"})
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    assert client.get("/api/v1/audits").json() == []  # nothing silently created as mock


def test_live_mode_allowed_when_provider_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_main.settings, "nebius_api_key", "test-key-not-real")
    monkeypatch.setattr(api_main.settings, "nebius_model_id", "nvidia/test-model")
    r = client.post("/api/v1/audits", json={"fixture_id": "clean-service", "mode": "live"})
    assert r.status_code == 201
    assert r.json()["mode"] == "live"


def test_stale_source_pin_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/v1/audits", json={"fixture_id": "AC-01", "mode": "mock", "source_hash": "0" * 64}
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "STALE_SOURCE"


def test_unknown_or_unsafe_fixture_rejected(client: TestClient) -> None:
    assert client.post("/api/v1/audits", json={"fixture_id": "nope", "mode": "mock"}).status_code == 404
    assert client.post("/api/v1/audits", json={"fixture_id": "../x", "mode": "mock"}).status_code == 404
    assert client.post("/api/v1/audits", json={"fixture_id": "AC-01", "mode": "demo"}).status_code == 422


def test_cancel_transitions_once(client: TestClient) -> None:
    audit_id = client.post("/api/v1/audits", json={"fixture_id": "AC-01"}).json()["audit_id"]
    assert client.post(f"/api/v1/audits/{audit_id}/cancel").status_code == 200
    assert client.get(f"/api/v1/audits/{audit_id}").json()["run_state"] == "CANCELLED"
    again = client.post(f"/api/v1/audits/{audit_id}/cancel")
    assert again.status_code == 409
    assert client.post("/api/v1/audits/audit-missing/cancel").status_code == 404
