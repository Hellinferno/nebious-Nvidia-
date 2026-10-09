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
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from benchproof import __version__
from benchproof.constraints import contract_hash, get_constraint, list_constraints
from benchproof.constraints.approval import ensure_registry_executable
from benchproof.domain import AuditRecord, RunState
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


# ── Engineering-State Graph (Day 4 / B-07) ────────────────────────────────

@app.get("/api/v1/audits/{audit_id}/graph")
def get_audit_graph(audit_id: str) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

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
def get_audit_impact(audit_id: str) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

    from benchproof.fixtures import fixture_dir
    from benchproof.graph.builder import build_state_graph
    from benchproof.impact import analyze_impact

    app_dir = fixture_dir(audit["fixture_id"]) / "app"
    graph = build_state_graph(app_dir, audit["contract_hash"])
    impact = analyze_impact(graph)
    return impact.to_dict()


# ── NVIDIA Investigation & Probe Execution (Day 5 / B-08) ────────────────

@app.post("/api/v1/audits/{audit_id}/diagnose")
def diagnose_audit(audit_id: str) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

    from benchproof.investigation import InvestigationError, run_investigation

    try:
        res = run_investigation(
            fixture_id=audit["fixture_id"],
            audit_id=audit_id,
            db_path=_db(),
        )
        return res
    except InvestigationError as e:
        status_code = 409 if e.code in {"STALE_SOURCE", "CONTRACT_UNAPPROVED", "STALE_CONTEXT"} else 422
        raise _error(status_code, e.code, e.message)


# ── Actions Trajectory ───────────────────────────────────────────────────

@app.get("/api/v1/audits/{audit_id}/actions")
def get_audit_actions(audit_id: str) -> list[dict[str, Any]]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

    return list_actions(audit_id, db_path=_db())


# ── Restricted Patch Authoring & Import (Day 6 / B-09) ───────────────────

class ProposePatchRequest(BaseModel):
    diff: str
    base_source_hash: str
    target_files: list[str] = Field(default_factory=list)
    explanation: str = ""
    author: str = "nemotron-repair"


@app.post("/api/v1/audits/{audit_id}/patch")
def propose_patch(audit_id: str, req: ProposePatchRequest) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

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
        policy_result="APPROVED",
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
        },
        db_path=_db(),
    )

    return {
        "patch_id": patch_id,
        "audit_id": audit_id,
        "policy_result": "APPROVED",
        "diff_hash": diff_hash,
        "approved_paths": approved_paths,
        "changed_lines": changed_lines,
    }


@app.get("/api/v1/audits/{audit_id}/patches")
def get_audit_patches(audit_id: str) -> list[dict[str, Any]]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

    from benchproof.storage import list_patches
    return list_patches(audit_id, db_path=_db())


# ── Fresh Independent Acceptance Gate (Day 6 / B-10) ─────────────────────

class VerifyCandidateRequest(BaseModel):
    patch_id: str | None = None
    use_docker: bool = False


@app.post("/api/v1/audits/{audit_id}/verify")
def verify_audit_candidate(audit_id: str, req: VerifyCandidateRequest) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

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
        status_code = 409 if e.code in {"BUDGET_EXHAUSTED", "PATCH_NOT_FOUND"} else 422
        raise _error(status_code, e.code, e.message)


@app.get("/api/v1/audits/{audit_id}/gate")
def get_audit_gate_status(audit_id: str) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

    from benchproof.storage.lifecycle import list_check_results

    checks = list_check_results(audit_id, db_path=_db())
    return {
        "audit_id": audit_id,
        "gate_verdict": audit.get("gate_verdict", "PENDING"),
        "run_state": audit.get("run_state", "QUEUED"),
        "checks": checks,
    }


# ── Evidence Bundle Export & Independent Replay (Day 7 / B-11) ───────────

@app.post("/api/v1/audits/{audit_id}/bundle")
def create_audit_bundle(audit_id: str) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

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
) -> Any:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

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
def validate_audit_bundle(audit_id: str) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

    from benchproof.bundle import export_bundle, validate_bundle_nonexecuting

    bundles_dir = Path("artifacts") / "bundles"
    bundle_path = bundles_dir / f"benchproof-audit-{audit_id}.zip"
    if not bundle_path.exists():
        bundle_path, _ = export_bundle(audit_id, db_path=_db())

    return validate_bundle_nonexecuting(bundle_path)


@app.get("/api/v1/audits/{audit_id}/replay")
@app.post("/api/v1/audits/{audit_id}/replay")
def replay_audit_bundle(audit_id: str) -> dict[str, Any]:
    audit = get_audit(audit_id, db_path=_db())
    if audit is None:
        raise _error(404, "INVALID_INPUT", "Audit not found")

    from benchproof.bundle import export_bundle, replay_bundle

    bundles_dir = Path("artifacts") / "bundles"
    bundle_path = bundles_dir / f"benchproof-audit-{audit_id}.zip"
    if not bundle_path.exists():
        bundle_path, _ = export_bundle(audit_id, db_path=_db())

    replay_rec = replay_bundle(bundle_path)
    return replay_rec.model_dump()


