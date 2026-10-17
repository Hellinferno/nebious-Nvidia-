"""Serve the built frontend and API on one localhost port for a small tunnel demo."""

from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class DemoServer:
    def __init__(self, api: ASGIApp, frontend: Path, limit_db: Path, daily_limit: int = 60):
        if not (frontend / "index.html").is_file():
            raise ValueError("Frontend build missing; run npm run build in frontend first")
        if daily_limit < 1:
            raise ValueError("daily_limit must be positive")
        self.api = api
        self.static = ExceptionMiddleware(StaticFiles(directory=frontend, html=True))
        self.limit_db = limit_db
        self.daily_limit = daily_limit
        self.action_lock = asyncio.Lock()
        limit_db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(limit_db) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS demo_actions (day TEXT PRIMARY KEY, used INTEGER NOT NULL)"
            )

    def reserve_action(self) -> bool:
        day = datetime.now(UTC).date().isoformat()
        with sqlite3.connect(self.limit_db, timeout=5) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO demo_actions(day, used) VALUES (?, 0)", (day,))
            changed = connection.execute(
                "UPDATE demo_actions SET used=used+1 WHERE day=? AND used<?",
                (day, self.daily_limit),
            ).rowcount
        return changed == 1

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.api(scope, receive, send)
            return
        path = scope.get("path", "")
        if not path.startswith("/api/"):
            await self.static(scope, receive, send)
            return
        is_action = scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}
        is_action = is_action or (scope["method"] == "GET" and path.endswith("/replay"))
        if not is_action:
            await self.api(scope, receive, send)
            return
        if scope["method"] == "POST" and path.endswith("/cancel"):
            await self.api(scope, receive, send)
            return
        if self.action_lock.locked():
            response = JSONResponse(
                {"detail": {"code": "DEMO_BUSY", "message": "Another demo action is running; try again shortly"}},
                status_code=429,
                headers={"Retry-After": "5"},
            )
            await response(scope, receive, send)
            return
        async with self.action_lock:
            if not self.reserve_action():
                response = JSONResponse(
                    {"detail": {"code": "DEMO_DAILY_LIMIT", "message": "The shared daily demo action limit is reached"}},
                    status_code=429,
                )
                await response(scope, receive, send)
                return
            await self.api(scope, receive, send)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--daily-actions", type=int, default=60)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "artifacts" / "public-demo")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    data_dir = args.data_dir.resolve()
    os.environ["DATABASE_PATH"] = str(data_dir / "benchproof.db")
    os.environ["BENCHPROOF_RUNNER"] = "docker"

    from benchproof.api.main import app, settings
    from benchproof.execution.docker_runner import DockerRunner

    if not settings.provider_configured:
        print("Live Nebius provider configuration is required", file=sys.stderr)
        return 2
    available, detail = DockerRunner().available()
    if not available:
        print(f"RUNNER_UNAVAILABLE: {detail}", file=sys.stderr)
        return 2
    demo = DemoServer(app, ROOT / "frontend" / "dist", data_dir / "limits.db", args.daily_actions)

    import uvicorn

    worker = subprocess.Popen(
        [sys.executable, str(BACKEND / "scripts" / "start_worker.py")],
        cwd=BACKEND,
        env=os.environ.copy(),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        print(f"Demo: http://127.0.0.1:{args.port}; shared limit {args.daily_actions} actions/day (UTC)")
        print(f"Persistent demo data: {data_dir}")
        uvicorn.run(demo, host="127.0.0.1", port=args.port, workers=1, access_log=False)
    finally:
        worker.terminate()
        try:
            worker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
