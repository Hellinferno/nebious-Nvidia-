"""Nebius Token Factory inference adapter (OpenAI-compatible). Narrow and bounded.

Credentials are read from the environment only. Missing credentials raise
ProviderError; nothing here ever substitutes a mock.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
_PLACEHOLDER_KEYS = {"", "your_api_key_here"}
_REPO_ROOT = Path(__file__).resolve().parents[3]


class ProviderError(Exception):
    pass


class NebiusAdapter:
    """Wraps the Nebius Token Factory OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 30.0,
    ):
        load_dotenv(dotenv_path=_REPO_ROOT / ".env")
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY", "")
        self.base_url = base_url or os.getenv("NEBIUS_BASE_URL", "").strip() or DEFAULT_BASE_URL
        if self.api_key in _PLACEHOLDER_KEYS:
            raise ProviderError("NEBIUS_API_KEY not configured")
        self._client = OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=timeout_s, max_retries=0
        )

    # ── Catalog ──────────────────────────────────────────────────────────

    def list_models(self) -> list[dict[str, Any]]:
        try:
            models = self._client.models.list()
        except Exception as e:
            raise ProviderError(f"Catalog request failed: {type(e).__name__}") from e
        return [{"id": m.id, "owned_by": getattr(m, "owned_by", None)} for m in models.data]

    # ── Bounded inference ────────────────────────────────────────────────

    def complete(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.0,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """One bounded chat completion. Returns sanitized metadata (no credentials)."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        started = time.perf_counter()
        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            raise ProviderError(f"Inference failed: {type(e).__name__}: {e}") from e
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        choice = response.choices[0]
        usage = response.usage
        return {
            "requested_model": model,
            "response_model": getattr(response, "model", None),
            "response_id": getattr(response, "id", None),
            "content": choice.message.content or "",
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
            },
            "elapsed_ms": elapsed_ms,
            "base_url": self.base_url,
        }
