"""BenchProof API — health/readiness, curated examples, accepted constraints, audits and events.

Live diagnosis can bill a model request; public candidate verification requires
the isolated Docker runner. Unconfigured live mode is refused, never mocked.
POST /audits is idempotent under an Idempotency-Key; events are resumable by
sequence; cancellation is a compare-and-swap transition.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from benchproof import __version__
from benchproof.api.body_limit import CodingBodyLimitMiddleware
from benchproof.api.coding import coding_router
from benchproof.coding.runtime import CodingRuntimeConfig
from benchproof.coding.store import CodingStore
from benchproof.constraints import contract_hash, get_constraint, list_constraints
from benchproof.constraints.approval import ensure_registry_executable
from benchproof.domain import AuditRecord, DecisionReviewStatus, RunState
from benchproof.fixtures import list_fixture_ids, list_public_examples, public_example
from benchproof.storage import (
    get_audit,
    get_graph_by_audit_id,
    list_actions,
    list_audits,
    migrate,
    save_audit,
    save_graph,
)
from benchproof.storage.heartbeat import latest_heartbeat
from benchproof.storage.lifecycle import (
    TERMINAL_STATES,
    IdempotencyConflict,
    append_event,
    body_hash,
    create_audit_idempotent,
    list_events,
    migrate_lifecycle,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLACEHOLDER_KEYS = {"", "your_api_key_here"}
_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


# ── Settings ─────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_REPO_ROOT / ".env"), extra="ignore")

    app_name: str = "BenchProof API"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_path: str = "benchproof.db"
    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    nebius_model_id: str = ""
    benchproof_diagnosis_max_tokens: int = Field(default=2_048, ge=256, le=4_096)
    benchproof_coding_enabled: bool = False
    benchproof_coding_model_calls_per_day: int = Field(default=0, ge=0)
    benchproof_coding_executions_per_day: int = Field(default=0, ge=0)
    benchproof_coding_max_tasks: int = Field(default=100, ge=1, le=100)
    benchproof_coding_deadline_epoch: float = Field(default=0, ge=0, allow_inf_nan=False)
    benchproof_coding_output_tokens: int = Field(default=2_048, ge=256, le=4_096)
    benchproof_runner: Literal["mock", "docker", "contree"] = "mock"
    heartbeat_stale_s: int = 30
    sse_max_wait_s: float = 15.0

    @property
    def provider_configured(self) -> bool:
        return self.nebius_api_key not in _PLACEHOLDER_KEYS and bool(self.nebius_model_id)


settings = Settings()


def _db() -> Path:
    return Path(settings.database_path)


def coding_runtime_config() -> CodingRuntimeConfig:
    return CodingRuntimeConfig(
        enabled=settings.benchproof_coding_enabled,
        model_calls_per_day=settings.benchproof_coding_model_calls_per_day,
        executions_per_day=settings.benchproof_coding_executions_per_day,
        max_tasks=settings.benchproof_coding_max_tasks,
        deadline_epoch=settings.benchproof_coding_deadline_epoch,
        max_output_tokens=settings.benchproof_coding_output_tokens,
    )


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _request_owner(
    x_benchproof_owner: str | None = Header(default=None, alias="X-BenchProof-Owner"),
) -> str:
    """Resolve the local/demo owner boundary without exposing an authentication claim."""
    if x_benchproof_owner is None:
        raise _error(401, "OWNER_REQUIRED", "X-BenchProof-Owner is required for audit records")
    owner = x_benchproof_owner.strip()
    if not _OWNER_PATTERN.fullmatch(owner):
        raise _error(400, "INVALID_INPUT", "Invalid X-BenchProof-Owner value")
    return owner


def _owned_audit(audit_id: str, owner_ref: str) -> dict[str, Any]:
    row = get_audit(audit_id, db_path=_db())
    if row is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")
    if row["owner_ref"] != owner_ref:
        raise _error(403, "OWNER_DENIED", "This audit belongs to another owner")
    return row


def runner_status() -> dict[str, Any]:
    """Probe the configured runner once (startup or explicit refresh), never per poll."""
    mode = settings.benchproof_runner
    if mode == "docker":
        from benchproof.execution.docker_runner import DockerRunner

        try:
            ok, detail = DockerRunner().available()
        except OSError as exc:
            ok, detail = False, f"docker readiness probe failed: {type(exc).__name__}"
        return {"mode": mode, "isolated_execution_available": ok, "detail": detail}
    if mode == "contree":
        return {"mode": mode, "isolated_execution_available": False, "detail": "no spawn permission on this account"}
    return {"mode": mode, "isolated_execution_available": False, "detail": "mock runner executes nothing"}


# ── App ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    migrate(_db())
    migrate_lifecycle(_db())
    CodingStore(_db(), coding_runtime_config().operator_limits())
    ensure_registry_executable()  # REQUIRED_CHECK_MISSING aborts startup
    application.state.runner = runner_status()
    yield


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key", "Last-Event-ID", "X-BenchProof-Owner"],
)
app.add_middleware(CodingBodyLimitMiddleware)

app.include_router(coding_router(
    _request_owner, _db, coding_runtime_config, lambda: settings.provider_configured,
    lambda: bool(getattr(app.state, "runner", {}).get("isolated_execution_available")),
    lambda: settings.nebius_model_id,
))


# ── Health / ready ───────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "runner": settings.benchproof_runner}


def _runtime_snapshot(request: Request) -> dict[str, Any]:
    """Provider/runner/worker readiness from cached probes; shared by /ready and /skills."""
    hb = latest_heartbeat(_db())
    worker_alive = bool(hb and hb["age_s"] <= settings.heartbeat_stale_s)
    coding = coding_runtime_config()
    coding_blocked = coding.blocked_reason(
        provider_configured=settings.provider_configured,
        runner_ready=bool(request.app.state.runner.get("isolated_execution_available")),
    )
    return {
        "provider": {
            "name": "nebius-token-factory",
            "configured": settings.provider_configured,
            "model_id": settings.nebius_model_id or None,
        },
        "runner": request.app.state.runner,
        "worker": {"alive": worker_alive, "heartbeat": hb},
        "coding": {
            "enabled": coding.enabled, "admission_configured": coding_blocked is None,
            "blocked_reason": coding_blocked,
            "worker_alive": bool(worker_alive and hb and hb["worker_id"].startswith("coding-worker-")),
            "profile": "invoice-observation-v1", "general_project_intake": False,
            "session_seconds_remaining": int(coding.seconds_remaining()),
            "hard_model_calls_per_day": coding.model_calls_per_day,
            "hard_executions_per_day": coding.executions_per_day,
            "hard_token_cap": False,
        },
    }


@app.get("/api/v1/ready")
def readiness_check(request: Request, refresh: bool = Query(False)) -> dict[str, Any]:
    """Configuration readiness. Never bills a model call."""
    if refresh:
        request.app.state.runner = runner_status()
    return {
        "status": "ok",
        "version": __version__,
        "database": _db().exists(),
        "contract_hash": contract_hash(),
        **_runtime_snapshot(request),
        "fixtures": len(list_fixture_ids()),
    }


# ── Constraints (public summary; hidden oracle excluded) ─────────────────

@app.get("/api/v1/constraints")
def get_constraints() -> list[dict[str, Any]]:
    return [c.model_dump() for c in list_constraints()]


@app.get("/api/v1/constraints/{constraint_id}")
@app.get("/api/v1/contracts/{constraint_id}")
def get_constraint_by_id(constraint_id: str) -> dict[str, Any]:
    c = get_constraint(constraint_id)
    if c is None:
        raise _error(404, "INVALID_INPUT", "Constraint not found")
    return c.model_dump()


# ── Examples (curated development fixtures; public manifest fields only) ──

@app.get("/api/v1/examples")
def get_examples() -> list[dict[str, Any]]:
    return list_public_examples()


# ── Audits ───────────────────────────────────────────────────────────────

class CreateAuditRequest(BaseModel):
    fixture_id: str
    mode: Literal["live", "mock"] = "mock"
    source_hash: str | None = None  # optional pin; mismatch is STALE_SOURCE
    contract_hash: str | None = None  # optional pin; mismatch is CONTRACT_UNAPPROVED


_ENDPOINT_CREATE = "POST /api/v1/audits"


@app.post("/api/v1/audits", status_code=201)
def create_audit(
    body: CreateAuditRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    owner_ref: str = Depends(_request_owner),
) -> JSONResponse:
    bhash = body_hash(body.model_dump())

    try:
        example = public_example(body.fixture_id)
    except (FileNotFoundError, ValueError):
        raise _error(404, "INVALID_INPUT", "Unknown fixture")

    if body.source_hash and body.source_hash != example["source_hash"]:
        raise _error(409, "STALE_SOURCE", "Pinned source_hash does not match the current fixture source")

    if body.contract_hash and body.contract_hash != contract_hash():
        raise _error(409, "CONTRACT_UNAPPROVED", "Pinned contract_hash is not the accepted contract version")

    if body.mode == "live" and not settings.provider_configured:
        raise _error(
            503,
            "PROVIDER_UNAVAILABLE",
            "Live mode requires NEBIUS_API_KEY and NEBIUS_MODEL_ID; not falling back to mock",
        )

    audit = AuditRecord(
        audit_id=f"audit-{uuid.uuid4().hex[:12]}",
        owner_ref=owner_ref,
        fixture_id=body.fixture_id,
        source_hash=example["source_hash"],
        contract_hash=contract_hash(),
        mode=body.mode,
    )
    created_payload = {
        "fixture_id": audit.fixture_id, "source_hash": audit.source_hash,
        "contract_hash": audit.contract_hash, "mode": audit.mode,
    }
    response = audit.model_dump(mode="json")
    if idempotency_key:
        # Audit row, idempotency record and audit_created event commit in one serialized
        # transaction, so a duplicate submit (double click, reconnect) can never create two audits.
        try:
            response, replayed = create_audit_idempotent(
                owner_ref, _ENDPOINT_CREATE, idempotency_key, bhash, audit, response, _db()
            )
        except IdempotencyConflict as exc:
            raise _error(409, "IDEMPOTENCY_CONFLICT", str(exc)) from exc
        headers = {"Idempotent-Replay": "true"} if replayed else {}
        return JSONResponse(response, status_code=201, headers=headers)
    save_audit(audit, _db())
    append_event(audit.audit_id, "audit_created", created_payload, db_path=_db())
    return JSONResponse(response, status_code=201)


@app.get("/api/v1/audits")
def list_all_audits(owner_ref: str = Depends(_request_owner)) -> list[dict[str, Any]]:
    return list_audits(owner=owner_ref, db_path=_db())


@app.get("/api/v1/audits/{audit_id}")
def get_audit_by_id(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    return _owned_audit(audit_id, owner_ref)


# ── Events (JSON list or SSE, resumable by sequence) ─────────────────────

def _sse_frame(ev: dict[str, Any]) -> str:
    return f"id: {ev['sequence']}\nevent: {ev['event_type']}\ndata: {json.dumps(ev, sort_keys=True)}\n\n"


async def _sse(audit_id: str, cursor: int) -> AsyncIterator[str]:
    deadline = asyncio.get_running_loop().time() + settings.sse_max_wait_s
    while True:
        for ev in list_events(audit_id, after=cursor, db_path=_db()):
            cursor = ev["sequence"]
            yield _sse_frame(ev)
        row = get_audit(audit_id, db_path=_db())
        if row is None or row["run_state"] in TERMINAL_STATES:
            yield f"event: end\ndata: {json.dumps({'run_state': row['run_state'] if row else None})}\n\n"
            return
        if asyncio.get_running_loop().time() >= deadline:
            yield "event: retry\ndata: {}\n\n"  # client reconnects with Last-Event-ID
            return
        await asyncio.sleep(0.5)


@app.get("/api/v1/audits/{audit_id}/events")
def get_events(
    audit_id: str,
    request: Request,
    after: int = Query(0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    owner_ref: str = Depends(_request_owner),
) -> Any:
    row = _owned_audit(audit_id, owner_ref)
    cursor = after
    if last_event_id and last_event_id.isdigit():
        cursor = max(cursor, int(last_event_id))
    if "text/event-stream" in request.headers.get("accept", ""):
        return StreamingResponse(_sse(audit_id, cursor), media_type="text/event-stream")
    return {
        "audit_id": audit_id,
        "run_state": row["run_state"],
        "gate_verdict": row["gate_verdict"],
        "events": list_events(audit_id, after=cursor, db_path=_db()),
    }


# ── Cancel (durable CAS transition) ──────────────────────────────────────

@app.post("/api/v1/audits/{audit_id}/cancel")
def cancel_audit(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> JSONResponse:
    row = _owned_audit(audit_id, owner_ref)
    from benchproof.storage.lifecycle import TransitionRejected, request_cancellation

    reservations = json.loads(row.get("reservations") or "{}")
    remote_active = bool(reservations.get("remote_run_id"))
    try:
        target = request_cancellation(
            audit_id,
            remote_reconciliation_required=remote_active,
            db_path=_db(),
        )
    except TransitionRejected as exc:
        raise _error(409, "INVALID_INPUT", str(exc)) from exc
    pending = target == RunState.CANCEL_PENDING
    return JSONResponse(
        {
            "status": "cancel_pending" if pending else "cancelled",
            "audit_id": audit_id,
            "remote_reconciliation": "pending" if pending else "not_applicable",
        },
        status_code=202 if pending else 200,
    )


# ── Decision Ledger & Fresh Context (Day 10 / B-14) ───────────────────────

class CreateDecisionRequest(BaseModel):
    statement: str
    review_status: Literal["PROPOSED", "REVIEWED"] = "PROPOSED"
    dependency_paths: list[str] = Field(default_factory=list)
    include_source: bool = False
    include_contract: bool = True
    include_graph: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    revisit_condition: str | None = None
    supersedes: str | None = None


def _refresh_decision_ledger(audit: dict[str, Any]) -> dict[str, Any]:
    from benchproof.constraints import contract_hash as current_contract_hash
    from benchproof.decisions import refresh_decisions
    from benchproof.fixtures import fixture_dir

    ledger = refresh_decisions(
        audit["audit_id"],
        fixture_dir(audit["fixture_id"]) / "app",
        current_contract_hash(),
        _db(),
    )
    for decision_id in ledger["invalidated_decision_ids"]:
        append_event(
            audit["audit_id"],
            "decision_invalidated",
            {"decision_id": decision_id, "reason": "declared dependency changed or was deleted"},
            db_path=_db(),
        )
    return ledger


@app.post("/api/v1/audits/{audit_id}/decisions", status_code=201)
def create_audit_decision(
    audit_id: str,
    body: CreateDecisionRequest,
    owner_ref: str = Depends(_request_owner),
) -> JSONResponse:
    audit = _owned_audit(audit_id, owner_ref)
    from benchproof.decisions import DecisionError, create_decision
    from benchproof.fixtures import fixture_dir
    from benchproof.storage import get_decision

    if body.supersedes:
        prior = get_decision(body.supersedes, _db())
        if prior is None or prior["audit_id"] != audit_id:
            raise _error(409, "INVALID_INPUT", "Superseded decision does not belong to this audit")
    try:
        decision = create_decision(
            audit_id=audit_id,
            app_dir=fixture_dir(audit["fixture_id"]) / "app",
            statement=body.statement,
            owner=owner_ref,
            review_status=DecisionReviewStatus(body.review_status),
            current_contract_hash=contract_hash(),
            dependency_paths=body.dependency_paths,
            include_source=body.include_source,
            include_contract=body.include_contract,
            include_graph=body.include_graph,
            evidence_ids=body.evidence_ids,
            revisit_condition=body.revisit_condition,
            supersedes=body.supersedes,
            db_path=_db(),
        )
    except DecisionError as exc:
        raise _error(422, exc.code, exc.message) from exc
    append_event(
        audit_id,
        "decision_recorded",
        {
            "decision_id": decision.decision_id,
            "review_status": decision.review_status.value,
            "dependency_count": len(decision.dependencies),
        },
        db_path=_db(),
    )
    return JSONResponse(decision.model_dump(mode="json"), status_code=201)


@app.get("/api/v1/audits/{audit_id}/decisions")
def get_audit_decisions(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)
    return _refresh_decision_ledger(audit)


@app.get("/api/v1/audits/{audit_id}/context")
def get_audit_context(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)
    from benchproof.decisions import build_current_context
    from benchproof.fixtures import fixture_dir

    graph, impact, context, ledger = build_current_context(
        audit_id,
        fixture_dir(audit["fixture_id"]) / "app",
        contract_hash(),
        db_path=_db(),
    )
    return {
        "context": context.model_dump(mode="json"),
        "impact": impact.to_dict(),
        "graph_hash": graph.graph_hash,
        "decisions": ledger,
    }


# ── Engineering-State Graph (Day 4 / B-07) ────────────────────────────────

@app.get("/api/v1/audits/{audit_id}/graph")
def get_audit_graph(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)

    existing = get_graph_by_audit_id(audit_id, db_path=_db())
    if existing:
        return existing

    from benchproof.fixtures import fixture_dir
    from benchproof.graph.builder import build_state_graph

    app_dir = fixture_dir(audit["fixture_id"]) / "app"
    graph = build_state_graph(app_dir, audit["contract_hash"])
    save_graph(
        graph_id=graph.graph_id,
        source_hash=graph.source_hash,
        contract_hash=graph.contract_hash,
        graph_hash=graph.graph_hash,
        coverage=graph.coverage,
        graph_data=graph.model_dump(),
        audit_id=audit_id,
        db_path=_db(),
    )
    return {
        "graph_id": graph.graph_id,
        "audit_id": audit_id,
        "source_hash": graph.source_hash,
        "contract_hash": graph.contract_hash,
        "graph_hash": graph.graph_hash,
        "coverage": graph.coverage,
        "graph": graph.model_dump(),
    }


# ── Blast Radius & Deterministic Risk (Day 5 / B-08) ─────────────────────

@app.get("/api/v1/audits/{audit_id}/impact")
def get_audit_impact(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)

    from benchproof.decisions import build_current_context
    from benchproof.fixtures import fixture_dir

    app_dir = fixture_dir(audit["fixture_id"]) / "app"
    _, impact, context, ledger = build_current_context(
        audit_id,
        app_dir,
        contract_hash(),
        db_path=_db(),
    )
    result = impact.to_dict()
    result.update(
        context_hash=context.context_hash,
        current_decision_ids=context.current_decision_ids,
        decision_refresh_overhead_ms=ledger["refresh_overhead_ms"],
    )
    return result


# ── NVIDIA Investigation & Probe Execution (Day 5 / B-08) ────────────────

@app.post("/api/v1/audits/{audit_id}/diagnose")
def diagnose_audit(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)

    if audit["run_state"] == RunState.STALLED.value:
        raise _error(409, "STALLED", "Repeated no-progress work stopped; use the single recovery")
    if audit["run_state"] == RunState.BLOCKED.value:
        raise _error(409, "RECOVERY_EXHAUSTED", "The audit is blocked after its recovery stalled")

    from benchproof.investigation import InvestigationError, run_investigation
    from benchproof.trajectory import TrajectoryError, recovery_state

    try:
        recovery = recovery_state(audit_id, _db())
        res = run_investigation(
            fixture_id=audit["fixture_id"],
            audit_id=audit_id,
            mode=audit["mode"],
            strategy=recovery["recovery_strategy"] or "broad_diagnosis",
            db_path=_db(),
            model_id=settings.nebius_model_id or None,
            api_key=settings.nebius_api_key or None,
            base_url=settings.nebius_base_url,
            max_tokens=settings.benchproof_diagnosis_max_tokens,
        )
        return res
    except InvestigationError as e:
        if e.code == "PROVIDER_UNAVAILABLE":
            status_code = 503
        elif e.code.startswith(("MODEL_OUTPUT_", "PROVIDER_INVALID_")) or e.code == "MALFORMED_ACTION":
            status_code = 502
        else:
            status_code = 409 if e.code in {"STALE_SOURCE", "CONTRACT_UNAPPROVED", "STALE_CONTEXT"} else 422
        raise _error(status_code, e.code, e.message)
    except TrajectoryError as e:
        status_code = 409 if e.code in {"BUDGET_EXHAUSTED", "RECOVERY_EXHAUSTED", "INVALID_STATE"} else 422
        raise _error(status_code, e.code, e.message)


@app.get("/api/v1/audits/{audit_id}/trajectory")
def get_audit_trajectory(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)
    from benchproof.trajectory import (
        FINGERPRINT_RULE_VERSION,
        STALL_REPEAT_THRESHOLD,
        recovery_state,
    )

    return {
        "audit_id": audit_id,
        "run_state": audit["run_state"],
        "rule_version": FINGERPRINT_RULE_VERSION,
        "repeat_threshold": STALL_REPEAT_THRESHOLD,
        **recovery_state(audit_id, _db()),
    }


@app.post("/api/v1/audits/{audit_id}/recover")
def recover_stalled_audit(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)
    from benchproof.investigation import InvestigationError, run_investigation
    from benchproof.trajectory import RECOVERY_STRATEGY, TrajectoryError, reserve_recovery

    try:
        reserved = reserve_recovery(audit_id, _db())
        result = run_investigation(
            fixture_id=audit["fixture_id"],
            audit_id=audit_id,
            mode=audit["mode"],
            strategy=RECOVERY_STRATEGY,
            db_path=_db(),
            model_id=settings.nebius_model_id or None,
            api_key=settings.nebius_api_key or None,
            base_url=settings.nebius_base_url,
            max_tokens=settings.benchproof_diagnosis_max_tokens,
        )
        return {"recovery": reserved, "result": result}
    except TrajectoryError as e:
        status_code = 409 if e.code in {"BUDGET_EXHAUSTED", "RECOVERY_EXHAUSTED", "INVALID_STATE"} else 422
        raise _error(status_code, e.code, e.message)
    except InvestigationError as e:
        if e.code == "PROVIDER_UNAVAILABLE":
            status_code = 503
        elif e.code.startswith(("MODEL_OUTPUT_", "PROVIDER_INVALID_")) or e.code == "MALFORMED_ACTION":
            status_code = 502
        else:
            status_code = 409
        raise _error(status_code, e.code, e.message)


# ── Actions Trajectory ───────────────────────────────────────────────────

@app.get("/api/v1/audits/{audit_id}/actions")
def get_audit_actions(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> list[dict[str, Any]]:
    _owned_audit(audit_id, owner_ref)
    return list_actions(audit_id, db_path=_db())


# ── Restricted Patch Authoring & Import (Day 6 / B-09) ───────────────────

class ProposePatchRequest(BaseModel):
    diff: str
    base_source_hash: str
    target_files: list[str] = Field(default_factory=list)
    explanation: str = ""
    author: str = "nemotron-repair"
    context_hash: str | None = None


@app.post("/api/v1/audits/{audit_id}/patch")
def propose_patch(
    audit_id: str,
    req: ProposePatchRequest,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)

    from benchproof.fixtures import fixture_dir, source_hash_for_dir
    from benchproof.patch import (
        PatchProposal,
        PatchValidationError,
        compute_diff_hash,
        validate_patch,
    )
    from benchproof.storage import save_patch
    from benchproof.storage.lifecycle import append_event

    current_shash = source_hash_for_dir(fixture_dir(audit["fixture_id"]) / "app")
    from benchproof.storage import list_decisions

    ledger_exists = bool(list_decisions(audit_id, _db()))
    if ledger_exists or req.context_hash:
        from benchproof.decisions import build_current_context

        _, _, current_context, _ = build_current_context(
            audit_id,
            fixture_dir(audit["fixture_id"]) / "app",
            contract_hash(),
            db_path=_db(),
        )
        if ledger_exists and not req.context_hash:
            raise _error(
                409,
                "STALE_CONTEXT",
                "A current context_hash is required when the audit has decision history",
            )
        if req.context_hash != current_context.context_hash:
            raise _error(
                409,
                "STALE_CONTEXT",
                "Patch was authored against an old decision/source/contract context",
            )
    patch_id = f"patch-{uuid.uuid4().hex[:12]}"

    proposal = PatchProposal(
        patch_id=patch_id,
        audit_id=audit_id,
        base_source_hash=req.base_source_hash,
        target_files=req.target_files,
        diff=req.diff,
        explanation=req.explanation,
        author=req.author,
    )

    try:
        _, approved_paths = validate_patch(proposal, current_shash)
    except PatchValidationError as e:
        status_code = 409 if e.code == "PATCH_BASE_MISMATCH" else 422
        raise _error(status_code, e.code, e.message)

    diff_hash = compute_diff_hash(req.diff)
    changed_lines = len(req.diff.splitlines())

    save_patch(
        patch_id=patch_id,
        audit_id=audit_id,
        base_hash=req.base_source_hash,
        diff_hash=diff_hash,
        diff_text=req.diff,
        approved_paths=approved_paths,
        changed_lines=changed_lines,
        # Validated against the patch rules, but not judged: only the protected gate may
        # write APPROVED or REJECTED, after an isolated verification.
        policy_result="PENDING",
        author=req.author,
        provider_meta={"explanation": req.explanation},
        db_path=_db(),
    )

    append_event(
        audit_id=audit_id,
        event_type="patch_proposed",
        payload={
            "patch_id": patch_id,
            "diff_hash": diff_hash,
            "approved_paths": approved_paths,
            "changed_lines": changed_lines,
            "policy_result": "PENDING",
        },
        db_path=_db(),
    )

    return {
        "patch_id": patch_id,
        "audit_id": audit_id,
        "policy_result": "PENDING",
        "diff_hash": diff_hash,
        "approved_paths": approved_paths,
        "changed_lines": changed_lines,
    }


@app.get("/api/v1/audits/{audit_id}/patches")
def get_audit_patches(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> list[dict[str, Any]]:
    _owned_audit(audit_id, owner_ref)
    from benchproof.storage import list_patches
    return list_patches(audit_id, db_path=_db())


@app.get("/api/v1/patches/{patch_id}")
def get_patch_by_id(
    patch_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    from benchproof.storage import get_patch

    patch = get_patch(patch_id, db_path=_db())
    if patch is None:
        raise _error(404, "INVALID_INPUT", "Patch not found")
    _owned_audit(patch["audit_id"], owner_ref)
    return patch


# ── Fresh Independent Acceptance Gate (Day 6 / B-10) ─────────────────────

class VerifyCandidateRequest(BaseModel):
    patch_id: str | None = None
    use_docker: bool = True


@app.post("/api/v1/audits/{audit_id}/verify")
def verify_audit_candidate(
    audit_id: str,
    req: VerifyCandidateRequest,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    _owned_audit(audit_id, owner_ref)

    if req.patch_id:
        from benchproof.storage import get_patch

        patch = get_patch(req.patch_id, db_path=_db())
        if patch is None or patch["audit_id"] != audit_id:
            raise _error(409, "PATCH_NOT_FOUND", "Patch does not belong to this audit")

    if not req.use_docker:
        raise _error(
            409,
            "ISOLATION_REQUIRED",
            "Public verification requires the isolated Docker runner; in-process execution is disabled",
        )
    if settings.benchproof_runner != "docker":
        raise _error(
            503,
            "RUNNER_UNAVAILABLE",
            "Verification is blocked until BENCHPROOF_RUNNER=docker is configured and ready",
        )

    from benchproof.gate import GateError, execute_acceptance_gate

    try:
        result = execute_acceptance_gate(
            audit_id=audit_id,
            patch_id=req.patch_id,
            use_docker=req.use_docker,
            db_path=_db(),
        )
        return result
    except GateError as e:
        if e.code == "RUNNER_UNAVAILABLE":
            status_code = 503
        else:
            status_code = 409 if e.code in {"BUDGET_EXHAUSTED", "PATCH_NOT_FOUND"} else 422
        raise _error(status_code, e.code, e.message)


@app.get("/api/v1/audits/{audit_id}/gate")
def get_audit_gate_status(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    audit = _owned_audit(audit_id, owner_ref)

    from benchproof.storage.lifecycle import latest_check_attempt, list_check_results

    checks = list_check_results(audit_id, db_path=_db())
    return {
        "audit_id": audit_id,
        "gate_verdict": audit.get("gate_verdict", "PENDING"),
        "run_state": audit.get("run_state", "QUEUED"),
        "attempt": latest_check_attempt(audit_id, db_path=_db()),
        "checks": checks,
    }


# ── Trusted semantic mutation assessment (Day 12 / B-16) ───────────────

class RunMutationRequest(BaseModel):
    patch_id: str | None = None
    max_mutants: int = Field(default=3, ge=1, le=3)


@app.post("/api/v1/audits/{audit_id}/mutations")
def run_audit_mutations(
    audit_id: str,
    req: RunMutationRequest,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    _owned_audit(audit_id, owner_ref)
    if settings.benchproof_runner != "docker":
        raise _error(
            503,
            "RUNNER_UNAVAILABLE",
            "Mutation assessment is blocked until the isolated Docker runner is configured and ready",
        )
    from benchproof.gate import GateError
    from benchproof.mutations import MutationError, run_mutation_assessment
    from benchproof.patch import PatchValidationError

    try:
        return run_mutation_assessment(
            audit_id,
            patch_id=req.patch_id,
            max_mutants=req.max_mutants,
            db_path=_db(),
            use_docker=True,
        )
    except MutationError as exc:
        status = 409 if exc.code in {
            "BUDGET_EXHAUSTED", "CANDIDATE_NOT_VERIFIED", "PATCH_NOT_FOUND",
            "CANDIDATE_CHANGED",
        } else 422
        raise _error(status, exc.code, exc.message) from exc
    except PatchValidationError as exc:
        raise _error(409, exc.code, exc.message) from exc
    except GateError as exc:
        status = 503 if exc.code == "RUNNER_UNAVAILABLE" else 422
        raise _error(status, exc.code, exc.message) from exc


@app.get("/api/v1/audits/{audit_id}/mutations")
def get_audit_mutations(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    _owned_audit(audit_id, owner_ref)
    from benchproof.mutations import MUTATION_POLICY, TEMPLATE_SET_VERSION
    from benchproof.storage import list_mutation_assessments

    runs = list_mutation_assessments(audit_id, db_path=_db())
    return {
        "audit_id": audit_id,
        "policy": MUTATION_POLICY,
        "template_set_version": TEMPLATE_SET_VERSION,
        "status": runs[-1]["strength_status"] if runs else "NOT_RUN",
        "runs": runs,
    }


# ── Evidence Bundle Export & Independent Replay (Day 7 / B-11) ───────────

@app.post("/api/v1/audits/{audit_id}/bundle")
def create_audit_bundle(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    _owned_audit(audit_id, owner_ref)

    from benchproof.bundle import export_bundle
    from benchproof.bundle.exporter import SafeArchivePathError, SecurityExclusionError

    try:
        bundle_path, manifest = export_bundle(audit_id, db_path=_db())
    except (SecurityExclusionError, SafeArchivePathError) as e:
        # Refuse to produce a bundle that would leak secrets or contain unsafe paths.
        raise _error(422, "BUNDLE_EXCLUSION_VIOLATION", str(e)) from e
    except (ValueError, OSError) as e:
        raise _error(500, "BUNDLE_EXPORT_FAILED", f"Bundle export error: {e}") from e

    import hashlib
    sha256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    return {
        "audit_id": audit_id,
        "bundle_path": str(bundle_path),
        "bundle_name": bundle_path.name,
        "sha256": sha256,
        "byte_size": bundle_path.stat().st_size,
        "manifest": manifest.model_dump(),
    }


@app.get("/api/v1/audits/{audit_id}/bundle")
def get_audit_bundle(
    audit_id: str,
    metadata: bool = Query(default=False, description="Return JSON metadata instead of binary zip"),
    owner_ref: str = Depends(_request_owner),
) -> Any:
    _owned_audit(audit_id, owner_ref)

    from benchproof.bundle import export_bundle

    bundles_dir = Path("artifacts") / "bundles"
    bundle_path = bundles_dir / f"benchproof-audit-{audit_id}.zip"

    if not bundle_path.exists():
        bundle_path, _ = export_bundle(audit_id, db_path=_db())
    else:
        from benchproof.bundle.validator import validate_bundle_nonexecuting
        val = validate_bundle_nonexecuting(bundle_path)
        if not val["valid"]:
            bundle_path, _ = export_bundle(audit_id, db_path=_db())

    if metadata:
        import hashlib
        import json
        import zipfile
        with zipfile.ZipFile(bundle_path, "r") as zf:
            m_data = json.loads(zf.read("manifest.json").decode("utf-8"))
        sha256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        return {
            "audit_id": audit_id,
            "bundle_path": str(bundle_path),
            "bundle_name": bundle_path.name,
            "sha256": sha256,
            "byte_size": bundle_path.stat().st_size,
            "manifest": m_data,
        }

    return FileResponse(
        path=str(bundle_path),
        media_type="application/zip",
        filename=f"benchproof-audit-{audit_id}.zip",
    )


@app.post("/api/v1/audits/{audit_id}/bundle/validate")
def validate_audit_bundle(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    _owned_audit(audit_id, owner_ref)

    from benchproof.bundle import export_bundle, validate_bundle_nonexecuting

    bundles_dir = Path("artifacts") / "bundles"
    bundle_path = bundles_dir / f"benchproof-audit-{audit_id}.zip"
    if not bundle_path.exists():
        bundle_path, _ = export_bundle(audit_id, db_path=_db())

    return validate_bundle_nonexecuting(bundle_path)


@app.get("/api/v1/audits/{audit_id}/replay")
@app.post("/api/v1/audits/{audit_id}/replay")
def replay_audit_bundle(
    audit_id: str,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    _owned_audit(audit_id, owner_ref)

    if settings.benchproof_runner != "docker":
        raise _error(
            503,
            "RUNNER_UNAVAILABLE",
            "Replay is blocked until BENCHPROOF_RUNNER=docker is configured and ready",
        )

    from benchproof.bundle import export_bundle, replay_bundle

    bundles_dir = Path("artifacts") / "bundles"
    bundle_path = bundles_dir / f"benchproof-audit-{audit_id}.zip"
    if not bundle_path.exists():
        bundle_path, _ = export_bundle(audit_id, db_path=_db())

    from benchproof.gate import GateError

    try:
        replay_rec = replay_bundle(bundle_path, use_docker=True)
        return replay_rec.model_dump()
    except GateError as exc:
        status = 503 if exc.code == "RUNNER_UNAVAILABLE" else 422
        raise _error(status, exc.code, exc.message) from exc


# ── Bounded skill catalog (Day 15 / B-22) ────────────────────────────────

def _skill_inputs(audit_id: str | None) -> dict[str, Any]:
    """Server-side facts the catalog needs: counts, recovery state and bundle presence."""
    if audit_id is None:
        return {}
    from benchproof.storage import list_patches
    from benchproof.trajectory import recovery_state

    bundle_path = Path("artifacts") / "bundles" / f"benchproof-audit-{audit_id}.zip"
    return {
        "recovery": recovery_state(audit_id, _db()),
        "action_count": len(list_actions(audit_id, db_path=_db())),
        "patch_count": len(list_patches(audit_id, db_path=_db())),
        "has_bundle": bundle_path.exists(),
    }


@app.get("/api/v1/skills")
def get_skills(request: Request) -> dict[str, Any]:
    """Catalog of bounded skills with session-level availability (no audit context)."""
    from benchproof.skills import SKILLS_VERSION, describe

    return {
        "version": SKILLS_VERSION,
        "audit_id": None,
        "skills": describe(audit=None, runtime=_runtime_snapshot(request)),
    }


@app.get("/api/v1/audits/{audit_id}/skills")
def get_audit_skills(
    audit_id: str,
    request: Request,
    owner_ref: str = Depends(_request_owner),
) -> dict[str, Any]:
    """Catalog with availability computed from this audit's record, budgets and runtime.

    Each entry names the endpoint it maps to; invoking a skill is just calling that
    endpoint, which repeats every check. The catalog never grants anything.
    """
    audit = _owned_audit(audit_id, owner_ref)
    from benchproof.skills import SKILLS_VERSION, describe

    return {
        "version": SKILLS_VERSION,
        "audit_id": audit_id,
        "run_state": audit["run_state"],
        "gate_verdict": audit["gate_verdict"],
        "skills": describe(audit=audit, runtime=_runtime_snapshot(request), **_skill_inputs(audit_id)),
    }


