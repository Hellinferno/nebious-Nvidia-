"""Bounded read-only MCP context access; no shell servers or model sampling."""

from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import os
import socket
import sqlite3
import ssl
import time
import uuid
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from benchproof.coding.extensions import ExternalContext


class MCPError(Exception):
    pass


class MCPConnection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=1, max_length=500)
    tools: list[str] = Field(min_length=1, max_length=10)
    token_env: str | None = Field(default=None, pattern=r"^BENCHPROOF_MCP_TOKEN_[A-Z0-9_]+$")

    @field_validator("tools")
    @classmethod
    def bounded_tools(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or any(not 1 <= len(name) <= 100 for name in value):
            raise ValueError("Tool names must be unique and contain 1–100 characters")
        return value


class MCPQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    connection: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")
    tool: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict, max_length=10)
    consent: Literal[True]

    @field_validator("consent", mode="before")
    @classmethod
    def explicit_consent(cls, value: Any) -> bool:
        if value is not True:
            raise ValueError("Explicit boolean consent is required")
        return True


def connections(raw: str | None = None) -> list[MCPConnection]:
    if raw is None:
        raw = os.getenv("BENCHPROOF_MCP_CONNECTIONS", "[]")
    try:
        if len(raw) > 16_384:
            raise ValueError()
        values = json.loads(raw)
        if not isinstance(values, list) or len(values) > 5:
            raise ValueError()
        configured = [MCPConnection.model_validate(value) for value in values]
        if len({item.id for item in configured}) != len(configured):
            raise ValueError()
        for item in configured:
            target = urlsplit(item.url)
            if target.scheme != "https" or not target.hostname or target.username or target.password or target.fragment or target.query or target.port not in {None, 443}:
                raise ValueError()
        return configured
    except (ValueError, TypeError) as exc:
        raise MCPError("MCP operator configuration is invalid") from exc


def public_addresses(host: str) -> list[str]:
    try:
        addresses = list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    except OSError as exc:
        raise MCPError("MCP server DNS lookup failed") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise MCPError("MCP servers must resolve exclusively to public addresses")
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str) -> None:
        super().__init__(host, timeout=8, context=ssl.create_default_context())
        self.address = address

    def connect(self) -> None:
        transport = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(transport, server_hostname=self.host)
        except BaseException:
            transport.close()
            raise


