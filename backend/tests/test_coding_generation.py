"""The production edit primitive never applies or executes a model's proposal."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from benchproof.coding.generation import CodingBrief, CodingPlan, GenerationError, generate_edits
from benchproof.fixtures import source_hash_for_dir
from benchproof.patch import apply_patch_to_file
from benchproof.providers import ProviderError


class ScriptedClient:
    def __init__(self, reply, before_reply=None):
        self.reply = reply
        self.before_reply = before_reply
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self.before_reply:
            self.before_reply()
        if isinstance(self.reply, Exception):
            raise self.reply
        return {
            "content": json.dumps(self.reply), "finish_reason": "stop",
            "response_model": "nvidia/test", "response_id": "coding-test",
            "usage": {"total_tokens": 120},
        }


def _task(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    (app / "core.py").write_bytes(b"VALUE = 1\n")
    brief = CodingBrief(task="Change VALUE to 2", source_hash=source_hash_for_dir(app), editable_paths=["app/core.py"])
    plan = CodingPlan(source_hash=brief.source_hash, brief_hash=brief.identity(), steps=["Update the constant"], target_files=brief.editable_paths)
    reply = {
        "schema_version": "coding-edit-v1", "source_hash": brief.source_hash,
        "plan_hash": plan.identity(), "files": [{"path": "app/core.py", "content": "VALUE = 2\n"}],
        "explanation": "Updated the requested constant",
    }
    return app, brief, plan, reply


def _generate(app, brief, plan, client, **kwargs):
    return generate_edits(brief, plan, plan.identity(), app, client=client, model_id="nvidia/test", **kwargs)


def test_real_edit_primitive_builds_reviewable_diff_without_modifying_source(tmp_path):
    app, brief, plan, reply = _task(tmp_path)
    client = ScriptedClient(reply)
    patch, metadata = _generate(app, brief, plan, client)
    assert patch.author == "nebius-coding-agent-v1"
    assert patch.target_files == ["app/core.py"]
    assert apply_patch_to_file("VALUE = 1\n", patch.diff) == "VALUE = 2\n"
    assert (app / "core.py").read_bytes() == b"VALUE = 1\n"
    assert metadata["plan_hash"] == plan.identity()
    assert metadata["usage"]["total_tokens"] == 120
    assert len(client.calls) == 1
    assert client.calls[0]["max_tokens"] == 2_048
    assert "VALUE = 1" in client.calls[0]["user_prompt"]


@pytest.mark.parametrize("path", [
    "../secret.py", "app/../tests/test.py", "/app/core.py", "app\\core.py",
    "C:app/core.py", "tests/core.py", "app/.env", "app/core.py/", "app//core.py",
    "app/tests/core.py", "app/evaluator/core.py",
])
def test_non_portable_or_protected_paths_fail_the_contract(path):
    with pytest.raises(ValidationError):
        CodingBrief(task="Task", source_hash="a" * 64, editable_paths=[path])


def test_duplicate_paths_are_rejected():
    with pytest.raises(ValidationError):
        CodingBrief(task="Task", source_hash="a" * 64, editable_paths=["app/Core.py", "app/core.py"])


def test_modified_plan_is_rejected_before_billing(tmp_path):
    app, brief, plan, reply = _task(tmp_path)
    client = ScriptedClient(reply)
    with pytest.raises(GenerationError) as error:
        generate_edits(brief, plan, "0" * 64, app, client=client, model_id="nvidia/test")
    assert error.value.code == "PLAN_UNAPPROVED"
    assert not client.calls


def test_changed_task_invalidates_approved_plan(tmp_path):
    app, brief, plan, reply = _task(tmp_path)
    modified = brief.model_copy(update={"task": "Different task"})
    client = ScriptedClient(reply)
    with pytest.raises(GenerationError) as error:
        _generate(app, modified, plan, client)
    assert error.value.code == "PLAN_UNAPPROVED"
    assert not client.calls


def test_plan_cannot_expand_approved_files(tmp_path):
    app, brief, plan, reply = _task(tmp_path)
    expanded = plan.model_copy(update={"target_files": ["app/other.py"]})
    client = ScriptedClient(reply)
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, expanded, client)
    assert error.value.code == "PLAN_UNAPPROVED"
    assert not client.calls


@pytest.mark.parametrize("during_call", [False, True])
def test_stale_source_before_or_during_generation_never_produces_patch(tmp_path, during_call):
    app, brief, plan, reply = _task(tmp_path)

    def change():
        (app / "core.py").write_bytes(b"VALUE = 3\n")

    client = ScriptedClient(reply, before_reply=change if during_call else None)
    if not during_call:
        change()
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, plan, client)
    assert error.value.code == "STALE_SOURCE"
    assert len(client.calls) == int(during_call)


@pytest.mark.parametrize("field", ["source_hash", "plan_hash"])
def test_response_must_echo_current_identities(tmp_path, field):
    app, brief, plan, reply = _task(tmp_path)
    reply[field] = "0" * 64
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, plan, ScriptedClient(reply))
    assert error.value.code == "STALE_CONTEXT"
    assert error.value.metadata["usage"]["total_tokens"] == 120


def test_model_cannot_choose_a_different_existing_file(tmp_path):
    app, brief, plan, reply = _task(tmp_path)
    (app / "other.py").write_bytes(b"VALUE = 1\n")
    brief = brief.model_copy(update={"source_hash": source_hash_for_dir(app)})
    plan = plan.model_copy(update={"source_hash": brief.source_hash, "brief_hash": brief.identity()})
    reply.update(source_hash=brief.source_hash, plan_hash=plan.identity())
    reply["files"][0]["path"] = "app/other.py"
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, plan, ScriptedClient(reply))
    assert error.value.code == "PROTECTED_FILE_VIOLATION"
    assert (app / "other.py").read_bytes() == b"VALUE = 1\n"


def test_oversized_context_is_rejected_before_paid_request(tmp_path):
    app, brief, plan, reply = _task(tmp_path)
    client = ScriptedClient(reply)
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, plan, client, observations={"log": "x" * 24_576})
    assert error.value.code == "SOURCE_LIMIT"
    assert not client.calls


@pytest.mark.parametrize("content,code", [("VALUE = 1\n", "EMPTY_DIFF"), ("\n" * 101, "PATCH_TOO_LARGE")])
def test_invalid_patch_is_rejected_with_usage_not_applied(tmp_path, content, code):
    app, brief, plan, reply = _task(tmp_path)
    reply["files"][0]["content"] = content
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, plan, ScriptedClient(reply))
    assert error.value.code == code
    assert error.value.metadata["usage"]["total_tokens"] == 120
    assert (app / "core.py").read_bytes() == b"VALUE = 1\n"


def test_provider_error_is_not_retried_or_substituted(tmp_path):
    app, brief, plan, _ = _task(tmp_path)
    client = ScriptedClient(ProviderError("private text"))
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, plan, client)
    assert len(client.calls) == 1
    assert error.value.code == "PROVIDER_UNAVAILABLE"
    assert "private" not in str(error.value)
    assert error.value.metadata["usage_status"] == "UNKNOWN"


def test_truncated_edit_retains_usage_and_never_becomes_a_patch(tmp_path):
    app, brief, plan, reply = _task(tmp_path)

    class TruncatedClient(ScriptedClient):
        def complete(self, **kwargs):
            response = super().complete(**kwargs)
            response["finish_reason"] = "length"
            return response

    client = TruncatedClient(reply)
    with pytest.raises(GenerationError) as error:
        _generate(app, brief, plan, client)
    assert error.value.code == "MODEL_OUTPUT_TRUNCATED"
    assert error.value.metadata["usage"]["total_tokens"] == 120
    assert len(client.calls) == 1
    assert (app / "core.py").read_bytes() == b"VALUE = 1\n"
