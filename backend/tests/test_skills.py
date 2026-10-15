"""B-22: bounded skill catalog. Availability is computed server-side from the audit record,
the runtime snapshot and the remaining budgets; the catalog never grants anything."""

from __future__ import annotations

from fastapi.testclient import TestClient

from benchproof.api import main as api_main
from benchproof.skills import (
    SKILLS,
    SKILLS_VERSION,
    Skill,
    catalog,
    describe,
    evaluate_availability,
)

RUNTIME_OFF = {"provider": {"configured": False}, "runner": {"isolated_execution_available": False}}
RUNTIME_ON = {"provider": {"configured": True}, "runner": {"isolated_execution_available": True}}


def _audit(**overrides: object) -> dict:
    base = {
        "audit_id": "audit-1", "fixture_id": "MC-01", "mode": "mock", "run_state": "QUEUED",
        "gate_verdict": "PENDING", "limits_json": "{}", "reservations": "{}",
    }
    return {**base, **overrides}


def _by_id(entries: list[dict]) -> dict[str, dict]:
    return {entry["skill_id"]: entry for entry in entries}


def test_catalog_is_versioned_unique_and_maps_to_registered_routes() -> None:
    entries = catalog()
    assert SKILLS_VERSION == "skills-v1" and len(entries) == 12
    assert len({e["skill_id"] for e in entries}) == 12 and len({e["slash"] for e in entries}) == 12
    assert all(e["slash"].startswith("/") for e in entries)
    routes = {(method, route.path) for route in api_main.app.routes for method in getattr(route, "methods", set())}
    for skill in SKILLS:
        assert (skill.method, skill.endpoint.split("?", 1)[0]) in routes, skill.skill_id
        assert set(skill.costs) <= {"model-call", "isolated-execution", "none"}
        assert skill.category in {"session", "run", "investigate", "repair", "evidence"}


def test_without_an_audit_only_session_skills_are_available() -> None:
    by_id = _by_id(describe(audit=None, runtime=RUNTIME_OFF))
    assert by_id["start"]["available"] and by_id["refresh-readiness"]["available"]
    assert not by_id["diagnose"]["available"]
    assert by_id["diagnose"]["blocked_reason"] == "Start or restore an audit first."
    assert by_id["diagnose"]["endpoint"] == "/api/v1/audits/{audit_id}/diagnose"  # template until an audit exists


