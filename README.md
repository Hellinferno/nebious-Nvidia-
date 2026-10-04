# BenchProof — Agentic Engineering Assurance Runtime

Hackathon build for the Coding and Agentic Engineering track. The runtime audits a
synthetic Python invoice service against human-approved executable constraints,
uses NVIDIA model inference on Nebius for bounded investigation and repair, and
accepts a patch only through a deterministic protected evaluator.

The full specification and plan live in [BenchProof_MD_Pack](BenchProof_MD_Pack/README.md).
Status and evidence are tracked in [PROGRESS_LOG.md](BenchProof_MD_Pack/planning/PROGRESS_LOG.md).

## Current state (Day 1, 4 October 2026)

Implemented: FastAPI scaffold with health/ready/examples/constraints/audit
endpoints, SQLite migrations, a constraint registry (C-API, C-AMOUNT,
C-INTEGRITY), five development fixtures with trusted expected properties and
reference repairs, a trusted evaluator with a deterministic gate, a heartbeat
worker, a provider adapter, and a minimal UI that reads real API records.

Not implemented: isolated candidate execution, graph/impact analysis, model-driven
repair, evidence export. Live mode is refused when no provider credentials exist.

## Setup (Windows, PowerShell)

Tested with Python 3.12.10, Node 24.12.0, npm 11.

```powershell
# backend
py -3.12 -m venv backend\venv
.\backend\venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
.\backend\venv\Scripts\python.exe -m pip install -e ".\backend[dev]" --no-deps
Copy-Item .env.example .env   # then fill NEBIUS_API_KEY / NEBIUS_MODEL_ID if you have them

# frontend
Set-Location frontend; npm ci; Set-Location ..
```

## Run

```powershell
# terminal 1 — API
Set-Location backend
.\venv\Scripts\python.exe -m uvicorn benchproof.api.main:app --host 127.0.0.1 --port 8000

# terminal 2 — worker (heartbeat only in this version)
Set-Location backend
.\venv\Scripts\python.exe scripts\start_worker.py

# terminal 3 — UI
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173. The UI shows the real mode: with no `.env` it reports
`mock — no provider credentials`.

## Checks

```powershell
Set-Location backend
.\venv\Scripts\python.exe -m pytest                                  # unit + fixture tests
.\venv\Scripts\python.exe scripts\validate_fixtures.py --suite development-v2
.\venv\Scripts\python.exe scripts\provider_preflight.py              # exits 1 without NEBIUS_API_KEY
```

The fixture validator imports candidate code in-process. That is a development
tool only; the automatic audit flow must use an isolated runner (not yet built).

## Layout

| Path | Purpose |
| --- | --- |
| `backend/benchproof/api` | FastAPI endpoints |
| `backend/benchproof/constraints` | Pinned owner-approved constraints and contract hash |
| `backend/benchproof/domain` | `benchproof/v2` typed records |
| `backend/benchproof/evaluator` | Trusted checks, gate, development harness |
| `backend/benchproof/fixtures` | Fixture registry and source hashing |
| `backend/benchproof/providers` | Nebius Token Factory adapter |
| `backend/benchproof/storage` | SQLite migrations, audits, heartbeats |
| `backend/fixtures/development/<id>/app` | Candidate-visible synthetic service |
| `backend/fixtures/development/<id>/expected.json`, `reference/` | Trusted evaluator assets, never mounted into a candidate |
| `backend/scripts` | Preflight, worker, fixture validation |
| `frontend/` | React/TypeScript/Vite UI |
