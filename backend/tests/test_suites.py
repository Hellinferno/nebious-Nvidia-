"""B-18: frozen held-out suites, truth lock and visible smoke gate."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

from benchproof.evaluator.harness import collect_observations_in_process, validate_fixture
from benchproof.evaluator.smoke import SMOKE_CHECK_IDS, evaluate_smoke, smoke_summary, smoke_verdict
from benchproof.fixtures import source_hash_for_dir
from benchproof.gate import verify_candidate_app
from benchproof.mutations import _fixture_family
from benchproof.patch import PatchProposal, apply_patch_to_dir, validate_patch
from benchproof.suites import (
    GATE_SUITE,
    GRAPH_SUITE,
    MUTANT_SUITE,
    REPAIR_SUITE,
    TRAJECTORY_SUITE,
    agent_visible_leaks,
    gate_root,
    load_json,
    load_manifest,
    load_scope,
    repair_case_ids,
    repair_root,
    require_frozen,
    verify_lock,
)

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND / "scripts") not in sys.path:
    sys.path.insert(0, str(BACKEND / "scripts"))

import author_heldout_r12 as r12
import author_heldout_v12 as v12

FAMILY_TOKENS = ("AC", "MC", "CI", "ID", "CL", "API", "AMOUNT", "CALLER", "IDEMP", "CLEAN")


@pytest.fixture()
def heldout_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(repair_root()))


def test_lock_matches_committed_assets() -> None:
    assert verify_lock() == []
    lock = require_frozen()
    assert lock["lock_hash"]
    assert all(k.startswith((REPAIR_SUITE, GATE_SUITE, "manifests/")) for k in lock["entries"])


def test_generators_reproduce_the_frozen_trees() -> None:
    assert r12.check_tree(r12.SUITE_ROOT, r12.all_cases()) == []
    assert v12.check_suite(v12.build_all()) == []


def test_repair_suite_counts_and_opaque_ids() -> None:
    manifest = load_manifest(REPAIR_SUITE)
    ids = repair_case_ids()
    assert len(ids) == 12
    assert manifest["counts"] == {
        "unique_cases": 12, "faulty": 8, "clean": 4, "trials_per_case": 3,
        "b2_trials": 36, "b1_trials": 36, "b0_runs": 12, "faulty_trials": 24, "clean_trials": 12,
    }
    assert set(manifest["r6_subset"]["case_ids"]) < set(ids)
    assert len(manifest["r6_subset"]["case_ids"]) == 6
    truth_by_id = {cid: load_json(repair_root() / cid / "expected.json") for cid in ids}
    r6_faulty = sum(1 for cid in manifest["r6_subset"]["case_ids"] if truth_by_id[cid]["expected_verdict"] == "REJECTED")
    assert r6_faulty == 4
    families = {t["family"] for t in truth_by_id.values()}
    assert families == {"API compatibility", "Exact amount boundary", "Cross-module caller impact",
                        "Tenant-scoped idempotency", "Clean control"}
    for cid in ids:
        assert cid.startswith("HO-") and cid[3:].isdigit()
        public = load_json(repair_root() / cid / "fixture.json")
        assert public["visibility"] == "held-out"
        assert public["family"] is None and public["constraint"] is None and public["defect"] is None
        assert agent_visible_leaks(repair_root() / cid) == []


def test_repair_truth_validates_externally(heldout_env: None) -> None:
    """Development harness: faulty cases fail intended checks, references and clean controls pass."""
    for cid in repair_case_ids():
        report = validate_fixture(cid)
        assert report["ok"], (cid, report["problems"])
        truth = load_json(repair_root() / cid / "expected.json")
        observed_failing = set(report["original"]["failing_checks"])
        allowed = set(truth["intended_failing_checks"]) | set(truth.get("consequential_failing_checks", []))
        assert observed_failing == allowed, (cid, observed_failing, allowed)


def test_every_faulty_case_passes_the_visible_smoke_gate(heldout_env: None) -> None:
    """The visible gate is blind to every frozen defect; the protected gate is what catches them."""
    passed_smoke = 0
    for cid in repair_case_ids():
        truth = load_json(repair_root() / cid / "expected.json")
        if truth["expected_verdict"] != "REJECTED":
            continue
        summary = smoke_summary(collect_observations_in_process(repair_root() / cid / "app"))
        assert summary["verdict"] == "PASS", (cid, summary["failing_checks"])
        passed_smoke += 1
    assert passed_smoke == 8


def test_gate_candidates_apply_and_match_frozen_labels() -> None:
    manifest = load_manifest(GATE_SUITE)
    truth = load_json(gate_root() / "expected.json")
    assert manifest["counts"] == {"total": 12, "valid": 4, "invalid": 8}
    labels = {row["candidate_id"]: row for row in truth["labels"]}
    assert len(labels) == 12
    v6 = manifest["v6_subset"]["candidate_ids"]
    assert len(v6) == 6
    assert sum(1 for cid in v6 if labels[cid]["validity"] == "valid") == 2
    for entry in manifest["candidates"]:
        row = labels[entry["candidate_id"]]
        base_app = repair_root() / row["base_case"] / "app"
        diff = (gate_root() / entry["diff_path"]).read_text(encoding="utf-8")
        proposal = PatchProposal(
            patch_id=row["candidate_id"], audit_id="test", base_source_hash=source_hash_for_dir(base_app),
            target_files=row["target_files"], diff=diff,
        )
        validate_patch(proposal, source_hash_for_dir(base_app))
        with tempfile.TemporaryDirectory(prefix="bp-v12-test-") as tmp:
            dest = Path(tmp) / "app"
            _, candidate_hash = apply_patch_to_dir(base_app, proposal, dest)
            assert candidate_hash == row["candidate_source_hash"]
            protected = verify_candidate_app(dest)
            smoke = smoke_verdict(evaluate_smoke(collect_observations_in_process(dest)))
        assert protected["verdict"] == row["expected_protected_verdict"], row["candidate_id"]
        assert set(row["expected_failing_checks"]) <= set(protected["failing_checks"])
        assert smoke == "PASS", row["candidate_id"]
        if row["validity"] == "invalid":
            assert protected["verdict"] == "REJECTED"


def test_graph_truth_names_existing_symbols_and_derives_checks() -> None:
    manifest = load_manifest(GRAPH_SUITE)
    assert manifest["counts"]["tasks"] == 8
    from benchproof.constraints import get_constraint

    for task in manifest["tasks"]:
        expected_checks = sorted({c for cid in task["expected_contracts"] for c in get_constraint(cid).protected_check_ids})
        assert task["expected_contract_checks"] == expected_checks
        assert task["source_hash"]
    empty = [t for t in manifest["tasks"] if not t["expected_contracts"]]
    assert len(empty) == 1 and empty[0]["expected_entry_points"] == []


def test_trajectory_and_mutant_manifests_are_frozen() -> None:
    trajectory = load_manifest(TRAJECTORY_SUITE)
    assert trajectory["counts"] == {"stalls": 4, "progressing": 4}
    assert trajectory["rule_version"] == "trajectory-fingerprint-v1"
    mutants = load_manifest(MUTANT_SUITE)
    assert mutants["counts"]["templates"] == 12
    assert mutants["counts"]["applicable"] == 12 and mutants["counts"]["syntax_valid"] == 12
    assert mutants["templates_module_hash"]
    scope = load_scope()
    assert scope["assigned_trials"]["B2_runtime_trials"] == 36
    assert scope["fallback"]["repair"]["suite"] == "repair-r6-v1"


def test_mutation_family_falls_back_to_trusted_truth(heldout_env: None) -> None:
    assert _fixture_family("MC-01") == "amount"
    assert _fixture_family("HO-07") == "idempotency"
    assert _fixture_family("does-not-exist") is None


def test_smoke_gate_handles_missing_and_failing_observations() -> None:
    assert smoke_verdict(evaluate_smoke(None)) == "UNKNOWN"
    results = evaluate_smoke({"error": "ImportError: boom", "route": {}, "worker": {}})
    assert [r.check_id for r in results] == list(SMOKE_CHECK_IDS)
    assert smoke_verdict(results) == "FAIL"
    good = {
        "error": None,
        "route": {"first": {"status": 201, "body": {"receipt_id": "r"}}},
        "worker": {"stored_receipt": {}, "error": None},
    }
    assert smoke_verdict(evaluate_smoke(good)) == "PASS"
    bad_worker = {**good, "worker": {"stored_receipt": None, "error": "TypeError"}}
    assert smoke_verdict(evaluate_smoke(bad_worker)) == "FAIL"
    assert json.dumps(smoke_summary(good))  # serializable record
