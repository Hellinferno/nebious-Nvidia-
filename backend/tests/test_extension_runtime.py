"""Extension controls and runner regressions with no candidate execution or inference."""

import hashlib
import io
import json
import subprocess
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_coding_worker import SyntheticExecutor, _approve, _drain, _setup

from benchproof.coding import mcp
from benchproof.coding.contracts import TaskLimits
from benchproof.coding.engine import DispatchingExecutor
from benchproof.coding.extensions import ExternalContext, SkillContext
from benchproof.coding.generation import CodingBrief, CodingPreferences, GenerationError
from benchproof.execution.base import ExecutionResult
from benchproof.execution.docker_runner import DockerRunner
from benchproof.execution.project_runner import ProjectExecutor, prepare_project_snapshot

OPERATION = "bp-coding-" + "a" * 32
FILES = {"app/worker.py": "VALUE = 1\n", "tests/test_value.py": "VALUE = 1\n"}


def test_extensions_preserve_legacy_identity_and_pin_content():
    brief = CodingBrief(task="Task", source_hash="a" * 64, editable_paths=["app/core.py"], preferences=CodingPreferences())
    original = brief.identity()
    assert brief.preferences.canonical_payload() == {"workflow": "custom", "instructions": ""}
    assert original == brief.model_copy(update={"preferences": CodingPreferences(harness="bounded-v1", skills=[], context=[])}).identity()
    skill = SkillContext(name="my-rules", description="My conventions", instructions="Preserve public names")
    customized = brief.model_copy(update={"preferences": CodingPreferences(skills=[skill])})
    assert customized.identity() != original
    assert len(skill.identity()) == 64
    assert TaskLimits.for_brief(brief.model_copy(update={"preferences": CodingPreferences(harness="single-pass-v1")})).patch_attempts == 1


def test_single_pass_stops_without_revision_or_budget_reset(tmp_path):
    store, worker, provider, executor, task_id = _setup(tmp_path, preferences=CodingPreferences(harness="single-pass-v1"), executor=SyntheticExecutor(["REJECTED", "REJECTED"]))
    _approve(store, worker, task_id)
    _drain(worker)
    task = store.get_task("owner", task_id)
    assert task["state"] == "BLOCKED"
    assert task["result"]["code"] == "HARNESS_STOPPED"
    assert len(provider.calls) == len(executor.calls) == 2
    assert task["counters"]["patch_attempts"] == task["limits"]["patch_attempts"] == 1


def test_skills_and_mcp_reference_reach_both_prompt_phases(tmp_path):
    content = "Public reference context"
    preferences = CodingPreferences(skills=[SkillContext(name="python-rules", description="Python edits", instructions="Preserve interfaces")], context=[ExternalContext(connection="docs", tool="search", content=content, sha256=hashlib.sha256(content.encode()).hexdigest())])
    store, worker, provider, _executor, task_id = _setup(tmp_path, preferences=preferences)
    _approve(store, worker, task_id)
    _drain(worker)
    contexts = [json.loads(call["user_prompt"])["preferences"] for call in provider.calls]
    assert contexts[0] == contexts[1]
    assert contexts[0]["skills"][0]["name"] == "python-rules"
    assert contexts[0]["context"][0]["content"] == content
    assert content not in provider.calls[0]["system_prompt"]
    assert store.export_bundle("owner", task_id)["brief"]["preferences"]["context"][0]["content"] == content


@pytest.mark.parametrize("updates", [{"harness": "arbitrary-module"}, {"skills": [{"name": "bad", "description": "d", "instructions": "x", "command": "evil"}]}, {"context": [{"connection": "docs", "tool": "search", "content": "x", "sha256": "a" * 64}]}])
def test_untrusted_extension_configs_fail_closed(updates):
    with pytest.raises(ValidationError):
        CodingPreferences.model_validate(updates)


