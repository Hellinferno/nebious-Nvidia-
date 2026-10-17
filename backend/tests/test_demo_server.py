import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from scripts.serve_demo import DemoServer


def make_demo(tmp_path, limit=1):
    frontend = tmp_path / "web"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text("<h1>BenchProof</h1>", encoding="utf-8")

    async def endpoint(request):
        return JSONResponse({"status": "ok"})

    api = Starlette(routes=[
        Route("/api/v1/health", endpoint),
        Route("/api/v1/action", endpoint, methods=["POST"]),
        Route("/api/v1/audits/test/replay", endpoint),
        Route("/api/v1/audits/test/cancel", endpoint, methods=["POST"]),
    ])
    return DemoServer(api, frontend, tmp_path / "limits.db", limit)


def test_static_and_api_share_an_origin_without_exposing_source(tmp_path):
    demo = make_demo(tmp_path)
    (tmp_path / ".env").write_text("PRIVATE_CONFIG", encoding="utf-8")
    with TestClient(demo) as client:
        assert "BenchProof" in client.get("/").text
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        for path in ("/.env", "/../.env", "/%2e%2e/.env", "/backend/benchproof.db"):
            assert client.get(path).status_code == 404


def test_shared_cap_survives_restart_and_cancel_still_works(tmp_path):
    with TestClient(make_demo(tmp_path)) as client:
        assert client.post("/api/v1/action").status_code == 200
        assert client.post("/api/v1/action").status_code == 429
        assert client.get("/api/v1/audits/test/replay").status_code == 429
        assert client.post("/api/v1/audits/test/cancel").status_code == 200
        assert client.get("/api/v1/health").status_code == 200
    with TestClient(make_demo(tmp_path)) as restarted:
        assert restarted.post("/api/v1/action").json()["detail"]["code"] == "DEMO_DAILY_LIMIT"


def test_busy_action_rejects_concurrent_work_but_allows_cancel(tmp_path):
    demo = make_demo(tmp_path, limit=3)

    async def requests():
        async with demo.action_lock:
            scope = {"type": "http", "method": "POST", "path": "/api/v1/action", "headers": []}
            messages = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            await demo(scope, receive, send)
            assert messages[0]["status"] == 429
            assert b"DEMO_BUSY" in messages[1]["body"]

    asyncio.run(requests())
    assert demo.reserve_action() is True
    assert demo.reserve_action() is True
    assert demo.reserve_action() is True
    assert demo.reserve_action() is False


def test_missing_build_is_refused(tmp_path: Path):
    with pytest.raises(ValueError, match="Frontend build missing"):
        DemoServer(Starlette(), tmp_path, tmp_path / "limits.db")
