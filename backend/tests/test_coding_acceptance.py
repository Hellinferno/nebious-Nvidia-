"""Acceptance tooling is explicitly opt-in and never retries a paid call."""

import json

import pytest

from benchproof.coding.generation import GenerationError
from benchproof.providers import ProviderError
from scripts import check_coding_generation as check


class CountingAdapter:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def complete(self, **kwargs):
        self.calls += 1
        if self.fail:
            raise ProviderError("private error")
        payload = json.loads(kwargs["user_prompt"])
        return {
            "finish_reason": "stop", "usage": {"total_tokens": 100}, "response_id": "test-only",
            "content": json.dumps({
                "source_hash": payload["source_hash"], "plan_hash": payload["plan_hash"],
                "files": [{"path": "app/money.py", "content": payload["source"]["app/money.py"] + "\n"}],
                "explanation": "Synthetic test edit, not live generation",
            }),
        }


def test_acceptance_records_one_call_without_claiming_execution(tmp_path):
    adapter = CountingAdapter()
    report = check.run_live_check(tmp_path, adapter, "nvidia/test")
    assert adapter.calls == 1
    assert report["status"] == "GENERATED_POLICY_VALIDATED"
    assert report["execution_status"] == "NOT_RUN"
    assert report["original_source_unchanged"] is True
    assert (tmp_path / "candidate.diff").is_file()
    assert (tmp_path / "call-reservation.json").is_file()
    assert json.loads((tmp_path / "report.json").read_text())["model_calls"] == 1


def test_failed_call_is_persisted_unknown_without_retry(tmp_path):
    adapter = CountingAdapter(fail=True)
    report = check.run_live_check(tmp_path, adapter, "nvidia/test")
    assert adapter.calls == 1
    assert report["status"] == "FAILED"
    assert report["provider"]["usage_status"] == "UNKNOWN"
    assert "private" not in json.dumps(report)
    assert not (tmp_path / "candidate.diff").exists()


def test_recording_client_cannot_make_second_call(tmp_path):
    adapter = CountingAdapter(fail=True)
    client = check.RecordingClient(adapter, tmp_path)
    with pytest.raises(ProviderError):
        client.complete(model="test", max_tokens=2_048)
    with pytest.raises(GenerationError) as error:
        client.complete(model="test", max_tokens=2_048)
    assert error.value.code == "BUDGET_EXHAUSTED"
    assert adapter.calls == 1


def test_unavailable_runner_blocks_before_any_inference(tmp_path):
    class UnavailableRunner:
        def available(self):
            return False, "offline"

    adapter = CountingAdapter()
    report = check.run_live_check(tmp_path, adapter, "nvidia/test", UnavailableRunner())
    assert report["code"] == "RUNNER_UNAVAILABLE"
    assert report["model_calls"] == adapter.calls == 0
    assert report["execution_status"] == "NOT_RUN"


def test_existing_run_cannot_overwrite_or_trigger_inference(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "REPO_ROOT", tmp_path)
    output = tmp_path / "artifacts" / "coding" / "existing"
    output.mkdir(parents=True)
    monkeypatch.setattr("sys.argv", ["check_coding_generation.py", "--run-id", "existing", "--live-once"])
    monkeypatch.setattr(check, "NebiusAdapter", lambda **_: pytest.fail("provider created"))
    with pytest.raises(FileExistsError):
        check.main()