def test_dispatch_uses_approved_profile_not_user_filename(tmp_path):
    (tmp_path / "worker.py").write_text("VALUE=1")
    calls = []
    class Executor:
        def __init__(self, name): self.name = name
        def run(self, *args, **kwargs): calls.append(self.name); return {}
        def cancel(self, operation): return self.name == "invoice"
    executor = DispatchingExecutor(Executor("invoice"), Executor("project"))
    executor.run(tmp_path, operation_id=OPERATION, check_profile="project-unittest-v1")
    assert calls == ["project"]
    assert executor.cancel(OPERATION) is False
    with pytest.raises(GenerationError): executor.run(tmp_path, operation_id=OPERATION)


@pytest.mark.parametrize("counts", [
    {"test_count": 1, "passed": [], "skipped": [{"test_id": "skip"}]},
    {"test_count": 2, "passed": ["one"], "skipped": []},
    {"test_count": 2, "passed": ["same", "same"], "skipped": []},
])
def test_skipped_missing_duplicate_checks_cannot_pass(counts):
    snapshot = prepare_project_snapshot(FILES)
    try:
        result = ExecutionResult("synthetic", OPERATION, 0, False, 1, "", "", {"test_results": {"failures": [], "errors": [], **counts}})
        report = ProjectExecutor()._evaluate_project_result(snapshot, result, "unittest")
        assert report["verdict"] != "VERIFIED"
        assert all(not check["passed"] for check in report["checks"] if check["status"] == "SKIPPED")
    finally: snapshot.cleanup()


def test_project_uses_shared_runner_identity_launcher_and_cancellation(monkeypatch):
    runner = DockerRunner(image="pinned-image", docker_bin="pinned-docker")
    calls = []
    def run(snapshot, **kwargs):
        calls.append(kwargs)
        return ExecutionResult("synthetic", OPERATION, None, False, 0, "", "", None, isolation={"enforced": False}, error="cancelled")
    monkeypatch.setattr(runner, "run_observation", run)
    monkeypatch.setattr(runner, "cancel_operation", lambda operation: operation == OPERATION)
    executor = ProjectExecutor(runner)
    executor.run(FILES, operation_id=OPERATION, should_cancel=lambda: True)
    assert calls[0]["operation_id"] == OPERATION
    assert calls[0]["launcher_file"] == "run_project_tests.py"
    assert calls[0]["should_cancel"]()
    assert executor.cancel(OPERATION)


def test_shared_runner_retains_nonroot_env_and_output_controls(monkeypatch):
    runner = DockerRunner(image="pinned-image", docker_bin="pinned-docker")
    monkeypatch.setattr(runner, "available", lambda: (True, "synthetic"))
    monkeypatch.setattr(runner, "image_ref", lambda: "pinned-image@sha256:test")
    calls = []
    def start(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout=io.BytesIO(b""), stderr=io.BytesIO(b""), wait=lambda **kwargs: 0)
    monkeypatch.setattr(subprocess, "Popen", start)
    snapshot = prepare_project_snapshot(FILES)
    try:
        result = runner.run_observation(snapshot, operation_id=OPERATION, launcher_file="run_project_tests.py")
        command = calls[0]
        assert command[0] == "pinned-docker"
        assert command[command.index("--name") + 1] == OPERATION
        assert command[command.index("--user") + 1] == "65534:65534"
        assert "env" in command and "-i" in command and "pinned-image" in command
        assert result.observations is None
        assert result.error
    finally: snapshot.cleanup()


@pytest.mark.parametrize("path", ["../secret.py", "/secret.py", "app/../../secret.py", "tests/../app/a.py", "app/.env"])
def test_snapshot_rejects_unsafe_paths_before_writing(path):
    with pytest.raises(ValueError): prepare_project_snapshot({path: "x"})


def configure_mcp(monkeypatch):
    monkeypatch.setenv("BENCHPROOF_MCP_CONNECTIONS", json.dumps([{"id": "docs", "name": "Docs", "url": "https://example.org/mcp", "tools": ["search"]}]))
    monkeypatch.setenv("BENCHPROOF_MCP_QUERIES_PER_DAY", "1")


