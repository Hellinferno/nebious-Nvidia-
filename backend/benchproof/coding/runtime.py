"""Explicit operator admission; a heartbeat alone never enables paid coding work."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from benchproof.coding.contracts import OperatorLimits


@dataclass(frozen=True)
class CodingRuntimeConfig:
    enabled: bool = False
    model_calls_per_day: int = 0
    executions_per_day: int = 0
    max_tasks: int = 100
    deadline_epoch: float = 0
    max_output_tokens: int = 2_048

    def __post_init__(self) -> None:
        self.operator_limits()
        if not math.isfinite(self.deadline_epoch) or self.deadline_epoch < 0:
            raise ValueError("A finite trusted session deadline is required")
        if not 256 <= self.max_output_tokens <= 4_096:
            raise ValueError("Unsupported coding output allowance")

    def operator_limits(self) -> OperatorLimits:
        return OperatorLimits(
            model_calls_per_day=self.model_calls_per_day,
            executions_per_day=self.executions_per_day,
            max_tasks=self.max_tasks,
        )

    def seconds_remaining(self) -> float:
        return max(0.0, self.deadline_epoch - time.time())

    def blocked_reason(self, *, provider_configured: bool, runner_ready: bool) -> str | None:
        if not self.enabled:
            return "CODING_DISABLED"
        if self.model_calls_per_day <= 0 or self.executions_per_day <= 0:
            return "OPERATOR_LIMIT"
        if not provider_configured:
            return "PROVIDER_UNAVAILABLE"
        if not runner_ready:
            return "RUNNER_UNAVAILABLE"
        if self.seconds_remaining() < 330:
            return "SESSION_WINDOW_INSUFFICIENT"
        return None


ADMISSION_MESSAGES = {
    "CODING_DISABLED": "Coding tasks are not enabled on this deployment yet.",
    "OPERATOR_LIMIT": "The operator must configure nonzero daily model-call and execution allowances.",
    "PROVIDER_UNAVAILABLE": "The trusted coding provider is not configured; no fallback is used.",
    "RUNNER_UNAVAILABLE": "Coding tasks require the isolated Docker runner to be ready.",
    "SESSION_WINDOW_INSUFFICIENT": "A trusted runtime deadline with at least 330 seconds remaining is required.",
}
