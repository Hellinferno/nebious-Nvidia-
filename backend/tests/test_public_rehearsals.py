"""Validate frozen public rehearsal inputs without executing candidate code."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from benchproof.coding.contracts import TaskLimits
from benchproof.coding.generation import CodingBrief, CodingPreferences
from benchproof.projects.intake import validate_project_intake

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "verification/public-workflows-v1.json"


def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_public_rehearsal_inputs_remain_frozen_and_not_held_out():
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == (
        "115227117b7ecfab6057012039ee4ee38ad9a8e74c1a29e0f2a5af8e069f4dfb"
    )
    suite = manifest()
    assert suite["schema_version"] == "benchproof/public-rehearsal-cases-v1"
    assert suite["suite_id"] == "public-workflows-v1"
    assert suite["held_out"] is False
    assert suite["comparative_benchmark"] is False
    assert len({case["id"] for case in suite["cases"]}) == 2


def test_public_rehearsal_sources_are_valid_scoped_and_source_bound():
    expected_hashes = {
        "bank-transfer-feature": "7ab96456b832bed3915587cfe1d8ae33d7502af29a4930ec407f4be6f51914fd",
        "correct-total-no-change": "6733e7c91b2563e9eb2c212ef023e7505208ee6571a1a418a596429bd4d01439",
    }
    for case in manifest()["cases"]:
        project, files = validate_project_intake(case["files"], runner_profile="unittest")
        assert project.source_hash == expected_hashes[case["id"]]
        assert all(name.startswith("app/") and name in files for name in case["editable_paths"])
        checks = []
        for filename, content in files.items():
            tree = ast.parse(content, filename=filename)
            if filename.startswith("tests/"):
                checks.extend(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
        assert len(checks) == case["expected"]["checks"]


def test_public_rehearsal_budgets_fit_the_approved_four_call_ceiling():
    cases = manifest()["cases"]
    assert sum(case["limits"]["model_calls"] for case in cases) <= 4
    for case in cases:
        project, _files = validate_project_intake(case["files"], runner_profile="unittest")
        preferences = CodingPreferences(
            workflow=case["workflow"], harness="single-pass-v1", limits=case["limits"],
        )
        brief = CodingBrief(
            task=case["task"], source_hash=project.source_hash,
            editable_paths=case["editable_paths"], preferences=preferences,
        )
        assert vars(TaskLimits.for_brief(brief)) == case["limits"]
        assert case["limits"]["patch_attempts"] == 1
        assert case["limits"]["executions"] <= 3


def test_no_change_control_is_an_expected_stop_not_an_implemented_feature():
    control = next(case for case in manifest()["cases"] if case["id"] == "correct-total-no-change")
    assert control["workflow"] == "bugfix"
    assert control["expected"]["state"] == "BLOCKED"
    assert control["expected"]["code"] == "BASELINE_ALREADY_PASSES"
    assert control["expected"]["patch_attempts"] == 0
    assert control["expected"]["patch_required"] is False
    assert control["limits"]["model_calls"] == 1
