"""Fail-closed structured completions shared by the coding runtime."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

MAX_STRUCTURED_BYTES = 32_768


class ModelOutputError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def completion_metadata(response: dict[str, Any], requested_model: str) -> dict[str, Any]:
    usage = response.get("usage") or {}
    total = usage.get("total_tokens")
    return {
        "mode": "live",
        "provider": "nebius-token-factory",
        "requested_model": requested_model,
        "model_id": response.get("response_model") or requested_model,
        "response_id": response.get("response_id"),
        "finish_reason": response.get("finish_reason"),
        "usage": usage,
        "usage_status": "RECORDED" if type(total) is int and total >= 0 else "UNKNOWN",
        "elapsed_ms": response.get("elapsed_ms"),
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("Non-finite JSON number")


def validate_completion[OutputModel: BaseModel](
    response: dict[str, Any], schema: type[OutputModel]
) -> OutputModel:
    reason = response.get("finish_reason")
    if reason == "length":
        raise ModelOutputError(
            "MODEL_OUTPUT_TRUNCATED",
            "The model reached its output limit; no partial proposal was accepted."
            " Review the task scope or output allowance before explicitly trying again.",
        )
    if reason != "stop":
        raise ModelOutputError(
            "MODEL_OUTPUT_INCOMPLETE",
            "The provider did not return a completed text response; no proposal was accepted.",
        )
    content = response.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ModelOutputError("MALFORMED_ACTION", "The model returned no structured proposal.")
    try:
        if len(content.encode("utf-8")) > MAX_STRUCTURED_BYTES:
            raise ModelOutputError("MODEL_OUTPUT_LIMIT", "The model response exceeded the byte limit.")
        cleaned = content.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fenced:
            cleaned = fenced.group(1)
        payload = json.loads(
            cleaned, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        return schema.model_validate(payload)
    except (ValueError, RecursionError) as exc:
        raise ModelOutputError(
            "MALFORMED_ACTION",
            "The model response did not match the required JSON schema; no proposal was accepted.",
        ) from exc
