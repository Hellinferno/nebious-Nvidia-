"""Cloud acceptance tooling never schedules inference or retries a mutation."""

import json
from types import SimpleNamespace

import httpx
import pytest

from benchproof.patch import PatchValidationError, compute_diff_hash
from scripts import check_coding_generation as generation
from scripts import verify_generated_patch_cloud as cloud


def _artifact(output):
    def complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        return {
            "finish_reason": "stop", "response_id": "synthetic-only", "usage": {"total_tokens": 100},
            "content": json.dumps({
                "source_hash": payload["source_hash"], "plan_hash": payload["plan_hash"],
                "files": [{"path": "app/money.py", "content": payload["source"]["app/money.py"] + "\n"}],
                "explanation": "Synthetic cloud-tool test, not inference or candidate execution",
            }),
        }

    generation.run_live_check(output, SimpleNamespace(complete=complete), "nvidia/test")
    return compute_diff_hash((output / "candidate.diff").read_text())


def _transport(diff_hash, calls, fail=False):
    def handle(request):
        calls.append(request)
        path = request.url.path
        if path.endswith("ready"):
            return httpx.Response(200, json={"contract_hash": "a" * 64, "runner": {"isolated_execution_available": True}})
        if path.endswith("audits"):
            return httpx.Response(201, json={"audit_id": "audit-cloud-test"})
        if path.endswith("patch"):
            return httpx.Response(200, json={"patch_id": "patch-cloud-test", "diff_hash": diff_hash, "policy_result": "PENDING"})
        if path.endswith("verify"):
            if fail:
                return httpx.Response(503, json={"detail": {"code": "RUNNER_UNAVAILABLE"}})
            body = json.loads(request.content)
            assert body["use_docker"] is True
            candidate = "patch_id" in body
            return httpx.Response(200, json={
                "verdict": "VERIFIED" if candidate else "REJECTED",
                "failing_checks": [] if candidate else ["amount-boundary"], "unknown_checks": [],
                "image_hash": "sha256:test", "patch_hash": diff_hash if candidate else "",
                "isolation": {"enforced": True, "network": "none"},
            })
        pytest.fail(f"Unexpected network route: {path}")

    return httpx.MockTransport(handle)


def test_cloud_check_imports_exact_saved_edit_without_model_or_host_execution(tmp_path):
    diff_hash = _artifact(tmp_path)
    calls = []
    with httpx.Client(base_url=cloud.PUBLIC_URL, transport=_transport(diff_hash, calls)) as client:
        report = cloud.verify_cloud(tmp_path, client)
    assert report["status"] == "PASSED"
    assert report["additional_model_calls"] == 0
    assert len(calls) == 5
    assert sum(request.method == "POST" for request in calls) == 4
    assert len({request.headers["X-BenchProof-Owner"] for request in calls}) == 1
    assert all("Authorization" not in request.headers for request in calls)


def test_cloud_failure_is_not_retried_and_later_actions_are_not_started(tmp_path):
    diff_hash = _artifact(tmp_path)
    calls = []
    with httpx.Client(base_url=cloud.PUBLIC_URL, transport=_transport(diff_hash, calls, fail=True)) as client:
        report = cloud.verify_cloud(tmp_path, client)
    assert report["status"] == "FAILED"
    assert report["http_status"] == 503
    assert report["failed_phase"] == "baseline"
    assert len(calls) == 3


def test_artifact_tampering_is_rejected_before_network(tmp_path):
    _artifact(tmp_path)
    (tmp_path / "candidate.diff").write_text("--- a/app/money.py\n+++ b/app/money.py\n@@ -1 +1 @@\n-forged\n+forged\n")
    with pytest.raises((ValueError, PatchValidationError)), httpx.Client(base_url=cloud.PUBLIC_URL) as client:
        cloud.verify_cloud(tmp_path, client)
    assert not (tmp_path / "cloud-reservation.json").exists()


def test_existing_cloud_reservation_prevents_repeated_mutations(tmp_path):
    diff_hash = _artifact(tmp_path)
    calls = []
    with httpx.Client(base_url=cloud.PUBLIC_URL, transport=_transport(diff_hash, calls)) as client:
        cloud.verify_cloud(tmp_path, client)
        with pytest.raises(FileExistsError):
            cloud.verify_cloud(tmp_path, client)
    assert len(calls) == 5
