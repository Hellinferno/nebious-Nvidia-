"""API tests for Day 6 (B-09 restricted patch authoring, B-10 acceptance gate)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from benchproof.api import main as api_main
from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.patch import (
    get_canonical_mc01_repair_diff,
)
from benchproof.storage import save_audit


def test_api_patch_and_verify_cycle(client: TestClient) -> None:
    db = Path(api_main.settings.database_path)

    # 1. Create audit for MC-01
    shash = source_hash_for_dir(fixture_dir("MC-01") / "app")
    aid = "audit-api-mc01"
    rec = AuditRecord(
        audit_id=aid,
        owner_ref="test-owner",
        fixture_id="MC-01",
        source_hash=shash,
        contract_hash=contract_hash(),
    )
    save_audit(rec, db_path=db)


    # 2. Try proposing a patch with wrong base hash -> 409
    bad_res = client.post(
        f"/api/v1/audits/{aid}/patch",
        json={
            "diff": get_canonical_mc01_repair_diff(),
            "base_source_hash": "wrong-hash",
            "target_files": ["app/money.py"],
        },
    )
    assert bad_res.status_code == 409
    assert bad_res.json()["detail"]["code"] == "PATCH_BASE_MISMATCH"


    # 3. Propose valid canonical patch -> 200 APPROVED
    good_diff = get_canonical_mc01_repair_diff()
    good_res = client.post(
        f"/api/v1/audits/{aid}/patch",
        json={
            "diff": good_diff,
            "base_source_hash": shash,
            "target_files": ["app/money.py"],
            "explanation": "Sum unrounded line items before rounding invoice total",
        },
    )
    assert good_res.status_code == 200
    patch_data = good_res.json()
    assert patch_data["policy_result"] == "APPROVED"
    patch_id = patch_data["patch_id"]

    # 4. List patches
    plist = client.get(f"/api/v1/audits/{aid}/patches").json()
    assert len(plist) == 1
    assert plist[0]["patch_id"] == patch_id

    # 5. Execute acceptance gate verification
    verify_res = client.post(
        f"/api/v1/audits/{aid}/verify",
        json={"patch_id": patch_id, "use_docker": False},
    )
    assert verify_res.status_code == 200
    gate_data = verify_res.json()
    assert gate_data["verdict"] == "VERIFIED"
    assert gate_data["failing_checks"] == []
    assert "amount-boundary" in gate_data["passing_checks"]

    # 6. Check gate status endpoint
    status_res = client.get(f"/api/v1/audits/{aid}/gate").json()
    assert status_res["gate_verdict"] == "VERIFIED"
    assert status_res["run_state"] == "COMPLETED"
    assert len(status_res["checks"]) >= 6

