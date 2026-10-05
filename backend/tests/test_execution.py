"""Execution boundary tests: snapshot hygiene, mock labeling, observation oracle, Docker runner."""

from __future__ import annotations

import copy

import pytest

from benchproof.evaluator import run_gate
from benchproof.evaluator.harness import (
    collect_observations_in_process,
    judge,
    required_check_ids,
)
from benchproof.evaluator.observations import evaluate_observations, isolation_findings
from benchproof.execution import MockRunner, prepare_snapshot
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import fixture_dir

CLEAN = fixture_dir("clean-service") / "app"


def test_snapshot_contains_only_candidate_files() -> None:
    snap = prepare_snapshot(CLEAN)
    try:
        names = sorted(p.name for p in snap.app_dir.iterdir())
        assert names == ["__init__.py", "money.py", "repository.py", "routes.py", "schemas.py", "services.py", "worker.py"]
        assert not (snap.root / "expected.json").exists()
        assert snap.out_dir.exists() and not any(snap.out_dir.iterdir())
        assert len(snap.source_hash) == 64
    finally:
        snap.cleanup()
    assert not snap.root.exists()


def test_two_snapshots_are_distinct_and_fresh() -> None:
    a = prepare_snapshot(CLEAN)
    b = prepare_snapshot(CLEAN)
    try:
        assert a.root != b.root and a.run_id != b.run_id
        assert a.source_hash == b.source_hash
    finally:
        a.cleanup()
        b.cleanup()


def test_mock_runner_is_labeled_and_executes_nothing() -> None:
    snap = prepare_snapshot(CLEAN)
    try:
        res = MockRunner().run_observation(snap)
        assert res.runner == "mock"
        assert res.isolation["enforced"] is False
        assert res.observations is None and res.error
        assert judge(res.observations, snap.app_dir)["verdict"] == "INCONCLUSIVE"
    finally:
        snap.cleanup()


def test_no_observations_is_inconclusive_never_verified() -> None:
    results = evaluate_observations(None, None)
    assert run_gate(results, required_check_ids()) == "INCONCLUSIVE"
    assert all(r.outcome.value == "UNKNOWN" for r in results)


def test_candidate_crash_is_inconclusive() -> None:
    obs = {"schema": "benchproof/observations-v1", "error": "ImportError: boom", "route": {}, "worker": {}}
    results = evaluate_observations(obs, (CLEAN / "worker.py").read_text())
    assert run_gate(results, required_check_ids()) == "INCONCLUSIVE"


def test_oracle_uses_trusted_inputs_not_reported_ones() -> None:
    """A candidate that reports different inputs cannot change the expected total."""
    obs = collect_observations_in_process(CLEAN)
    tampered = copy.deepcopy(obs)
    tampered["inputs"] = {"boundary_lines": ["0.01", "0.01"]}  # would make 0.02 'correct'
    tampered["route"]["first"]["body"]["total_amount"] = "0.02"
    tampered["worker"]["stored_receipt"]["response"]["total_amount"] = "0.02"
    results = evaluate_observations(tampered, (CLEAN / "worker.py").read_text())
    amount = next(r for r in results if r.check_id == "amount-boundary")
    assert amount.outcome.value == "FAIL"


def test_forged_pass_text_in_observations_is_ignored() -> None:
    obs = collect_observations_in_process(fixture_dir("MC-01") / "app")
    obs["verdict"] = "VERIFIED"
    obs["checks"] = [{"check_id": "amount-boundary", "outcome": "PASS"}]
    verdict = judge(obs, fixture_dir("MC-01") / "app")
    assert verdict["verdict"] == "REJECTED"
    assert "amount-boundary" in verdict["failing_checks"]


def test_in_process_and_launcher_schema_agree() -> None:
    obs = collect_observations_in_process(CLEAN)
    assert obs["schema"] == "benchproof/observations-v1"
    assert set(obs["route"]) == {"first", "second", "conflict"}
    assert judge(obs, CLEAN)["verdict"] == "VERIFIED"


# ── Docker (skipped when the daemon/image is unavailable) ───────────────

_runner = DockerRunner()
_docker_ok, _docker_why = _runner.available()
docker = pytest.mark.skipif(not _docker_ok, reason=f"docker runner unavailable: {_docker_why}")


@docker
@pytest.mark.parametrize(("fid", "expected"), [("clean-service", "VERIFIED"), ("MC-01", "REJECTED")])
def test_docker_runner_judged_outside_matches_expected(fid: str, expected: str) -> None:
    snap = prepare_snapshot(fixture_dir(fid) / "app")
    try:
        res = _runner.run_observation(snap, timeout_s=90)
        assert res.exit_code == 0 and not res.timed_out, res.stderr[-500:]
        assert res.isolation["network"] == "none" and res.isolation["enforced"] is True
        assert res.image_ref and "@sha256:" in res.image_ref
        iso = isolation_findings(res.observations)
        assert iso["internet_denied"] is True and iso["metadata_denied"] is True
        assert iso["secret_env_names"] == []
        assert iso["trusted_assets_present"] == []
        assert iso["candidate_writable"] is False
        assert judge(res.observations, snap.app_dir)["verdict"] == expected
    finally:
        snap.cleanup()


@docker
def test_docker_runner_timeout_kills_container() -> None:
    snap = prepare_snapshot(CLEAN)
    try:
        res = _runner.run_observation(snap, timeout_s=4, launcher_args=["--sleep", "30"])
        assert res.timed_out is True
        assert res.observations is None
        assert not _runner.container_running(snap.run_id)
        assert judge(res.observations, snap.app_dir)["verdict"] == "INCONCLUSIVE"
    finally:
        snap.cleanup()
