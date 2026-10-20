import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

MODULE_PATH = Path(__file__).resolve().parents[2] / "deployment" / "vercel" / "origin.py"
SPEC = importlib.util.spec_from_file_location("vercel_origin", MODULE_PATH)
origin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(origin)


def test_origin_denies_missing_wrong_and_duplicate_tokens_before_action():
    calls = []

    async def endpoint(request):
        calls.append(True)
        return JSONResponse({"ok": True})

    secret = "x" * 48
    guarded = origin.OriginGuard(Starlette(routes=[Route("/api/v1/action", endpoint, methods=["POST"])]), secret)
    with TestClient(guarded) as client:
        assert client.post("/api/v1/action").status_code == 403
        assert client.post("/api/v1/action", headers={"X-BenchProof-Origin": "wrong"}).status_code == 403
        assert client.post("/api/v1/action", headers=[("X-BenchProof-Origin", secret), ("X-BenchProof-Origin", secret)]).status_code == 403
        assert calls == []
        assert client.post("/api/v1/action", headers={"X-BenchProof-Origin": secret}).status_code == 200
        assert calls == [True]


def test_origin_requires_a_strong_secret():
    with pytest.raises(ValueError, match="strong origin token"):
        origin.OriginGuard(Starlette(), "short")


def test_origin_mcp_environment_is_disabled_by_default_and_preserves_only_dedicated_credentials():
    assert origin.mcp_environment(None) == {"BENCHPROOF_MCP_CONNECTIONS": "[]", "BENCHPROOF_MCP_QUERIES_PER_DAY": "0"}
    config = {"connections": [{"id": "docs", "name": "Docs", "url": "https://example.org/mcp", "tools": ["read_guide"], "token_env": "BENCHPROOF_MCP_TOKEN_DOCS"}], "queries_per_day": 5, "credentials": {"BENCHPROOF_MCP_TOKEN_DOCS": "synthetic-docs-token"}}
    result = origin.mcp_environment(config)
    assert result["BENCHPROOF_MCP_TOKEN_DOCS"] == "synthetic-docs-token"
    assert result["BENCHPROOF_MCP_QUERIES_PER_DAY"] == "5"
    config["credentials"]["NEBIUS_API_KEY"] = "must-not-be-copied"
    with pytest.raises(ValueError, match="dedicated"):
        origin.mcp_environment(config)


@pytest.mark.parametrize("allowance", [True, -1, 0, 21, "5"])
def test_origin_mcp_environment_rejects_unsafe_allowance(allowance):
    config = {"connections": [{"id": "docs", "name": "Docs", "url": "https://example.org/mcp", "tools": ["read_guide"]}], "queries_per_day": allowance, "credentials": {}}
    with pytest.raises(ValueError):
        origin.mcp_environment(config)
