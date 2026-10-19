"""Authenticated trusted origin running inside a persistent Vercel Sandbox."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


class OriginGuard:
    def __init__(self, app, token: str):
        if len(token) < 32:
            raise ValueError("A strong origin token is required")
        self.app = app
        self.token = token.encode("utf-8")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            tokens = [value for name, value in scope.get("headers", []) if name.lower() == b"x-benchproof-origin"]
            if len(tokens) != 1 or not hmac.compare_digest(tokens[0], self.token):
                await JSONResponse({"detail": {"code": "ORIGIN_DENIED"}}, status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    os.environ.update({
        "NEBIUS_API_KEY": config["nebius_api_key"],
        "NEBIUS_BASE_URL": "https://api.tokenfactory.nebius.com/v1/",
        "NEBIUS_MODEL_ID": config["model_id"],
        "BENCHPROOF_RUNNER": "docker",
        "DATABASE_PATH": "/data/benchproof/benchproof.db",
    })
    coding = config.get("coding")
    if coding is not None:
        os.environ.update({
            "BENCHPROOF_CODING_ENABLED": "true" if coding["enabled"] is True else "false",
            "BENCHPROOF_CODING_MODEL_CALLS_PER_DAY": str(int(coding["model_calls_per_day"])),
            "BENCHPROOF_CODING_EXECUTIONS_PER_DAY": str(int(coding["executions_per_day"])),
            "BENCHPROOF_CODING_DEADLINE_EPOCH": str(float(coding["deadline_epoch"])),
            "BENCHPROOF_CODING_OUTPUT_TOKENS": str(int(coding["output_tokens"])),
        })
    working = Path("/data/benchproof/runtime")
    working.mkdir(parents=True, exist_ok=True)
    os.chdir(working)

    from benchproof.api.main import app, settings
    from scripts.serve_demo import DemoServer

    if not settings.provider_configured:
        raise ValueError("Nebius configuration is required")
    guarded = OriginGuard(
        DemoServer(app, ROOT / "frontend" / "dist", Path("/data/benchproof/limits.db"), config["daily_actions"]),
        config["origin_token"],
    )
    import uvicorn

    worker = subprocess.Popen(
        [sys.executable, str(ROOT / "backend" / "scripts" / "start_worker.py")],
        cwd=working,
        env=os.environ.copy(),
    )
    try:
        uvicorn.run(guarded, host="0.0.0.0", port=8765, workers=1, access_log=False)
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
