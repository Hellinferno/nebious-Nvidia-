"""Persisted coding-container identities stay bounded and cannot target other containers."""

import subprocess
from types import SimpleNamespace

import pytest

from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import fixture_dir

OPERATION = "bp-coding-" + "a" * 32


@pytest.mark.parametrize("operation", ["personal-container", "bp-coding-../foo", "--all", "bp-coding-short"])
def test_invalid_operation_is_rejected_before_any_docker_command(monkeypatch, operation):
    runner = DockerRunner()
    monkeypatch.setattr(runner, "available", lambda: pytest.fail("preflight should not run"))
    monkeypatch.setattr(subprocess, "run", lambda *_, **__: pytest.fail("docker command ran"))
    with pytest.raises(ValueError):
        runner.run_observation(None, operation_id=operation)
    with pytest.raises(ValueError):
        runner.cancel_operation(operation)


def test_cancel_before_launch_never_starts_candidate(monkeypatch):
    from benchproof.execution import prepare_snapshot

    runner = DockerRunner()
    monkeypatch.setattr(runner, "available", lambda: (True, "synthetic test"))
    monkeypatch.setattr(subprocess, "Popen", lambda *_, **__: pytest.fail("candidate launched"))
    snapshot = prepare_snapshot(fixture_dir("MC-01") / "app")
    try:
        result = runner.run_observation(snapshot, operation_id=OPERATION, should_cancel=lambda: True)
    finally:
        snapshot.cleanup()
    assert result.operation_id == OPERATION
    assert result.observations is None
    assert result.isolation["cancelled_before_launch"] is True
    assert not runner._containers


@pytest.mark.parametrize("states,expected", [
    ([(0, "false")], True),
    ([(1, ""), (0, "")], True),
    ([(1, ""), (1, "")], False),
    ([(0, "unexpected")], False),
    ([(0, "true"), (0, "killed"), (0, "false")], True),
    ([(0, "true"), (1, "not killed")], False),
    ([(0, "true"), (0, "killed"), (0, "true")], False),
])
def test_operation_cancellation_confirms_state_without_in_memory_mapping(monkeypatch, states, expected):
    calls = []
    remaining = iter(states)

    def command(arguments, **kwargs):
        calls.append(arguments)
        assert kwargs["timeout"] == 5
        assert kwargs["check"] is False
        code, stdout = next(remaining)
        return SimpleNamespace(returncode=code, stdout=stdout)

    monkeypatch.setattr(subprocess, "run", command)
    assert DockerRunner().cancel_operation(OPERATION) is expected
    assert all(OPERATION in " ".join(command) for command in calls)


def test_unknown_daemon_timeout_is_not_reported_cancelled(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("docker", 5)

    monkeypatch.setattr(subprocess, "run", timeout)
    assert DockerRunner().cancel_operation(OPERATION) is False
