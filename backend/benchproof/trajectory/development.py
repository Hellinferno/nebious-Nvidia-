"""Frozen development-only W8 trajectory sources and human labels."""

from __future__ import annotations

from typing import Any

from benchproof.trajectory import RECOVERY_STRATEGY, TraceStep

SUITE_ID = "trajectory-w8-v1"
FROZEN_AT = "2026-10-13"


def _step(**overrides: Any) -> TraceStep:
    values: dict[str, Any] = {
        "source_hash": "source-v1",
        "tool": "observe_invoice",
        "arguments": {"constraint": "C-AMOUNT"},
        "failure_category": "CHECK_FAILURE",
        "failed_check_ids": ["amount-boundary"],
        "affected_constraints": ["C-AMOUNT"],
        "salient_detail": "expected 0.01, observed 0.02",
        "observation_fingerprints": ["obs-amount-002"],
    }
    values.update(overrides)
    return TraceStep(**values)


def development_traces() -> list[dict[str, Any]]:
    """Return four true stalls and four legitimate-progress controls."""
    return [
        {
            "trace_id": "W8-S1",
            "label": "STALLED",
            "reason": "request IDs differ but the semantic attempt is identical",
            "steps": [
                _step(arguments={"constraint": "C-AMOUNT", "request_id": "req-abcdef12"}),
                _step(arguments={"constraint": "C-AMOUNT", "request_id": "req-fedcba21"}),
            ],
        },
        {
            "trace_id": "W8-S2",
            "label": "STALLED",
            "reason": "timestamps differ but the timeout failure is identical",
            "steps": [
                _step(salient_detail="timeout at 2026-10-13T10:00:00Z"),
                _step(salient_detail="timeout at 2026-10-13T10:05:00Z"),
            ],
        },
        {
            "trace_id": "W8-S3",
            "label": "STALLED",
            "reason": "same API check failure without new evidence",
            "steps": [
                _step(failed_check_ids=["api-field-presence"]),
                _step(failed_check_ids=["api-field-presence"]),
            ],
        },
        {
            "trace_id": "W8-S4",
            "label": "STALLED",
            "reason": "same runner timeout without a new observation",
            "steps": [
                _step(failure_category="RUNNER_TIMEOUT", observation_fingerprints=[]),
                _step(failure_category="RUNNER_TIMEOUT", observation_fingerprints=[]),
            ],
        },
        {
            "trace_id": "W8-P1",
            "label": "PROGRESSING",
            "reason": "source version changed",
            "steps": [_step(), _step(source_hash="source-v2")],
        },
        {
            "trace_id": "W8-P2",
            "label": "PROGRESSING",
            "reason": "recovery uses a genuinely different named strategy",
            "steps": [_step(), _step(strategy=RECOVERY_STRATEGY)],
        },
        {
            "trace_id": "W8-P3",
            "label": "PROGRESSING",
            "reason": "one check resolved even though another still fails",
            "steps": [
                _step(failed_check_ids=["amount-boundary", "caller-consistency"]),
                _step(
                    failed_check_ids=["caller-consistency"],
                    resolved_check_ids=["amount-boundary"],
                ),
            ],
        },
        {
            "trace_id": "W8-P4",
            "label": "PROGRESSING",
            "reason": "new semantic observation was added",
            "steps": [
                _step(),
                _step(observation_fingerprints=["obs-amount-002", "obs-caller-new"]),
            ],
        },
    ]
