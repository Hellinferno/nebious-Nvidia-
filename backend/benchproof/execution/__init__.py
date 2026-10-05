"""Execution adapters — the protected boundary between BenchProof and candidate code.

Interface names (prepare / run_observation / cancel / collect_artifacts) are
BenchProof's own. Implementations:

  DockerRunner   local isolated container (development alternate; see DECISIONS D-024)
  MockRunner     labeled mock, executes nothing
  (Contree)      Nebius Sandboxes — blocked until the account gains spawn permission

Candidate snapshots contain only the fixture's `app/` tree. The launcher that
observes the candidate lives outside that tree and is mounted read-only.
"""

from __future__ import annotations

from benchproof.execution.base import (
    ExecutionAdapter,
    ExecutionResult,
    RunnerUnavailable,
    Snapshot,
    prepare_snapshot,
)
from benchproof.execution.mock_runner import MockRunner

__all__ = [
    "ExecutionAdapter",
    "ExecutionResult",
    "MockRunner",
    "RunnerUnavailable",
    "Snapshot",
    "prepare_snapshot",
]
