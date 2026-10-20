"""Versioned instruction/context snapshots and trusted orchestration policies."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SkillContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    description: str = Field(min_length=1, max_length=512)
    instructions: str = Field(min_length=1, max_length=2_000)

    def identity(self) -> str:
        text = f"{self.name}\n{self.description}\n{self.instructions}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ExternalContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    connection: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")
    tool: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2_000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def verify_content(self) -> ExternalContext:
        if hashlib.sha256(self.content.encode("utf-8")).hexdigest() != self.sha256:
            raise ValueError("External context hash does not match its content")
        return self


HarnessId = Literal["bounded-v1", "single-pass-v1"]


@dataclass(frozen=True)
class HarnessPolicy:
    harness_id: str
    title: str
    description: str
    max_patch_attempts: int

    def allows_revision(self, attempts: int) -> bool:
        return attempts < self.max_patch_attempts


HARNESSES = {
    "bounded-v1": HarnessPolicy(
        "bounded-v1", "Bounded repair loop", "Revise a failed candidate within the approved limits.", 2,
    ),
    "single-pass-v1": HarnessPolicy(
        "single-pass-v1", "Single-pass changes", "One candidate only; stop on failed checks instead of revising.", 1,
    ),
}


def harness_policy(harness_id: str) -> HarnessPolicy:
    try:
        return HARNESSES[harness_id]
    except KeyError as exc:
        raise ValueError("Unsupported harness; only reviewed built-in adapters are available") from exc
