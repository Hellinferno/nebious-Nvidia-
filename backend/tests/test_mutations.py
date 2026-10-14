"""Day 12 / B-16 trusted semantic mutation strength tests."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api import main as api_main
from benchproof.bundle import export_bundle
from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord, MutationOutcome
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.gate import verify_candidate_app
from benchproof.mutations import (
    TEMPLATES,
    MutationError,
    MutationTemplate,
    Replacement,
    execute_mutant,
    run_mutation_assessment,
    template_registry,
)
from benchproof.storage import list_mutation_assessments, migrate, save_audit
from benchproof.trajectory import budget_snapshot


def _clean_audit(db: Path, *, max_executions: int = 12) -> AuditRecord:
    app_dir = fixture_dir("clean-service") / "app"
    audit = AuditRecord(
        audit_id="audit-mutation-clean",
        owner_ref="test-owner",
        fixture_id="clean-service",
        source_hash=source_hash_for_dir(app_dir),
        contract_hash=contract_hash(),
        limits={
            "max_actions": 15,
            "max_patches": 5,
            "max_executions": max_executions,
            "process_timeout_s": 60,
            "audit_deadline_s": 300,
        },
    )
    save_audit(audit, db)
    return audit


def test_registry_has_three_versioned_templates_per_family() -> None:
    registry = template_registry()
    assert len(registry) == 12
    assert len({item["template_id"] for item in registry}) == 12
    for family in ("api", "amount", "caller", "idempotency"):
        selected = [item for item in registry if item["family"] == family]
        assert len(selected) == 3
        assert all(item["version"] == 1 for item in selected)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda item: item.template_id)
def test_all_trusted_templates_are_applicable_executable_and_semantic(
    template: MutationTemplate,
) -> None:
    accepted = fixture_dir("clean-service") / "app"
    baseline = verify_candidate_app(accepted)
    assert baseline["verdict"] == "VERIFIED"
    baseline_checks = {item["check_id"]: item["outcome"] for item in baseline["checks"]}
    base_hash = source_hash_for_dir(accepted)

    result = execute_mutant(accepted, template, baseline_checks)

    assert result.base_candidate_hash == base_hash
    assert result.mutant_hash and result.mutant_hash != base_hash
    assert result.validity == "valid"
    assert result.outcome in {MutationOutcome.KILLED, MutationOutcome.SURVIVED}
    if template.template_id == "idempotency-drop-tenant-key":
        assert result.outcome == MutationOutcome.SURVIVED
    assert source_hash_for_dir(accepted) == base_hash


def test_invalid_syntax_is_invalid_not_killed() -> None:
    accepted = fixture_dir("clean-service") / "app"
    baseline = verify_candidate_app(accepted)
    baseline_checks = {item["check_id"]: item["outcome"] for item in baseline["checks"]}
    invalid = MutationTemplate(
        template_id="test-invalid-syntax",
        version=1,
        family="idempotency",
        intended_behavior="Test-only malformed branch.",
        supporting_check_ids=("idempotency-duplicate",),
        replacements=(
            Replacement(
                "repository.py",
                "return _store.get(tenant_id, {}).get(request_id)",
                "return (",
            ),
        ),
    )

    result = execute_mutant(accepted, invalid, baseline_checks)

    assert result.validity == "invalid_syntax"
    assert result.outcome == MutationOutcome.INVALID


def test_bounded_run_reports_survivor_preserves_candidate_and_consumes_budget(tmp_path: Path) -> None:
    db = tmp_path / "mutation.db"
    migrate(db)
    audit = _clean_audit(db, max_executions=4)
    original_hash = audit.source_hash

    run = run_mutation_assessment(audit.audit_id, max_mutants=3, db_path=db)

    assert run["strength_status"] == "WEAK"
    assert run["policy"] == "OPTIONAL"
    assert run["counts"] == {"killed": 2, "survived": 1, "invalid": 0, "skipped": 0, "unknown": 0}
    assert run["execution_count"] == 4
    assert run["candidate_unchanged"] is True
    assert run["base_candidate_hash"] == original_hash == run["final_candidate_hash"]
    assert len(run["template_versions"]) == 3
    assert list_mutation_assessments(audit.audit_id, db)[0]["counts"] == run["counts"]
    assert budget_snapshot(audit.audit_id, db)["used_executions"] == 4
    assert budget_snapshot(audit.audit_id, db)["max_executions"] == 0
    with sqlite3.connect(db) as conn, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        conn.execute(
            "UPDATE mutation_results SET outcome='KILLED' WHERE mutation_run_id=?",
            (run["mutation_run_id"],),
        )
    with pytest.raises(MutationError, match="executions") as exhausted:
        run_mutation_assessment(audit.audit_id, max_mutants=1, db_path=db)
    assert exhausted.value.code == "BUDGET_EXHAUSTED"


def test_mutation_api_is_owner_scoped_and_bundle_exports_real_results(
    client: TestClient, tmp_path: Path
) -> None:
    created = client.post(
        "/api/v1/audits",
        json={"fixture_id": "clean-service", "mode": "mock"},
        headers={"Idempotency-Key": "mutation-api"},
    )
    assert created.status_code == 201
    audit_id = created.json()["audit_id"]
    from benchproof.gate import execute_acceptance_gate

    assert execute_acceptance_gate(
        audit_id,
        db_path=Path(api_main.settings.database_path),
    )["verdict"] == "VERIFIED"

    blocked = client.post(
        f"/api/v1/audits/{audit_id}/mutations",
        json={"patch_id": None, "max_mutants": 3},
    )
    assert blocked.status_code == 503
    assert blocked.json()["detail"]["code"] == "RUNNER_UNAVAILABLE"
    response = run_mutation_assessment(
        audit_id,
        max_mutants=3,
        db_path=Path(api_main.settings.database_path),
    )
    assert response["strength_status"] == "WEAK"
    ledger = client.get(f"/api/v1/audits/{audit_id}/mutations")
    assert ledger.json()["status"] == "WEAK"
    denied = client.get(
        f"/api/v1/audits/{audit_id}/mutations",
        headers={"X-BenchProof-Owner": "other-owner"},
    )
    assert denied.status_code == 403
    denied_run = client.post(
        f"/api/v1/audits/{audit_id}/mutations",
        json={"patch_id": None, "max_mutants": 1},
        headers={"X-BenchProof-Owner": "other-owner"},
    )
    assert denied_run.status_code == 403

    bundle, manifest = export_bundle(
        audit_id,
        output_path=tmp_path / "mutation-evidence.zip",
        db_path=Path(api_main.settings.database_path),
    )
    if not bundle.exists():
        pytest.fail("bundle was not created")
    assert "P1-mutations" not in manifest.omissions
    with zipfile.ZipFile(bundle) as archive:
        payload = json.loads(archive.read("mutations.json"))
    assert payload["status"] == "WEAK"
    assert payload["runs"][-1]["counts"]["survived"] == 1
