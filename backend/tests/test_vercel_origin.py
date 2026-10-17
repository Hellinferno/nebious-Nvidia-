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
