"""Versioned durable coding-task contracts and operator admission limits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from benchproof.coding.extensions import harness_policy
from benchproof.coding.generation import CodingBrief, CodingPlan, CodingPreferences

TaskState = Literal[
    "DRAFT", "QUEUED", "RUNNING", "AWAITING_APPROVAL", "APPROVED", "PAUSED",
    "INTERRUPTED", "CANCEL_PENDING", "CANCELLED", "BLOCKED", "FAILED", "STALLED",
    "BUDGET_EXHAUSTED", "REVIEW_READY",
]
ActionKind = Literal["PLAN", "EDIT", "EXECUTION"]


@dataclass(frozen=True)
class OperatorLimits:
    model_calls_per_day: int = 0
    executions_per_day: int = 0
    max_tasks: int = 100

    def __post_init__(self) -> None:
        for value in (self.model_calls_per_day, self.executions_per_day, self.max_tasks):
            if type(value) is not int or value < 0:
                raise ValueError("Operator limits must be nonnegative integers")
        if self.max_tasks > 100:
            raise ValueError("The prepared-project store supports at most 100 tasks")


@dataclass(frozen=True)
class TaskLimits:
    model_calls: int = 4
    patch_attempts: int = 2
    executions: int = 4
    active_seconds: int = 300

    @classmethod
    def for_brief(cls, brief: CodingBrief) -> TaskLimits:
        requested = brief.preferences.limits if brief.preferences is not None else None
        limits = requested.model_dump() if requested is not None else vars(cls()).copy()
        if brief.preferences is not None:
            limits["patch_attempts"] = min(limits["patch_attempts"], harness_policy(brief.preferences.harness).max_patch_attempts)
        return cls(**limits)


@dataclass(frozen=True)
class Lease:
    task_id: str
    worker_id: str
    fence: int


class CodingStoreError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ActionKind", "CodingBrief", "CodingPlan", "CodingPreferences", "CodingStoreError", "Lease", "OperatorLimits",
    "TaskLimits", "TaskState",
]
