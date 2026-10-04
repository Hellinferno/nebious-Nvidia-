"""BenchProof domain schemas — v2 records for constraints, graph, audit, patches, checks."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────

class RunState(str, Enum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    ANALYZING = "ANALYZING"
    INVESTIGATING = "INVESTIGATING"
    PATCH_READY = "PATCH_READY"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    STALLED = "STALLED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class GateVerdict(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    NOT_RUN = "NOT_RUN"


class CheckOutcome(str, Enum):
    PASS_ = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class EdgeProvenance(str, Enum):
    OBSERVED = "OBSERVED"
    DECLARED = "DECLARED"
    INFERRED = "INFERRED"


class MutationOutcome(str, Enum):
    KILLED = "KILLED"
    SURVIVED = "SURVIVED"
    INVALID = "INVALID"
    INCONCLUSIVE = "INCONCLUSIVE"
    SKIPPED = "SKIPPED"


class DecisionStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"


class PatchPolicyResult(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


# ── Helpers ──────────────────────────────────────────────────────────────

def _canonical_hash(obj: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON (sorted keys, no whitespace)."""
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ── Constraint ───────────────────────────────────────────────────────────

class Constraint(BaseModel):
    schema_version: str = "benchproof/v2"
    constraint_id: str
    version: int = 1
    statement: str
    scope: list[str] = Field(default_factory=list)
    required: bool = True
    protected_check_ids: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    approval_ref: str = ""
    hash: str = ""

    def compute_hash(self) -> str:
        payload = self.model_dump(exclude={"hash"})
        self.hash = _canonical_hash(payload)
        return self.hash


# ── Graph ────────────────────────────────────────────────────────────────

class GraphEdge(BaseModel):
    from_node: str
    to_node: str
    edge_type: str  # e.g. "imports", "calls", "tests", "declares"
    provenance: EdgeProvenance
    source_span: str | None = None
    manifest_ref: str | None = None
    uncertainty: str | None = None


class GraphSnapshot(BaseModel):
    graph_id: str
    graph_hash: str = ""
    source_hash: str
    contract_hash: str
    builder_version: str = "0.1.0"
    nodes: list[str] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)
    unresolved_items: list[str] = Field(default_factory=list)

    def compute_hash(self) -> str:
        payload = self.model_dump(exclude={"graph_hash"})
        self.graph_hash = _canonical_hash(payload)
        return self.graph_hash


# ── Context ──────────────────────────────────────────────────────────────

class ContextPacket(BaseModel):
    context_hash: str = ""
    source_hash: str
    contract_hash: str
    graph_hash: str
    current_decision_ids: list[str] = Field(default_factory=list)
    excerpts: dict[str, str] = Field(default_factory=dict)
    selected_checks: list[str] = Field(default_factory=list)
    unresolved_coverage: list[str] = Field(default_factory=list)
    remaining_budget: dict[str, int] = Field(default_factory=dict)

    def compute_hash(self) -> str:
        payload = self.model_dump(exclude={"context_hash"})
        self.context_hash = _canonical_hash(payload)
        return self.context_hash


# ── Decision ─────────────────────────────────────────────────────────────

class Decision(BaseModel):
    decision_id: str
    statement: str
    status: DecisionStatus = DecisionStatus.CURRENT
    dependency_hashes: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    owner: str = ""
    role: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)
    supersedes: str | None = None
    revisit_condition: str | None = None


# ── Action ───────────────────────────────────────────────────────────────

class Action(BaseModel):
    action_id: str
    role: str
    tool: str
    canonical_args_hash: str = ""
    source_hash: str = ""
    context_hash: str = ""
    observation_ids: list[str] = Field(default_factory=list)
    failure_fingerprint: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: int = 0
    status: str = "pending"


# ── Patch ────────────────────────────────────────────────────────────────

class Patch(BaseModel):
    patch_id: str
    base_hash: str
    diff_hash: str = ""
    diff_text: str = ""
    approved_paths: list[str] = Field(default_factory=list)
    changed_lines: int = 0
    targeted_constraints: list[str] = Field(default_factory=list)
    policy_result: PatchPolicyResult = PatchPolicyResult.PENDING
    author: str = ""
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


# ── Check Result ─────────────────────────────────────────────────────────

class CheckResult(BaseModel):
    check_id: str
    check_version: int = 1
    patch_hash: str | None = None
    source_hash: str = ""
    contract_hash: str = ""
    image_hash: str = ""
    evaluator_hash: str = ""
    outcome: CheckOutcome = CheckOutcome.UNKNOWN
    oracle_kind: str = ""  # e.g. "deterministic", "reference", "heuristic"
    observation_refs: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    reason: str = ""


# ── Mutation Result ──────────────────────────────────────────────────────

class MutationResult(BaseModel):
    template_id: str
    template_version: int = 1
    mutant_hash: str = ""
    validity: str = ""  # "valid", "invalid_syntax", etc.
    outcome: MutationOutcome = MutationOutcome.SKIPPED
    supporting_check_ids: list[str] = Field(default_factory=list)


# ── Artifact ─────────────────────────────────────────────────────────────

class Artifact(BaseModel):
    artifact_id: str
    owner: str
    audit_id: str
    attempt: int = 1
    relative_name: str
    mime_type: str = "application/octet-stream"
    byte_size: int = 0
    sha256: str = ""
    visibility: str = "private"


# ── Audit ────────────────────────────────────────────────────────────────

class AuditRecord(BaseModel):
    schema_version: str = "benchproof/v2"
    audit_id: str
    owner_ref: str
    fixture_id: str
    task_id: str = ""
    source_hash: str
    contract_hash: str
    run_state: RunState = RunState.QUEUED
    gate_verdict: GateVerdict = GateVerdict.PENDING
    mode: str = "live"  # "live" | "mock"
    created_at: datetime = Field(default_factory=_utcnow)
    attempt: int = 1
    limits: dict[str, int] = Field(
        default_factory=lambda: {
            "max_actions": 15,
            "max_patches": 5,
            "process_timeout_s": 60,
            "audit_deadline_s": 300,
        }
    )
    reservations: dict[str, Any] = Field(default_factory=dict)
