from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from benchproof.api.body_limit import CodingBodyLimitMiddleware


def exercise(
    messages: list[dict[str, Any]],
    *,
    path: str = "/api/v1/coding-tasks",
    headers: list[tuple[bytes, bytes]] | None = None,
    max_bytes: int = 65_536,
    scope_type: str = "http",
    read_disconnect: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    received: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    remaining = list(messages)

    async def receive():
        message = remaining.pop(0) if remaining else {"type": "http.disconnect"}
        received.append(message)
        return message

    async def send(message):
        sent.append(message)

    async def app(scope, downstream_receive, downstream_send):
        call = {"scope": scope, "received_before_call": len(received)}
        calls.append(call)
        payload = bytearray()
        observed = []
        while True:
            message = await downstream_receive()
            observed.append(message)
            if message["type"] == "http.disconnect":
                break
            payload.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        if read_disconnect:
            observed.append(await downstream_receive())
        call.update(body=bytes(payload), messages=observed)
        await downstream_send({"type": "http.response.start", "status": 200, "headers": []})
        await downstream_send({"type": "http.response.body", "body": b"ok"})

    scope = {"type": scope_type, "method": "POST", "path": path, "headers": headers or []}
    asyncio.run(CodingBodyLimitMiddleware(app, max_bytes=max_bytes)(scope, receive, send))
    return calls, sent, received


@pytest.mark.parametrize("path", ["/api/v1/coding-tasks", "/api/v1/coding-tasks/task-1/start"])
def test_exact_default_limit_reaches_downstream_only_after_complete_body(path):
    messages = [
        {"type": "http.request", "body": b"a" * 32_768, "more_body": True},
        {"type": "http.request", "body": b"b" * 32_768, "more_body": False},
    ]
    calls, sent, received = exercise(messages, path=path)
    assert received == messages
    assert calls[0]["received_before_call"] == len(messages)
    assert calls[0]["body"] == b"a" * 32_768 + b"b" * 32_768
    assert len(calls[0]["messages"]) == 1
    assert sent[0]["status"] == 200


@pytest.mark.parametrize("headers", [[], [(b"content-length", b"0")], [(b"content-length", b"1")]])
def test_streamed_overflow_ignores_missing_or_false_content_length(headers):
    calls, sent, received = exercise([
        {"type": "http.request", "body": b"a" * 32_768, "more_body": True},
        {"type": "http.request", "body": b"b" * 32_769, "more_body": True},
        {"type": "http.request", "body": b"not consumed", "more_body": False},
    ], headers=headers)
    assert calls == []
    assert len(received) == 2
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["detail"]["code"] == "SOURCE_LIMIT"
    assert b"not consumed" not in sent[1]["body"]


def test_single_chunk_one_byte_over_limit_never_calls_downstream():
    calls, sent, _received = exercise([
        {"type": "http.request", "body": b"x" * 65_537, "more_body": False},
    ])
    assert calls == []
    assert sent[0]["status"] == 413


@pytest.mark.parametrize("value", [b"invalid", b"-1", b"9999999999999999999999999999", b"1, 1"])
def test_malformed_or_unsupported_length_headers_do_not_crash_or_override_bytes(value):
    headers = [(b"content-length", value), (b"transfer-encoding", b"chunked")]
    calls, sent, _received = exercise([
        {"type": "http.request", "body": b"{}", "more_body": False},
    ], headers=headers)
    assert calls[0]["body"] == b"{}"
    assert calls[0]["scope"]["headers"] == headers
    assert sent[0]["status"] == 200


def test_duplicate_length_headers_cannot_bypass_body_limit():
    calls, sent, _received = exercise([
        {"type": "http.request", "body": b"12345", "more_body": False},
    ], headers=[(b"content-length", b"1"), (b"content-length", b"1")], max_bytes=4)
    assert calls == []
    assert sent[0]["status"] == 413


@pytest.mark.parametrize("path", ["/api/v1/audits", "/api/v1/coding-tasks-extra", "/"])
def test_legacy_and_nonmatching_paths_preserve_original_receive_stream(path):
    messages = [
        {"type": "http.request", "body": b"first", "more_body": True},
        {"type": "http.request", "body": b"second", "more_body": False},
    ]
    calls, sent, _received = exercise(messages, path=path, max_bytes=1)
    assert calls[0]["messages"] == messages
    assert calls[0]["body"] == b"firstsecond"
    assert sent[0]["status"] == 200


@pytest.mark.parametrize("scope_type", ["websocket", "lifespan"])
def test_non_http_scopes_pass_through(scope_type):
    calls, sent, _received = exercise([
        {"type": "http.request", "body": b"12345", "more_body": False},
    ], max_bytes=1, scope_type=scope_type)
    assert calls[0]["scope"]["type"] == scope_type
    assert sent[0]["status"] == 200


def test_mid_body_disconnect_does_not_invoke_application_or_send_response():
    messages = [
        {"type": "http.request", "body": b"partial", "more_body": True},
        {"type": "http.disconnect"},
    ]
    calls, sent, received = exercise(messages)
    assert calls == []
    assert sent == []
    assert received == messages


def test_disconnect_after_complete_body_remains_available_to_application():
    calls, sent, _received = exercise([
        {"type": "http.request", "body": b"{}", "more_body": False},
        {"type": "http.disconnect"},
    ], read_disconnect=True)
    assert calls[0]["messages"][-1] == {"type": "http.disconnect"}
    assert sent[0]["status"] == 200


def test_empty_chunks_and_empty_request_are_supported():
    calls, sent, _received = exercise([
        *[{"type": "http.request", "body": b"", "more_body": True} for _ in range(100)],
        {"type": "http.request", "more_body": False},
    ], max_bytes=1)
    assert calls[0]["body"] == b""
    assert len(calls[0]["messages"]) == 1
    assert sent[0]["status"] == 200


@pytest.mark.parametrize("max_bytes", [0, -1, True, 1.5, "5"])
def test_invalid_limits_are_rejected(max_bytes):
    with pytest.raises(ValueError, match="positive integer"):
        CodingBodyLimitMiddleware(None, max_bytes=max_bytes)
