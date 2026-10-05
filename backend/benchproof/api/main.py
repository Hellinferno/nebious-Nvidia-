"""BenchProof API — health/readiness, curated examples, accepted constraints, audits and events.

No endpoint executes candidate code or bills a model call. Live mode is refused
explicitly when the provider is not configured; it never falls back to a mock.
POST /audits is idempotent under an Idempotency-Key; events are resumable by
sequence; cancellation is a compare-and-swap transition.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from benchproof import __version__
from benchproof.constraints import contract_hash, get_constraint, list_constraints
from benchproof.constraints.approval import ensure_registry_executable
from benchproof.domain import AuditRecord, RunState
from benchproof.fixtures import list_fixture_ids, list_public_examples, public_example
from benchproof.storage import get_audit, list_audits, migrate, save_audit
from benchproof.storage.heartbeat import latest_heartbeat
from benchproof.storage.lifecycle import (
    TERMINAL_STATES,
    append_event,
    body_hash,
    idempotency_get,
    idempotency_put,
    list_events,
    migrate_lifecycle,
    transition,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLACEHOLDER_KEYS = {"", "your_api_key_here"}
_OWNER = "default-owner"  # single-owner development mode; owner auth is B-13


# ── Settings ─────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_REPO_ROOT / ".env"), extra="ignore")

    app_name: str = "BenchProof API"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_path: str = "benchproof.db"
    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    nebius_model_id: str = ""
    benchproof_runner: Literal["mock", "docker", "contree"] = "mock"
    heartbeat_stale_s: int = 30
    sse_max_wait_s: float = 15.0

    @property
    def provider_configured(self) -> bool:
        return self.nebius_api_key not in _PLACEHOLDER_KEYS and bool(self.nebius_model_id)


settings = Settings()


def _db() -> Path:
    return Path(settings.database_path)


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def runner_status() -> dict[str, Any]:
    """Probe the configured runner once (startup or explicit refresh), never per poll."""
    mode = settings.benchproof_runner
    if mode == "docker":
        from benchproof.execution.docker_runner import DockerRunner

        ok, detail = DockerRunner().available()
        return {"mode": mode, "isolated_execution_available": ok, "detail": detail}
    if mode == "contree":
        return {"mode": mode, "isolated_execution_available": False, "detail": "no spawn permission on this account"}
    return {"mode": mode, "isolated_execution_available": False, "detail": "mock runner executes nothing"}


# ── App ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    migrate(_db())
    migrate_lifecycle(_db())
    ensure_registry_executable()  # REQUIRED_CHECK_MISSING aborts startup
    application.state.runner = runner_status()
    yield


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key", "Last-Event-ID"],
)


# ── Health / ready ───────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "runner": settings.benchproof_runner}


@app.get("/api/v1/ready")
def readiness_check(request: Request, refresh: bool = Query(False)) -> dict[str, Any]:
    """Configuration readiness. Never bills a model call."""
    if refresh:
        request.app.state.runner = runner_status()
    hb = latest_heartbeat(_db())
    worker_alive = bool(hb and hb["age_s"] <= settings.heartbeat_stale_s)
    return {
        "status": "ok",
        "version": __version__,
        "database": _db().exists(),
        "contract_hash": contract_hash(),
        "provider": {
            "name": "nebius-token-factory",
            "configured": settings.provider_configured,
            "model_id": settings.nebius_model_id or None,
        },
        "runner": request.app.state.runner,
        "worker": {"alive": worker_alive, "heartbeat": hb},
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
) -> JSONResponse:
    bhash = body_hash(body.model_dump())
    if idempotency_key:
        prior = idempotency_get(_OWNER, _ENDPOINT_CREATE, idempotency_key, _db())
        if prior is not None:
            if prior["body_hash"] != bhash:
                raise _error(409, "IDEMPOTENCY_CONFLICT", "Idempotency-Key reused with a different body")
            return JSONResponse(prior["response"], status_code=201, headers={"Idempotent-Replay": "true"})

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
        owner_ref=_OWNER,
        fixture_id=body.fixture_id,
        source_hash=example["source_hash"],
        contract_hash=contract_hash(),
        mode=body.mode,
    )
    save_audit(audit, _db())
    append_event(
        audit.audit_id,
        "audit_created",
        {"fixture_id": audit.fixture_id, "source_hash": audit.source_hash,
         "contract_hash": audit.contract_hash, "mode": audit.mode},
        db_path=_db(),
    )
    response = audit.model_dump(mode="json")
    if idempotency_key:
        idempotency_put(_OWNER, _ENDPOINT_CREATE, idempotency_key, bhash, audit.audit_id, response, _db())
    return JSONResponse(response, status_code=201)


@app.get("/api/v1/audits")
def list_all_audits() -> list[dict[str, Any]]:
    return list_audits(db_path=_db())


@app.get("/api/v1/audits/{audit_id}")
def get_audit_by_id(audit_id: str) -> dict[str, Any]:
    row = get_audit(audit_id, db_path=_db())
    if row is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")
    return row


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
) -> Any:
    row = get_audit(audit_id, db_path=_db())
    if row is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")
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

_CANCELLABLE = {s.value for s in RunState} - TERMINAL_STATES


@app.post("/api/v1/audits/{audit_id}/cancel")
def cancel_audit(audit_id: str) -> dict[str, str]:
    row = get_audit(audit_id, db_path=_db())
    if row is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")
    if not transition(audit_id, _CANCELLABLE, RunState.CANCELLED, db_path=_db(), reason="owner request"):
        current = get_audit(audit_id, db_path=_db())
        raise _error(409, "INVALID_INPUT", f"Audit already in terminal state: {current['run_state'] if current else '?'}")
    append_event(audit_id, "cancelled", {"remote_reconciliation": "not applicable (no remote run)"}, db_path=_db())
    return {"status": "cancelled", "audit_id": audit_id}
