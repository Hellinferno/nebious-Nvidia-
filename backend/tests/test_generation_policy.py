"""Policy identity regressions; no provider calls or candidate execution."""

from __future__ import annotations

import pytest

from benchproof.coding import prompts


def test_generation_policy_has_a_frozen_identity_separate_from_historical_runs():
    assert prompts.generation_policy() == {
        "version": "coding-generation-v3",
        "sha256": "34108fa5ff381d7b5b2da5211eac64fd89630d15a4baf682d3b29b369a35d165",
    }


@pytest.mark.parametrize("name", ["PLAN_SYSTEM_PROMPT", "EDIT_SYSTEM_PROMPT"])
def test_either_prompt_change_invalidates_the_policy_identity(monkeypatch, name):
    before = prompts.generation_policy()
    monkeypatch.setattr(prompts, name, getattr(prompts, name) + "\nNew reviewed policy.")
    assert prompts.generation_policy()["sha256"] != before["sha256"]


def test_runtime_identity_adds_policy_without_increasing_existing_allowances():
    identity = prompts.coding_runtime_identity("nvidia/test", 2_048)
    assert identity == {
        "model_id": "nvidia/test",
        "max_output_tokens": 2_048,
        "engine_version": "coding-engine-v1",
        "generation_policy": prompts.generation_policy(),
    }
    identity["generation_policy"]["sha256"] = "untrusted"
    assert prompts.coding_runtime_identity("nvidia/test", 2_048)["generation_policy"] == prompts.generation_policy()
