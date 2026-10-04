"""BenchProof API — health/readiness, curated examples, accepted constraints and audit records.

Day 1 scope: no candidate execution, no model call on any endpoint. Live mode
is refused explicitly when the provider is not configured; it never falls back
to a mock silently.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from benchproof import __version__
from benchproof.constraints import contract_hash, get_constraint, list_constraints
from benchproof.domain import AuditRecord, RunState
from benchproof.fixtures import list_fixture_ids, list_public_examples, public_example
from benchproof.storage import get_audit, list_audits, migrate, save_audit, update_audit_state
from benchproof.storage.heartbeat import latest_heartbeat

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLACEHOLDER_KEYS = {"", "your_api_key_here"}


# ── Settings ─────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_REPO_ROOT / ".env"), extra="ignore")

    app_name: str = "BenchProof API"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_path: str = "benchproof.db"
    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    nebius_model_id: str = ""
    benchproof_runner: Literal["mock", "contree"] = "mock"
    heartbeat_stale_s: int = 30

    @property
    def provider_configured(self) -> bool:
        return self.nebius_api_key not in _PLACEHOLDER_KEYS and bool(self.nebius_model_id)


settings = Settings()


def _db() -> Path:
    return Path(settings.database_path)


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


# ── App ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    migrate(_db())
    yield


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ── Health / ready ───────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "runner": settings.benchproof_runner}


@app.get("/api/v1/ready")
def readiness_check() -> dict[str, Any]:
    """Configuration readiness. Never bills a model call."""
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
        "runner": {
            "mode": settings.benchproof_runner,
            "isolated_execution_available": False,  # no runner adapter exists yet
        },
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
    source_hash: str | None = None  # optional client pin; mismatch is STALE_SOURCE


@app.post("/api/v1/audits", status_code=201)
def create_audit(body: CreateAuditRequest) -> dict[str, Any]:
    try:
        example = public_example(body.fixture_id)
    except (FileNotFoundError, ValueError):
        raise _error(404, "INVALID_INPUT", "Unknown fixture")

    if body.source_hash and body.source_hash != example["source_hash"]:
        raise _error(
            409, "STALE_SOURCE", "Pinned source_hash does not match the current fixture source"
        )

    if body.mode == "live" and not settings.provider_configured:
        raise _error(
            503,
            "PROVIDER_UNAVAILABLE",
            "Live mode requires NEBIUS_API_KEY and NEBIUS_MODEL_ID; not falling back to mock",
        )

    audit = AuditRecord(
        audit_id=f"audit-{uuid.uuid4().hex[:12]}",
        owner_ref="default-owner",
        fixture_id=body.fixture_id,
        source_hash=example["source_hash"],
        contract_hash=contract_hash(),
        mode=body.mode,
    )
    save_audit(audit, _db())
    return audit.model_dump(mode="json")


@app.get("/api/v1/audits")
def list_all_audits() -> list[dict[str, Any]]:
    return list_audits(db_path=_db())


@app.get("/api/v1/audits/{audit_id}")
def get_audit_by_id(audit_id: str) -> dict[str, Any]:
    row = get_audit(audit_id, db_path=_db())
    if row is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")
    return row


_TERMINAL = {
    s.value
    for s in (
        RunState.COMPLETED,
        RunState.FAILED,
        RunState.CANCELLED,
        RunState.TIMED_OUT,
        RunState.BLOCKED,
    )
}


@app.post("/api/v1/audits/{audit_id}/cancel")
def cancel_audit(audit_id: str) -> dict[str, str]:
    row = get_audit(audit_id, db_path=_db())
    if row is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")
    if row["run_state"] in _TERMINAL:
        raise _error(409, "INVALID_INPUT", f"Audit already in terminal state: {row['run_state']}")
    update_audit_state(audit_id, RunState.CANCELLED, db_path=_db())
    return {"status": "cancelled", "audit_id": audit_id}
