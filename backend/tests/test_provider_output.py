"""Provider and diagnosis failure boundaries; no live inference in these tests."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchproof.api import main as api_main
from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord, ContextPacket
from benchproof.fixtures import source_hash
from benchproof.impact import ImpactReport, RiskSeverity
from benchproof.investigation import (
    DiagnosisProposal,
    InvestigationError,
    generate_structured_diagnosis,
    run_investigation,
)
from benchproof.investigation.actions import reserve_diagnosis
from benchproof.providers import NebiusAdapter, ProviderError
from benchproof.providers.structured import ModelOutputError, validate_completion
from benchproof.storage import list_actions, migrate, save_audit
from benchproof.storage.lifecycle import list_events, migrate_lifecycle
from benchproof.trajectory import TrajectoryError, budget_snapshot


def _valid() -> dict:
    return {"hypotheses": [{
        "hypothesis_id": "H1", "constraint_id": "C-AMOUNT",
        "source_location": "app/money.py:compute_total", "claim": "Rounding may differ",
        "refutation_condition": "The boundary check passes",
    }]}


def _response(content: str | None = None, reason: str | None = "stop") -> dict:
    return {
        "content": json.dumps(_valid()) if content is None else content,
        "finish_reason": reason, "response_id": "response-test", "response_model": "nvidia/test",
        "usage": {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50},
        "elapsed_ms": 7,
    }


def _provider(monkeypatch, response):
    calls = []

    class FakeAdapter:
        def __init__(self, **kwargs):
            self.options = kwargs

        def complete(self, **kwargs):
            calls.append(kwargs)
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr("benchproof.investigation.NebiusAdapter", FakeAdapter)
    return calls


def _context():
    context = ContextPacket(source_hash="source", contract_hash="contract", graph_hash="graph")
    impact = ImpactReport([], [], [], [], RiskSeverity.LOW, [], "PARTIAL")
    return context, impact


def _audit(tmp_path: Path, max_actions: int = 2) -> tuple[Path, str]:
    db = tmp_path / "provider.db"
    migrate(db)
    migrate_lifecycle(db)
    audit_id = "audit-provider"
    save_audit(AuditRecord(
        audit_id=audit_id, owner_ref="test-owner", fixture_id="MC-01", mode="live",
        source_hash=source_hash("MC-01"), contract_hash=contract_hash(),
        limits={"max_actions": max_actions},
    ), db)
    return db, audit_id


@pytest.mark.parametrize("fenced", [False, True])
def test_complete_json_is_accepted_without_inventing_fields(fenced):
    content = json.dumps(_valid())
    if fenced:
        content = f"```json\n{content}\n```"
    result = validate_completion(_response(content), DiagnosisProposal)
    assert result.hypotheses[0].claim == "Rounding may differ"


@pytest.mark.parametrize("reason,code", [
    ("length", "MODEL_OUTPUT_TRUNCATED"), ("content_filter", "MODEL_OUTPUT_INCOMPLETE"),
    ("tool_calls", "MODEL_OUTPUT_INCOMPLETE"), (None, "MODEL_OUTPUT_INCOMPLETE"),
])
def test_non_stop_is_rejected_even_when_json_looks_valid(reason, code):
    with pytest.raises(ModelOutputError) as error:
        validate_completion(_response(reason=reason), DiagnosisProposal)
    assert error.value.code == code


@pytest.mark.parametrize("content", [
    '{"hypotheses":[{"hypothesis_id":"H1"',
    '{"hypotheses":[{"hypothesis_id":"H1"}]}',
    '{"hypotheses":[],"hypotheses":[]}',
    '{"hypotheses":[],"risk_reasons":[NaN]}',
    'text before ```json\n{}\n```', "", "[]", "null",
    json.dumps({"hypotheses": [{**_valid()["hypotheses"][0], "proposed_probe": "shell"}]}),
])
def test_malformed_output_is_never_repaired(content):
    with pytest.raises(ModelOutputError) as error:
        validate_completion(_response(content), DiagnosisProposal)
    assert error.value.code == "MALFORMED_ACTION"
    assert content not in error.value.message or not content


def test_response_bytes_are_bounded_before_parsing():
    with pytest.raises(ModelOutputError) as error:
        validate_completion(_response("é" * 16_385), DiagnosisProposal)
    assert error.value.code == "MODEL_OUTPUT_LIMIT"


def test_live_diagnosis_uses_configured_model_and_retains_provenance(monkeypatch):
    calls = _provider(monkeypatch, _response())
    monkeypatch.setenv("NEBIUS_MODEL_ID", "nvidia/configured-test")
    proposal, metadata = generate_structured_diagnosis(*_context())
    assert proposal.hypotheses
    assert len(calls) == 1
    assert calls[0]["model"] == "nvidia/configured-test"
    assert calls[0]["max_tokens"] == 2_048
    assert metadata["requested_model"] == "nvidia/configured-test"
    assert metadata["model_id"] == "nvidia/test"
    assert metadata["usage_status"] == "RECORDED"


def test_truncation_keeps_usage_without_retry_or_probe(tmp_path, monkeypatch):
    db, audit_id = _audit(tmp_path)
    calls = _provider(monkeypatch, _response(reason="length"))
    monkeypatch.setattr("benchproof.investigation.run_baseline", lambda **_: pytest.fail("probe ran"))
    before = source_hash("MC-01")
    with pytest.raises(InvestigationError) as error:
        run_investigation("MC-01", audit_id, mode="live", db_path=db)
    assert error.value.code == "MODEL_OUTPUT_TRUNCATED"
    assert len(calls) == 1
    actions = list_actions(audit_id, db)
    assert len(actions) == 1
    assert actions[0]["status"] == "failed"
    assert actions[0]["usage"]["total_tokens"] == 50
    assert actions[0]["provider_metadata"]["finish_reason"] == "length"
    assert budget_snapshot(audit_id, db)["used_actions"] == 1
    assert list_events(audit_id, db_path=db)[-1]["event_type"] == "action_failed"
    assert source_hash("MC-01") == before


def test_failed_calls_exhaust_original_budget_and_keep_unknown_usage(tmp_path, monkeypatch):
    db, audit_id = _audit(tmp_path, max_actions=1)
    calls = _provider(monkeypatch, ProviderError("private upstream details"))
    with pytest.raises(InvestigationError) as error:
        run_investigation("MC-01", audit_id, mode="live", db_path=db)
    assert error.value.code == "PROVIDER_UNAVAILABLE"
    assert "private" not in error.value.message
    assert list_actions(audit_id, db)[0]["provider_metadata"]["usage_status"] == "UNKNOWN"
    with pytest.raises(TrajectoryError) as exhausted:
        run_investigation("MC-01", audit_id, mode="live", db_path=db)
    assert exhausted.value.code == "BUDGET_EXHAUSTED"
    assert len(calls) == 1


def test_simultaneous_and_interrupted_diagnoses_cannot_double_spend(tmp_path):
    db, audit_id = _audit(tmp_path)

    def reserve(index):
        try:
            reserve_diagnosis(audit_id, f"action-{index}", "source", "context", "test", db)
            return "reserved"
        except TrajectoryError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, [1, 2]))
    assert sorted(outcomes) == ["INVALID_STATE", "reserved"]
    assert reserve(3) == "INVALID_STATE"
    assert len(list_actions(audit_id, db)) == 1


@pytest.mark.parametrize("code,status", [
    ("PROVIDER_UNAVAILABLE", 503), ("PROVIDER_INVALID_RESPONSE", 502),
    ("MODEL_OUTPUT_TRUNCATED", 502), ("MODEL_OUTPUT_INCOMPLETE", 502),
    ("MALFORMED_ACTION", 502),
])
def test_api_reports_upstream_failures_not_client_validation_errors(client, monkeypatch, code, status):
    audit_id = client.post("/api/v1/audits", json={"fixture_id": "MC-01", "mode": "mock"}).json()["audit_id"]

    def fail(**kwargs):
        assert kwargs["max_tokens"] == api_main.settings.benchproof_diagnosis_max_tokens
        raise InvestigationError(code, "Safe explanation")

    monkeypatch.setattr("benchproof.investigation.run_investigation", fail)
    response = client.post(f"/api/v1/audits/{audit_id}/diagnose")
    assert response.status_code == status
    assert response.json()["detail"] == {"code": code, "message": "Safe explanation"}


def test_adapter_never_exposes_raw_transport_exception(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("Bearer secret-value, private body")

    adapter = object.__new__(NebiusAdapter)
    adapter._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
    with pytest.raises(ProviderError) as error:
        adapter.complete("model", "system", "user")
    assert str(error.value) == "Inference failed: RuntimeError"


def test_adapter_empty_choices_is_a_provider_protocol_error():
    adapter = object.__new__(NebiusAdapter)
    adapter._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **_: SimpleNamespace(choices=[]),
    )))
    with pytest.raises(ProviderError) as error:
        adapter.complete("model", "system", "user")
    assert error.value.code == "PROVIDER_INVALID_RESPONSE"
