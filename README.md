# BenchProof — Agentic Engineering Assurance Runtime

Hackathon build for the Coding and Agentic Engineering track. The runtime audits a
synthetic Python invoice service against human-approved executable constraints,
uses NVIDIA model inference on Nebius for bounded investigation and repair, and
accepts a patch only through a deterministic protected evaluator.

The full specification and plan live in [BenchProof_MD_Pack](BenchProof_MD_Pack/README.md).
Status and evidence are tracked in [PROGRESS_LOG.md](BenchProof_MD_Pack/planning/PROGRESS_LOG.md).

## Current state (5 October 2026, Days 1–3)

Implemented: FastAPI with health/ready/examples/constraints/audits/events,
idempotent audit creation, SQLite with leases, CAS transitions, ordered events and
immutable check results; a constraint registry (C-API, C-AMOUNT, C-INTEGRITY) with
manifest approval; five development fixtures with trusted expected properties and
reference repairs; an observation-based trusted evaluator; a local Docker runner
(network none, read-only, cleared env, timeout kill) with a protected launcher; a
Nebius Token Factory adapter with a real preflight; a heartbeat worker; a minimal UI.

Not implemented: graph/impact analysis, model-driven repair, patch policy, evidence
export, hosted sandbox execution (Nebius Sandboxes access not yet granted), owner auth.

## Setup (Windows, PowerShell)

Tested with Python 3.12.10, Node 24.12.0, npm 11.6.2, Docker Desktop 29.7.2.

```powershell
# backend
py -3.12 -m venv backend\venv
.\backend\venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
.\backend\venv\Scripts\python.exe -m pip install -e ".\backend[dev]" --no-deps
Copy-Item .env.example .env   # fill NEBIUS_API_KEY, then run the provider preflight to pin the model

# candidate runtime image (local isolated runner)
docker build -t benchproof-candidate:dev backend\runner\image

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

Open http://127.0.0.1:5173. The UI shows the real mode. Set `BENCHPROOF_RUNNER=docker`
in `.env` to have `/api/v1/ready` probe the local runner at startup.

## Checks

```powershell
Set-Location backend
.\venv\Scripts\python.exe -m pytest                                   # 76 tests; Docker tests skip without a daemon
.\venv\Scripts\python.exe scripts\validate_fixtures.py --suite development-v2
.\venv\Scripts\python.exe scripts\provider_preflight.py               # real catalog + inference + JSON check
.\venv\Scripts\python.exe scripts\runner_preflight.py                 # Sandboxes permissions + Docker runs + timeout negative
```

The fixture validator imports candidate code in-process. That is a development
tool only. The Docker runner is the tested isolated route for development; the
hosted route is still Nebius Sandboxes, pending beta access (see DECISIONS D-024).

## Layout

| Path | Purpose |
| --- | --- |
| `backend/benchproof/api` | FastAPI endpoints (audits, events, constraints, readiness) |
| `backend/benchproof/constraints` | Pinned owner-approved constraints, contract hash, manifest approval |
| `backend/benchproof/domain` | `benchproof/v2` typed records |
| `backend/benchproof/evaluator` | Check registry, observation oracle, gate, development harness |
| `backend/benchproof/execution` | Execution adapter contract, Docker runner, mock runner |
| `backend/benchproof/fixtures` | Fixture registry and source hashing |
| `backend/benchproof/providers` | Nebius Token Factory adapter |
| `backend/benchproof/storage` | SQLite migrations, audits, heartbeats, leases/events/immutability |
| `backend/runner/image` | Pinned candidate runtime image |
| `backend/runner/launcher` | Protected launcher that observes a candidate from inside its runtime |
| `backend/fixtures/development/<id>/app` | Candidate-visible synthetic service |
| `backend/fixtures/development/<id>/expected.json`, `reference/` | Trusted evaluator assets, never mounted into a candidate |
| `backend/scripts` | Provider/runner preflight, worker, fixture validation |
| `frontend/` | React/TypeScript/Vite UI |
