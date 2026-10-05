"""Day 3 API behavior: idempotent creation, contract pin, resumable events, CAS cancel."""

from __future__ import annotations

from fastapi.testclient import TestClient

from benchproof.constraints import contract_hash


def test_idempotent_replay_returns_same_audit_without_duplicate_work(client: TestClient) -> None:
    body = {"fixture_id": "MC-01", "mode": "mock"}
    a = client.post("/api/v1/audits", json=body, headers={"Idempotency-Key": "k1"})
    b = client.post("/api/v1/audits", json=body, headers={"Idempotency-Key": "k1"})
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["audit_id"] == b.json()["audit_id"]
    assert b.headers.get("Idempotent-Replay") == "true"
    assert len(client.get("/api/v1/audits").json()) == 1
    events = client.get(f"/api/v1/audits/{a.json()['audit_id']}/events").json()["events"]
    assert [e["event_type"] for e in events] == ["audit_created"]  # created exactly once


def test_same_key_different_body_is_conflict(client: TestClient) -> None:
    client.post("/api/v1/audits", json={"fixture_id": "MC-01"}, headers={"Idempotency-Key": "k2"})
    r = client.post("/api/v1/audits", json={"fixture_id": "AC-01"}, headers={"Idempotency-Key": "k2"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert len(client.get("/api/v1/audits").json()) == 1


def test_without_key_each_post_creates_a_new_audit(client: TestClient) -> None:
    client.post("/api/v1/audits", json={"fixture_id": "MC-01"})
    client.post("/api/v1/audits", json={"fixture_id": "MC-01"})
    assert len(client.get("/api/v1/audits").json()) == 2


def test_contract_pin_must_match_accepted_version(client: TestClient) -> None:
    bad = client.post("/api/v1/audits", json={"fixture_id": "MC-01", "contract_hash": "f" * 64})
    assert bad.status_code == 409
    assert bad.json()["detail"]["code"] == "CONTRACT_UNAPPROVED"
    good = client.post("/api/v1/audits", json={"fixture_id": "MC-01", "contract_hash": contract_hash()})
    assert good.status_code == 201


def test_events_are_ordered_and_resumable(client: TestClient) -> None:
    audit_id = client.post("/api/v1/audits", json={"fixture_id": "AC-01"}).json()["audit_id"]
    assert client.post(f"/api/v1/audits/{audit_id}/cancel").status_code == 200
    full = client.get(f"/api/v1/audits/{audit_id}/events").json()
    assert full["run_state"] == "CANCELLED"
    assert [e["event_type"] for e in full["events"]] == ["audit_created", "state_changed", "cancelled"]
    assert [e["sequence"] for e in full["events"]] == [1, 2, 3]
    resumed = client.get(f"/api/v1/audits/{audit_id}/events?after=1").json()["events"]
    assert [e["sequence"] for e in resumed] == [2, 3]
    via_header = client.get(f"/api/v1/audits/{audit_id}/events", headers={"Last-Event-ID": "2"}).json()["events"]
    assert [e["sequence"] for e in via_header] == [3]
    assert client.get("/api/v1/audits/audit-nope/events").status_code == 404


def test_sse_stream_replays_and_ends_on_terminal_state(client: TestClient) -> None:
    audit_id = client.post("/api/v1/audits", json={"fixture_id": "AC-01"}).json()["audit_id"]
    client.post(f"/api/v1/audits/{audit_id}/cancel")
    with client.stream(
        "GET", f"/api/v1/audits/{audit_id}/events", headers={"Accept": "text/event-stream", "Last-Event-ID": "1"}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        text = "".join(r.iter_text())
    assert "id: 1\n" not in text  # resumed after sequence 1
    assert "id: 2\nevent: state_changed" in text
    assert "id: 3\nevent: cancelled" in text
    assert "event: end" in text


def test_cancel_is_compare_and_swap(client: TestClient) -> None:
    audit_id = client.post("/api/v1/audits", json={"fixture_id": "AC-01"}).json()["audit_id"]
    assert client.post(f"/api/v1/audits/{audit_id}/cancel").status_code == 200
    again = client.post(f"/api/v1/audits/{audit_id}/cancel")
    assert again.status_code == 409
    events = client.get(f"/api/v1/audits/{audit_id}/events").json()["events"]
    assert sum(e["event_type"] == "cancelled" for e in events) == 1


def test_ready_reports_runner_mode_without_probing_docker(client: TestClient) -> None:
    runner = client.get("/api/v1/ready").json()["runner"]
    assert runner["mode"] == "mock"
    assert runner["isolated_execution_available"] is False
