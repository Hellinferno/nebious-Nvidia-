"""Connected-journey and reliability boundaries for B-12/B-13."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from benchproof.api import main as api_main
from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord, RunState
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.patch import get_canonical_mc01_repair_diff
from benchproof.storage import get_audit, save_audit, save_patch
from benchproof.storage.lifecycle import reconcile_cancellation


def _create(client: TestClient, fixture_id: str, key: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/audits",
        json={"fixture_id": fixture_id, "mode": "mock"},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 201
    return response.json()


def test_owner_isolation_covers_runs_events_patches_and_bundles(client: TestClient) -> None:
    audit = _create(client, "MC-01", "owner-boundary")
    audit_id = str(audit["audit_id"])
    source_hash = str(audit["source_hash"])
    patch_response = client.post(
        f"/api/v1/audits/{audit_id}/patch",
        json={
            "diff": get_canonical_mc01_repair_diff(),
            "base_source_hash": source_hash,
            "target_files": ["app/money.py"],
        },
    )
    assert patch_response.status_code == 200
    patch_id = patch_response.json()["patch_id"]

    intruder = {"X-BenchProof-Owner": "other-owner"}
    protected = [
        ("get", f"/api/v1/audits/{audit_id}"),
        ("get", f"/api/v1/audits/{audit_id}/events"),
        ("get", f"/api/v1/audits/{audit_id}/patches"),
        ("get", f"/api/v1/patches/{patch_id}"),
        ("get", f"/api/v1/audits/{audit_id}/bundle?metadata=true"),
    ]
    for method, path in protected:
        response = client.request(method, path, headers=intruder)
        assert response.status_code == 403, path
        assert response.json()["detail"]["code"] == "OWNER_DENIED"

    assert client.get("/api/v1/audits", headers=intruder).json() == []


def test_reload_snapshot_and_cursor_resume_do_not_create_a_second_audit(client: TestClient) -> None:
    first = _create(client, "AC-01", "stable-create-key")
    replay = _create(client, "AC-01", "stable-create-key")
    assert replay["audit_id"] == first["audit_id"]
    assert len(client.get("/api/v1/audits").json()) == 1

    audit_id = str(first["audit_id"])
    assert client.post(f"/api/v1/audits/{audit_id}/cancel").status_code == 200
    resumed = client.get(
        f"/api/v1/audits/{audit_id}/events",
        headers={"Last-Event-ID": "1"},
    ).json()
    assert [event["sequence"] for event in resumed["events"]] == [2, 3]
    assert resumed["run_state"] == "CANCELLED"


def test_remote_cancel_stays_pending_until_worker_reconciles(client: TestClient) -> None:
    db = Path(api_main.settings.database_path)
    audit_id = "audit-remote-cancel"
    save_audit(
        AuditRecord(
            audit_id=audit_id,
            owner_ref="test-owner",
            fixture_id="MC-01",
            source_hash=source_hash_for_dir(fixture_dir("MC-01") / "app"),
            contract_hash=contract_hash(),
            run_state=RunState.INVESTIGATING,
            reservations={"remote_run_id": "remote-123"},
        ),
        db_path=db,
    )

    pending = client.post(f"/api/v1/audits/{audit_id}/cancel")
    assert pending.status_code == 202
    assert pending.json()["status"] == "cancel_pending"
    assert get_audit(audit_id, db)["run_state"] == "CANCEL_PENDING"

    repeated = client.post(f"/api/v1/audits/{audit_id}/cancel")
    assert repeated.status_code == 202
    events = client.get(f"/api/v1/audits/{audit_id}/events").json()["events"]
    assert sum(event["event_type"] == "cancel_pending" for event in events) == 1

    assert reconcile_cancellation(audit_id, remote_terminated=False, db_path=db) is False
    assert get_audit(audit_id, db)["run_state"] == "CANCEL_PENDING"
    assert reconcile_cancellation(audit_id, remote_terminated=True, db_path=db) is True
    assert get_audit(audit_id, db)["run_state"] == "CANCELLED"


def test_patch_from_another_owned_audit_cannot_be_verified(client: TestClient) -> None:
    db = Path(api_main.settings.database_path)
    first = _create(client, "MC-01", "patch-parent-a")
    second = _create(client, "MC-01", "patch-parent-b")
    patch_id = "patch-wrong-parent"
    save_patch(
        patch_id=patch_id,
        audit_id=str(first["audit_id"]),
        base_hash=str(first["source_hash"]),
        diff_hash="d" * 64,
        diff_text=get_canonical_mc01_repair_diff(),
        approved_paths=["app/money.py"],
        changed_lines=8,
        db_path=db,
    )

    response = client.post(
        f"/api/v1/audits/{second['audit_id']}/verify",
        json={"patch_id": patch_id, "use_docker": False},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PATCH_NOT_FOUND"
