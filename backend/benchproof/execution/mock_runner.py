"""Labeled mock runner. Executes nothing; returns caller-supplied observations."""

from __future__ import annotations

from typing import Any

from benchproof.execution.base import ExecutionResult, Snapshot


class MockRunner:
    name = "mock"

    def __init__(self, canned: dict[str, Any] | None = None) -> None:
        self.canned = canned
        self.calls: list[dict[str, Any]] = []

    def available(self) -> tuple[bool, str]:
        return True, "mock runner: no candidate execution"

    def run_observation(self, snapshot: Snapshot, timeout_s: int = 60, **kwargs: Any) -> ExecutionResult:
        self.calls.append({"run_id": snapshot.run_id, "timeout_s": timeout_s, **kwargs})
        return ExecutionResult(
            runner=self.name,
            run_id=snapshot.run_id,
            exit_code=0 if self.canned is not None else None,
            timed_out=False,
            duration_ms=0,
            stdout="",
            stderr="",
            observations=self.canned,
            image_ref=None,
            isolation={"enforced": False, "note": "MOCK — nothing was executed"},
            error=None if self.canned is not None else "mock runner has no canned observations",
        )

    def cancel(self, run_id: str) -> bool:
        return False

    def collect_artifacts(self, snapshot: Snapshot) -> list:
        return []
