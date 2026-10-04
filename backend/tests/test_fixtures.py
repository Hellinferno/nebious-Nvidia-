"""Development-suite checks (B-03). Imports candidate code in-process: development only."""

from __future__ import annotations

import pytest

from benchproof.evaluator.harness import (
    evaluate_fixture,
    evaluate_reference_repair,
    required_check_ids,
    validate_fixture,
)
from benchproof.fixtures import (
    fixture_dir,
    list_fixture_ids,
    load_expected,
    load_manifest,
    source_hash,
)

FAULTY = ["AC-01", "MC-01", "CI-01", "ID-01"]


def test_suite_lists_five_development_fixtures() -> None:
    assert list_fixture_ids() == ["AC-01", "CI-01", "ID-01", "MC-01", "clean-service"]
    for fid in list_fixture_ids():
        assert load_manifest(fid)["suite"] == "development-v2"


def test_source_hash_is_deterministic_and_fixture_specific() -> None:
    assert source_hash("AC-01") == source_hash("AC-01")
    assert len({source_hash(f) for f in list_fixture_ids()}) == 5


def test_trusted_assets_are_outside_candidate_tree() -> None:
    for fid in list_fixture_ids():
        app = fixture_dir(fid) / "app"
        assert not (app / "expected.json").exists()
        assert not (app / "reference").exists()
        assert (fixture_dir(fid) / "expected.json").exists()


def test_required_checks_cover_every_constraint() -> None:
    assert required_check_ids() == {
        "api-field-presence",
        "api-status-code",
        "amount-boundary",
        "caller-consistency",
        "idempotency-duplicate",
        "idempotency-conflict",
        "worker-caller-path",
    }


@pytest.mark.parametrize("fid", FAULTY)
def test_faulty_fixture_fails_intended_checks_and_is_rejected(fid: str) -> None:
    actual = evaluate_fixture(fid)
    intended = set(load_expected(fid)["intended_failing_checks"])
    assert intended, fid
    assert intended.issubset(set(actual["failing_checks"])), actual
    assert actual["verdict"] == "REJECTED"


@pytest.mark.parametrize("fid", FAULTY)
def test_reference_repair_is_verified(fid: str) -> None:
    ref = evaluate_reference_repair(fid)
    assert ref is not None
    assert ref["verdict"] == "VERIFIED", ref
    assert ref["failing_checks"] == [] and ref["unknown_checks"] == []


def test_clean_control_passes_untouched() -> None:
    actual = evaluate_fixture("clean-service")
    assert actual["verdict"] == "VERIFIED", actual
    assert actual["failing_checks"] == []
    assert evaluate_reference_repair("clean-service") is None


def test_boundary_input_distinguishes_mc01_from_clean() -> None:
    mc = evaluate_fixture("MC-01")
    reason = next(c["reason"] for c in mc["checks"] if c["check_id"] == "amount-boundary")
    assert "0.02" in reason and "0.01" in reason


def test_every_check_result_cites_versions() -> None:
    actual = evaluate_fixture("clean-service")
    for c in actual["checks"]:
        assert c["source_hash"] == actual["source_hash"]
        assert c["contract_hash"] == actual["contract_hash"]
        assert c["evaluator_hash"] == actual["evaluator_hash"]


def test_validate_fixture_reports_ok_for_whole_suite() -> None:
    reports = [validate_fixture(f) for f in list_fixture_ids()]
    assert all(r["ok"] for r in reports), [r["problems"] for r in reports if not r["ok"]]