def test_mcp_query_is_explicit_bounded_read_only_and_pinned(monkeypatch, tmp_path):
    configure_mcp(monkeypatch)
    calls = []
    def rpc(connection, method, parameters):
        calls.append((method, parameters))
        if method == "tools/list": return {"tools": [{"name": "search", "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}]}
        return {"content": [{"type": "text", "text": "Public docs result"}]}
    monkeypatch.setattr(mcp, "rpc", rpc)
    query = mcp.MCPQuery(connection="docs", tool="search", arguments={"query": "decimal"}, consent=True)
    result = mcp.query_context(tmp_path / "mcp.db", "owner", query)
    assert result.content == "Public docs result"
    assert result.sha256 == hashlib.sha256(result.content.encode()).hexdigest()
    assert [call[0] for call in calls] == ["tools/list", "tools/call"]
    with pytest.raises(mcp.MCPError, match="allowance"): mcp.query_context(tmp_path / "mcp.db", "another-owner", query)
    assert len(calls) == 2


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fd00::1"])
def test_mcp_rejects_private_dns_before_connection(monkeypatch, address):
    monkeypatch.setattr(mcp.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, (address, 443))])
    with pytest.raises(mcp.MCPError, match="public"): mcp.public_addresses("example.org")


@pytest.mark.parametrize("consent", [False, 1, "true"])
def test_mcp_requires_explicit_boolean_consent(consent):
    with pytest.raises(ValidationError): mcp.MCPQuery(connection="docs", tool="search", consent=consent)


def test_mcp_denies_mutating_tools_without_call(monkeypatch, tmp_path):
    configure_mcp(monkeypatch)
    calls = []
    monkeypatch.setattr(mcp, "rpc", lambda connection, method, parameters: calls.append(method) or {"tools": [{"name": "search", "annotations": {"readOnlyHint": False}}]})
    with pytest.raises(mcp.MCPError, match="read-only"):
        mcp.query_context(tmp_path / "mcp.db", "owner", mcp.MCPQuery(connection="docs", tool="search", consent=True))
    assert calls == ["tools/list"]


@pytest.mark.parametrize("schema,value", [({"type": "object", "properties": {}}, {"unknown": 1}), ({"type": "integer"}, True), ({"$ref": "http://example.org"}, {}), ({"type": "string", "maxLength": 2}, "long")])
def test_mcp_validates_arguments_without_schema_fetch(schema, value):
    with pytest.raises(mcp.MCPError): mcp.validate_arguments(value, schema)


def test_imported_worker_filename_uses_project_loop_without_host_execution(tmp_path):
    from benchproof.coding.contracts import OperatorLimits
    from benchproof.coding.engine import CodingEngine
    from benchproof.coding.generation import CodingPlan
    from benchproof.coding.store import CodingStore
    from benchproof.coding.worker import CodingWorker
    from benchproof.execution.project_runner import PROJECT_CONTRACT_HASH
    from benchproof.projects.store import ProjectStore

    database = tmp_path / "project.db"
    project = ProjectStore(database).create_project(owner_ref="owner", name="Worker module", files=FILES, runner_profile="unittest")
    store = CodingStore(database, OperatorLimits(model_calls_per_day=10, executions_per_day=10))
    brief = CodingBrief(task="Change VALUE to 2", source_hash=project.source_hash, editable_paths=["app/worker.py"])
    task = store.create_task("owner", project.project_id, brief, project.files, PROJECT_CONTRACT_HASH, "create")
    calls = []
    class Provider:
        def complete(self, **kwargs):
            payload = json.loads(kwargs["user_prompt"])
            calls.append(payload)
            if "brief" in payload:
                result = {"source_hash": brief.source_hash, "brief_hash": brief.identity(), "steps": ["Change the constant"], "target_files": brief.editable_paths, "check_profile": "project-unittest-v1"}
            else:
                result = {"source_hash": brief.source_hash, "plan_hash": payload["plan_hash"], "files": [{"path": "app/worker.py", "content": "VALUE = 2\n"}], "explanation": "Changed the requested constant"}
            return {"content": json.dumps(result), "finish_reason": "stop", "response_model": "synthetic", "usage": {"total_tokens": 10}}
    executions = []
    def observe(snapshot, timeout_s):
        executions.append(snapshot.source_hash)
        passed = "VALUE = 2" in (snapshot.app_dir / "worker.py").read_text()
        results = {"test_count": 1, "passed": ["required-test"] if passed else [], "failures": [] if passed else [{"test_id": "required-test", "traceback": "Value must be two"}], "errors": [], "skipped": []}
        return ExecutionResult("synthetic", snapshot.run_id, 0, False, 1, "", "", {"test_results": results}, isolation={"enforced": True})
    class ForbiddenInvoice:
        def run(self, *args, **kwargs): pytest.fail("Imported worker.py was routed to invoice checks")
        def cancel(self, operation): return True
    executor = DispatchingExecutor(ForbiddenInvoice(), ProjectExecutor(synthetic_runner=observe))
    engine = CodingEngine(client=Provider(), model_id="synthetic", executor=executor, synthetic=True)
    worker = CodingWorker(store, engine)
    store.enqueue("owner", task["task_id"], "plan", phase="plan")
    worker.run_once()
    planned = store.get_task("owner", task["task_id"])
    store.approve_plan("owner", task["task_id"], CodingPlan.model_validate(planned["plan"]).identity())
    store.enqueue("owner", task["task_id"], "start", phase="run")
    _drain(worker)
    final = store.get_task("owner", task["task_id"])
    assert final["state"] == "REVIEW_READY"
    assert len(calls) == 2 and len(executions) == 3
    assert executions[0] == brief.source_hash
    assert executions[1] == executions[2] != executions[0]
    assert final["source_files"] == project.files


def test_extension_http_routes_require_owner_and_do_not_leak_credentials(client, monkeypatch):
    configure_mcp(monkeypatch)
    monkeypatch.setenv("BENCHPROOF_MCP_TOKEN_DOCS", "synthetic-not-a-real-secret")
    response = client.get("/api/v1/coding-tasks/extensions/catalog")
    assert response.status_code == 200
    assert response.json()["mcp_connections"][0] == {"id": "docs", "name": "Docs", "tools": ["search"]}
    assert "synthetic-not-a-real-secret" not in response.text
    client.headers.pop("X-BenchProof-Owner")
    assert client.get("/api/v1/coding-tasks/extensions/catalog").status_code == 401


@pytest.mark.parametrize("mode", ["success", "redirect", "sse", "oversized", "mismatched-id", "rpc-error", "invalid-json"])
def test_mcp_transport_is_bounded_and_fails_closed(monkeypatch, mode):
    monkeypatch.setattr(mcp, "public_addresses", lambda host: ["93.184.216.34"])
    requests = []
    class Transport:
        sock = None
        closed = False
        def __init__(self, host, address):
            assert (host, address) == ("example.org", "93.184.216.34")
        def request(self, method, path, payload, headers):
            requests.append((method, path, json.loads(payload), headers))
        def getresponse(self):
            payload = requests[-1][2]
            body = {"jsonrpc": "2.0", "id": payload["id"], "result": {"tools": []}}
            if mode == "mismatched-id": body["id"] = "wrong-id"
            if mode == "rpc-error": body["error"] = {"message": "secret-error-must-not-be-exposed"}
            data = b"x" * 32_769 if mode == "oversized" else b"invalid" if mode == "invalid-json" else json.dumps(body).encode()
            return SimpleNamespace(status=302 if mode == "redirect" else 200,
                                   getheader=lambda *args: "text/event-stream" if mode == "sse" else "application/json",
                                   read1=io.BytesIO(data).read)
        def close(self): Transport.closed = True
    monkeypatch.setattr(mcp, "PinnedHTTPSConnection", Transport)
    connection = mcp.MCPConnection(id="docs", name="Docs", url="https://example.org/mcp", tools=["search"])
    if mode == "success": assert mcp.rpc(connection, "tools/list", {}) == {"tools": []}
    else:
        with pytest.raises(mcp.MCPError) as caught: mcp.rpc(connection, "tools/list", {})
        assert "secret-error" not in str(caught.value)
    assert len(requests) == 1 and Transport.closed
    assert requests[0][0:2] == ("POST", "/mcp")
    assert "Authorization" not in requests[0][3]
    assert requests[0][3]["MCP-Protocol-Version"] == "2026-07-28"
    assert requests[0][3]["Mcp-Method"] == "tools/list"


@pytest.mark.parametrize("name,expected", [("read_guide", "read_guide"), ("日本語", "=?base64?5pel5pys6Kqe?="), ("=?base64?literal?=", "=?base64?PT9iYXNlNjQ/bGl0ZXJhbD89?=")])
def test_mcp_tool_name_header_is_encoded_without_injection(monkeypatch, name, expected):
    monkeypatch.setattr(mcp, "public_addresses", lambda host: ["93.184.216.34"])
    calls = []
    class Transport:
        sock = None
        def __init__(self, *args): pass
        def request(self, method, path, payload, headers): calls.append((json.loads(payload), headers))
        def getresponse(self):
            payload = json.dumps({"jsonrpc": "2.0", "id": calls[0][0]["id"], "result": {"content": []}}).encode()
            return SimpleNamespace(status=200, getheader=lambda *args: "application/json", read1=io.BytesIO(payload).read)
        def close(self): pass
    monkeypatch.setattr(mcp, "PinnedHTTPSConnection", Transport)
    connection = mcp.MCPConnection(id="docs", name="Docs", url="https://example.org/mcp", tools=[name])
    mcp.rpc(connection, "tools/call", {"name": name, "arguments": {}})
    assert calls[0][1]["Mcp-Method"] == "tools/call"
    assert calls[0][1]["Mcp-Name"] == expected


def test_mcp_mixed_dns_and_unsupported_schema_are_rejected(monkeypatch):
    monkeypatch.setattr(mcp.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, (address, 443)) for address in ["93.184.216.34", "127.0.0.1"]])
    with pytest.raises(mcp.MCPError): mcp.public_addresses("example.org")
    with pytest.raises(mcp.MCPError): mcp.validate_arguments("text", {"type": "string", "pattern": "^allowed$"})
    with pytest.raises(mcp.MCPError): mcp.validate_arguments([], {"type": "array", "items": {"type": "string"}, "minItems": 1})


@pytest.mark.parametrize("url", ["http://example.org", "https://user:password@example.org/mcp", "https://example.org/mcp?token=secret", "https://example.org:444/mcp"])
def test_mcp_operator_urls_reject_unsafe_configuration(monkeypatch, url):
    monkeypatch.setenv("BENCHPROOF_MCP_CONNECTIONS", json.dumps([{"id": "docs", "name": "Docs", "url": url, "tools": ["search"]}]))
    with pytest.raises(mcp.MCPError): mcp.connections()


def test_mcp_disabled_quota_makes_no_requests(monkeypatch, tmp_path):
    configure_mcp(monkeypatch)
    monkeypatch.setenv("BENCHPROOF_MCP_QUERIES_PER_DAY", "0")
    monkeypatch.setattr(mcp, "rpc", lambda *args: pytest.fail("Network request made without quota"))
    with pytest.raises(mcp.MCPError, match="disabled"):
        mcp.query_context(tmp_path / "mcp.db", "owner", mcp.MCPQuery(connection="docs", tool="search", consent=True))
