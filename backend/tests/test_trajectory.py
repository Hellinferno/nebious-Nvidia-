"""Trajectory fingerprint, no-progress stop, and bounded recovery tests (B-15/W8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api.main import app, settings
from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord
from benchproof.fixtures import source_hash
from benchproof.investigation import run_investigation
from benchproof.storage import get_audit, list_actions, migrate, save_audit
from benchproof.storage.lifecycle import list_events, migrate_lifecycle
from benchproof.trajectory import (
    RECOVERY_STRATEGY,
    STALL_REPEAT_THRESHOLD,
    TrajectoryError,
    classify_trace,
    recovery_state,
    reserve_recovery,
)
from benchproof.trajectory.development import development_traces


@pytest.mark.parametrize("trace", development_traces(), ids=lambda trace: trace["trace_id"])
def test_eight_labeled_development_traces(trace: dict) -> None:
    result = classify_trace(trace["steps"])
    assert result["classification"] == trace["label"]
    assert result["stall_index"] == (1 if trace["label"] == "STALLED" else None)
    assert result["repeat_threshold"] == STALL_REPEAT_THRESHOLD


def test_executed_recovery_preserves_counters_and_second_stall_blocks(tmp_path: Path) -> None:
    db = tmp_path / "trajectory.db"
    migrate(db)
    migrate_lifecycle(db)
    audit_id = "audit-executed-recovery"
    original_limits = {
        "max_actions": 6,
        "max_patches": 2,
        "process_timeout_s": 60,
        "audit_deadline_s": 300,
    }
    save_audit(
        AuditRecord(
            audit_id=audit_id,
            owner_ref="test-owner",
            fixture_id="MC-01",
            source_hash=source_hash("MC-01"),
            contract_hash=contract_hash(),
            mode="mock",
            limits=original_limits,
        ),
        db,
    )

    first = run_investigation("MC-01", audit_id, mode="mock", db_path=db)
    second = run_investigation("MC-01", audit_id, mode="mock", db_path=db)
    assert first["trajectory"]["outcome"] == "PROGRESSING"
    assert second["trajectory"]["outcome"] == "STALLED"
    assert get_audit(audit_id, db)["run_state"] == "STALLED"
    assert len(list_actions(audit_id, db)) == 2

    reserved = reserve_recovery(audit_id, db)
    assert reserved["recovery_count"] == 1
    assert reserved["remaining_limits"]["used_actions"] == 2
    assert json.loads(get_audit(audit_id, db)["limits_json"]) == original_limits

    recovered = run_investigation(
        "MC-01",
        audit_id,
        mode="mock",
        strategy=RECOVERY_STRATEGY,
        db_path=db,
    )
    assert recovered["trajectory"]["outcome"] == "PROGRESSING"
    assert recovered["strategy"] == RECOVERY_STRATEGY
    assert recovery_state(audit_id, db)["remaining_limits"]["used_actions"] == 3

    second_recovery_attempt = run_investigation(
        "MC-01",
        audit_id,
        mode="mock",
        strategy=RECOVERY_STRATEGY,
        db_path=db,
    )
    assert second_recovery_attempt["trajectory"]["outcome"] == "BLOCKED"
    assert get_audit(audit_id, db)["run_state"] == "BLOCKED"
    assert recovery_state(audit_id, db)["remaining_limits"]["used_actions"] == 4

    with pytest.raises(TrajectoryError) as exc_info:
        reserve_recovery(audit_id, db)
    assert exc_info.value.code in {"INVALID_STATE", "RECOVERY_EXHAUSTED"}
    event_types = [event["event_type"] for event in list_events(audit_id, db_path=db)]
    assert event_types.count("stalled") == 2
    assert "recovery_started" in event_types
    assert "blocked" in event_types


def test_api_exposes_stall_and_runs_only_one_recovery(tmp_path: Path) -> None:
    settings.database_path = str(tmp_path / "trajectory-api.db")
    with TestClient(app) as client:
        client.headers.update({"X-BenchProof-Owner": "trajectory-owner"})
        created = client.post("/api/v1/audits", json={"fixture_id": "MC-01", "mode": "mock"})
        assert created.status_code == 201
        audit_id = created.json()["audit_id"]

        assert client.post(f"/api/v1/audits/{audit_id}/diagnose").status_code == 200
        repeated = client.post(f"/api/v1/audits/{audit_id}/diagnose")
        assert repeated.status_code == 200
        assert repeated.json()["trajectory"]["outcome"] == "STALLED"

        status = client.get(f"/api/v1/audits/{audit_id}/trajectory")
        assert status.status_code == 200
        assert status.json()["run_state"] == "STALLED"
        assert status.json()["recovery_count"] == 0

        recovered = client.post(f"/api/v1/audits/{audit_id}/recover")
        assert recovered.status_code == 200
        assert recovered.json()["result"]["strategy"] == RECOVERY_STRATEGY
        assert recovered.json()["result"]["trajectory"]["recovery_count"] == 1

        refused = client.post(f"/api/v1/audits/{audit_id}/recover")
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == "INVALID_STATE"


def test_original_action_cap_blocks_without_reset(tmp_path: Path) -> None:
    db = tmp_path / "budget.db"
    migrate(db)
    migrate_lifecycle(db)
    audit_id = "audit-action-cap"
    save_audit(
        AuditRecord(
            audit_id=audit_id,
            owner_ref="test-owner",
            fixture_id="MC-01",
            source_hash=source_hash("MC-01"),
            contract_hash=contract_hash(),
            mode="mock",
            limits={
                "max_actions": 1,
                "max_patches": 2,
                "process_timeout_s": 60,
                "audit_deadline_s": 300,
            },
        ),
        db,
    )
    run_investigation("MC-01", audit_id, mode="mock", db_path=db)
    with pytest.raises(TrajectoryError) as exc_info:
        run_investigation("MC-01", audit_id, mode="mock", db_path=db)
    assert exc_info.value.code == "BUDGET_EXHAUSTED"
    assert len(list_actions(audit_id, db)) == 1
    assert get_audit(audit_id, db)["run_state"] == "BLOCKED"
    assert "budget_exhausted" in [
        event["event_type"] for event in list_events(audit_id, db_path=db)
    ]