def test_availability_follows_the_record_the_budgets_and_the_runtime() -> None:
    fresh = _by_id(describe(audit=_audit(), runtime=RUNTIME_OFF))
    assert fresh["diagnose"]["available"]  # mock mode needs no provider
    assert fresh["repair"]["available"] and fresh["cancel"]["available"] and fresh["export"]["available"]
    assert not fresh["verify"]["available"] and "Docker" in fresh["verify"]["blocked_reason"]
    assert not fresh["strength"]["available"] and "VERIFIED" in fresh["strength"]["blocked_reason"]
    assert not fresh["validate"]["available"] and not fresh["recover"]["available"]
    assert fresh["diagnose"]["endpoint"] == "/api/v1/audits/audit-1/diagnose"

    live = _by_id(describe(audit=_audit(mode="live"), runtime=RUNTIME_OFF))
    assert not live["diagnose"]["available"] and "NVIDIA" in live["diagnose"]["blocked_reason"]

    ready = _by_id(describe(audit=_audit(gate_verdict="VERIFIED"), runtime=RUNTIME_ON, has_bundle=True))
    assert all(ready[s]["available"] for s in ("verify", "strength", "validate", "replay"))

    low = _by_id(describe(audit=_audit(gate_verdict="VERIFIED", reservations='{"mutation_executions": 11}'), runtime=RUNTIME_ON))
    assert not low["strength"]["available"] and "budget" in low["strength"]["blocked_reason"]

    stalled = _by_id(describe(audit=_audit(run_state="STALLED"), runtime=RUNTIME_OFF, recovery={"recovery_count": 0}))
    assert not stalled["diagnose"]["available"] and stalled["recover"]["available"]
    used = _by_id(describe(audit=_audit(run_state="STALLED"), runtime=RUNTIME_OFF, recovery={"recovery_count": 1}))
    assert not used["recover"]["available"] and "used" in used["recover"]["blocked_reason"]
    blocked = _by_id(describe(audit=_audit(run_state="BLOCKED"), runtime=RUNTIME_ON))
    assert not blocked["diagnose"]["available"] and blocked["export"]["available"]

    exhausted = _by_id(describe(audit=_audit(limits_json='{"max_actions": 2}'), runtime=RUNTIME_OFF, action_count=2))
    assert not exhausted["diagnose"]["available"] and "budget" in exhausted["diagnose"]["blocked_reason"]
    patched_out = _by_id(describe(audit=_audit(limits_json='{"max_patches": 1}'), runtime=RUNTIME_OFF, patch_count=1))
    assert not patched_out["repair"]["available"]
    no_repair = _by_id(describe(audit=_audit(fixture_id="CI-01"), runtime=RUNTIME_OFF))
    assert not no_repair["repair"]["available"] and "No owner-approved repair" in no_repair["repair"]["blocked_reason"]

    done = _by_id(describe(audit=_audit(run_state="CANCELLED"), runtime=RUNTIME_ON))
    assert done["export"]["available"]
    assert not done["cancel"]["available"] and not done["diagnose"]["available"] and not done["verify"]["available"]
    pending = _by_id(describe(audit=_audit(run_state="CANCEL_PENDING"), runtime=RUNTIME_ON))
    assert not pending["cancel"]["available"] and not pending["diagnose"]["available"]


def test_unknown_skill_is_never_available() -> None:
    bogus = Skill("bogus", "/bogus", "x", "y", "run", "POST", "/nope")
    assert evaluate_availability(bogus, audit=_audit(), runtime=RUNTIME_ON) == (False, "Unknown skill.")


def test_skills_api_is_owner_scoped_and_reflects_the_record(client: TestClient) -> None:
    session = client.get("/api/v1/skills")
    assert session.status_code == 200 and session.json()["audit_id"] is None
    ids = _by_id(session.json()["skills"])
    assert ids["start"]["available"] and not ids["verify"]["available"]

    audit_id = client.post("/api/v1/audits", json={"fixture_id": "MC-01"}).json()["audit_id"]
    scoped = client.get(f"/api/v1/audits/{audit_id}/skills")
    assert scoped.status_code == 200
    body = scoped.json()
    assert body["audit_id"] == audit_id and body["version"] == SKILLS_VERSION and body["run_state"] == "QUEUED"
    by_id = _by_id(body["skills"])
    assert by_id["diagnose"]["available"]
    assert by_id["diagnose"]["endpoint"] == f"/api/v1/audits/{audit_id}/diagnose"
    assert not by_id["verify"]["available"]  # the test runner is the labeled mock
    assert not by_id["validate"]["available"]

    assert client.post(f"/api/v1/audits/{audit_id}/bundle").status_code == 200
    after_bundle = _by_id(client.get(f"/api/v1/audits/{audit_id}/skills").json()["skills"])
    assert after_bundle["validate"]["available"]

    assert client.post(f"/api/v1/audits/{audit_id}/cancel").status_code == 200
    cancelled = _by_id(client.get(f"/api/v1/audits/{audit_id}/skills").json()["skills"])
    assert not cancelled["cancel"]["available"] and "CANCELLED" in cancelled["cancel"]["blocked_reason"]
    assert cancelled["export"]["available"]

    denied = client.get(f"/api/v1/audits/{audit_id}/skills", headers={"X-BenchProof-Owner": "someone-else"})
    assert denied.status_code == 403 and denied.json()["detail"]["code"] == "OWNER_DENIED"
