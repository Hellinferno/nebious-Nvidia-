"""Bound coding-task request bodies before downstream parsing or mutation."""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CodingBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = 65_536, max_project_bytes: int = 262_144) -> None:
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("max_bytes must be a positive integer")
        if type(max_project_bytes) is not int or max_project_bytes < 1:
            raise ValueError("max_project_bytes must be a positive integer")
        self.app = app
        self.max_bytes = max_bytes
        self.max_project_bytes = max_project_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        is_coding = path == "/api/v1/coding-tasks" or path.startswith("/api/v1/coding-tasks/")
        is_project = path == "/api/v1/projects" or path.startswith("/api/v1/projects/")
        if scope["type"] != "http" or not (is_coding or is_project):
            await self.app(scope, receive, send)
            return

        effective_limit = self.max_project_bytes if is_project else self.max_bytes
        buffered = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(buffered) + len(chunk) > effective_limit:
                await JSONResponse(
                    {"detail": {
                        "code": "SOURCE_LIMIT",
                        "message": "Request body exceeds the byte limit",
                    }},
                    status_code=413,
                )(scope, receive, send)
                return
            buffered.extend(chunk)
            if not message.get("more_body", False):
                break

        body = bytes(buffered)
        pending = True

        async def replay_receive() -> Message:
            nonlocal pending
            if pending:
                pending = False
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)