def rpc(connection: MCPConnection, method: str, parameters: dict[str, Any]) -> dict[str, Any]:
    target = urlsplit(connection.url)
    host = target.hostname
    if not host or target.scheme != "https":
        raise MCPError("Invalid MCP endpoint")
    addresses = public_addresses(host)
    request_id = uuid.uuid4().hex
    metadata = {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {"name": "benchproof-context", "version": "1"},
    }
    payload = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method,
                          "params": {**parameters, "_meta": metadata}}).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json",
               "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": method}
    if method == "tools/call":
        name = parameters.get("name")
        if not isinstance(name, str) or not 1 <= len(name) <= 100:
            raise MCPError("Invalid MCP tool name")
        plain = name == name.strip() and all(32 <= ord(character) <= 126 for character in name)
        sentinel = name.startswith("=?base64?") and name.endswith("?=")
        headers["Mcp-Name"] = name if plain and not sentinel else "=?base64?" + base64.b64encode(name.encode()).decode() + "?="
    if connection.token_env:
        token = os.getenv(connection.token_env, "")
        if not token or "\r" in token or "\n" in token:
            raise MCPError("The MCP connection credential is unavailable")
        headers["Authorization"] = f"Bearer {token}"
    transport = PinnedHTTPSConnection(host, addresses[0])
    deadline = time.monotonic() + 12
    try:
        transport.request("POST", target.path or "/", payload, headers)
        response = transport.getresponse()
        if response.status != 200 or "application/json" not in response.getheader("Content-Type", ""):
            raise MCPError("MCP requires a successful stateless JSON response (protocol 2026-07-28)")
        raw = bytearray()
        while len(raw) <= 32_768:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError("MCP response deadline exceeded")
            if transport.sock is not None:
                transport.sock.settimeout(min(8, remaining))
            chunk = response.read1(min(4096, 32_769 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        if len(raw) > 32_768:
            raise MCPError("MCP response exceeds 32 KiB")
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("id") != request_id or value.get("jsonrpc") != "2.0" or "error" in value or not isinstance(value.get("result"), dict):
            raise MCPError("MCP returned an invalid or error response")
        return value["result"]
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise MCPError("MCP request failed; no automatic retry was made") from exc
    finally:
        transport.close()


def validate_arguments(value: Any, schema: dict[str, Any], depth: int = 0) -> None:
    allowed_keys = {"type", "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
                    "minLength", "maxLength", "minimum", "maximum", "enum", "description", "title", "default", "examples", "$schema"}
    if not isinstance(schema, dict) or depth > 4 or set(schema) - allowed_keys:
        raise MCPError("This MCP argument schema is unsupported")
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    if kind not in types or not isinstance(value, types[kind]) or (kind in {"integer", "number"} and type(value) is bool):
        raise MCPError("MCP arguments do not match the declared schema")
    if "enum" in schema and value not in schema["enum"]:
        raise MCPError("MCP argument is outside its declared choices")
    if kind == "object":
        properties = schema.get("properties", {})
        if not isinstance(properties, dict) or len(value) > 10 or set(value) - set(properties) or not set(schema.get("required", [])) <= set(value):
            raise MCPError("MCP arguments contain missing or unsupported fields")
        for key, child in value.items():
            validate_arguments(child, properties[key], depth + 1)
    elif kind == "array":
        if not schema.get("minItems", 0) <= len(value) <= min(schema.get("maxItems", 10), 10):
            raise MCPError("Too many MCP argument items")
        for child in value:
            validate_arguments(child, schema.get("items", {}), depth + 1)
    elif kind == "string" and not schema.get("minLength", 0) <= len(value) <= min(schema.get("maxLength", 1000), 1000):
        raise MCPError("MCP argument text is outside its bounds")
    elif kind in {"integer", "number"} and not schema.get("minimum", float("-inf")) <= value <= schema.get("maximum", float("inf")):
        raise MCPError("MCP numeric argument is outside its bounds")


def reserve_query(database: Path, owner: str) -> None:
    try:
        allowance = int(os.getenv("BENCHPROOF_MCP_QUERIES_PER_DAY", "0"))
    except ValueError as exc:
        raise MCPError("MCP query allowance is not configured") from exc
    if not 1 <= allowance <= 20:
        raise MCPError("MCP calls are disabled; the operator must configure a daily allowance")
    with sqlite3.connect(database, timeout=5) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS mcp_context_usage(day TEXT, owner TEXT, requests INTEGER, PRIMARY KEY(day,owner))")
        connection.execute("BEGIN IMMEDIATE")
        used = connection.execute("SELECT COALESCE(SUM(requests),0) FROM mcp_context_usage WHERE day=date('now')").fetchone()[0]
        if used >= allowance:
            raise MCPError("The global daily MCP query allowance is exhausted")
        connection.execute("INSERT INTO mcp_context_usage VALUES(date('now'),?,1) ON CONFLICT(day,owner) DO UPDATE SET requests=requests+1", (owner,))


def query_context(database: Path, owner: str, query: MCPQuery) -> ExternalContext:
    configured = next((item for item in connections() if item.id == query.connection), None)
    if configured is None or query.tool not in configured.tools:
        raise MCPError("MCP connection or tool is not operator-approved")
    if len(json.dumps(query.arguments).encode("utf-8")) > 2048:
        raise MCPError("MCP arguments exceed 2 KiB")
    reserve_query(database, owner)
    listing = rpc(configured, "tools/list", {})
    tools = listing.get("tools", [])
    if not isinstance(tools, list):
        raise MCPError("MCP tool catalog is invalid")
    tool = next((item for item in tools if isinstance(item, dict) and item.get("name") == query.tool), None)
    annotations = (tool or {}).get("annotations", {})
    if not isinstance(annotations, dict):
        raise MCPError("MCP tool permissions are invalid")
    if not tool or annotations.get("readOnlyHint") is not True or annotations.get("destructiveHint") is True:
        raise MCPError("Only explicitly read-only MCP tools are supported")
    try:
        validate_arguments(query.arguments, tool.get("inputSchema", {}))
    except (TypeError, ValueError, KeyError) as exc:
        raise MCPError("MCP argument schema is invalid") from exc
    result = rpc(configured, "tools/call", {"name": query.tool, "arguments": query.arguments})
    if result.get("isError"):
        raise MCPError("The MCP tool reported an error")
    blocks = result.get("content", [])
    if not isinstance(blocks, list) or any(not isinstance(block, dict) or block.get("type") != "text" or not isinstance(block.get("text"), str) for block in blocks):
        raise MCPError("Only text MCP results are supported")
    content = "\n".join(block["text"] for block in blocks)
    if not content or len(content) > 2000:
        raise MCPError("MCP context must contain 1–2,000 characters; no truncation was applied")
    return ExternalContext(connection=configured.id, tool=query.tool, content=content,
                           sha256=hashlib.sha256(content.encode("utf-8")).hexdigest())
