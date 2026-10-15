# BenchProof — Agentic Engineering Assurance Runtime

Hackathon build for the Coding and Agentic Engineering track. The runtime audits a
synthetic Python invoice service against human-approved executable constraints,
uses NVIDIA model inference on Nebius for bounded investigation and repair, and
accepts a patch only through a deterministic protected evaluator.

The full specification and plan live in [BenchProof_MD_Pack](BenchProof_MD_Pack/README.md).
Status and evidence are tracked in [PROGRESS_LOG.md](BenchProof_MD_Pack/planning/PROGRESS_LOG.md).

## Current state (14 October 2026, Days 1–15)

Implemented: curated intake; accepted executable constraints; durable owner-scoped
audits, leases, ordered/resumable events and idempotent creation; Engineering-State
Graph and deterministic impact context; bounded NVIDIA investigation; restricted
source-hash-bound repairs; an independent protected acceptance gate; immutable ZIP
evidence export, non-executing integrity validation and fresh replay; and a connected
responsive UI that restores the active audit and SSE cursor after reload; and a
dependency-aware decision ledger. Reviewed decisions enter context only while their
declared file/source/contract/graph hashes remain current. Changed or deleted
dependencies become sticky `STALE`, late provider responses and old-context patches
are rejected, and decision reasons/current versions are exported and shown in the UI.
Two identical no-progress source/action/failure attempts now enter `STALLED`.
One atomic recovery rebuilds current context, changes to a narrower named strategy,
and consumes the original limits without resetting counters; a repeated recovery
stall ends `BLOCKED`. The UI shows remaining actions and the one-recovery allowance.
Twelve versioned trusted semantic mutations (three each for API, amount, caller and
idempotency) now run in at most three relevant fresh branches after a VERIFIED
baseline. Results preserve killed, survived, invalid, skipped and unknown separately,
consume the audit's `max_executions` reserve, prove the accepted candidate hash is
unchanged, and remain an optional strength signal that cannot alter the gate verdict.
Remote cancellation stays `CANCEL_PENDING` until worker reconciliation confirms termination.

Owner access currently uses a browser-generated opaque capability in the required
`X-BenchProof-Owner` header. This is sufficient for the bounded local/demo boundary,
not a claim of production identity authentication. Hosted sandbox execution remains
blocked because Nebius Sandboxes spawn permission has not been granted. B-17 runtime
hardening is recorded in `INTEGRITY_REPORT_v1.md`. The final evaluation assets are
frozen (B-18): `backend/fixtures/heldout/` holds the held-out repair suite `repair-r12-v1`
(twelve opaque cases, eight faulty and four clean, built from four source styles), the fixed
candidate gate suite `gate-v12-v1` (four valid and eight invalid candidates that all pass
the visible smoke gate), and manifests for `graph-g8-v1`, `freshness-f6-v1`,
`trajectory-w8-v1` and `mutants-m12-v1`. Every asset is pinned in `truth.lock.json`; the
R6/V6 fallback is predeclared by id (D-027). Measured outcomes do not exist yet; the B-19
configuration freeze and B-21 trials are next.

Day 15 (B-22, self-review; no volunteer tester, so no user study is claimed) added a bounded
skill catalog: twelve slash skills (`/start` … `/cancel`) that map to existing endpoints and
report server-computed availability, cost class and blocked reason at `GET /api/v1/skills`
and `GET /api/v1/audits/{id}/skills`, with a Ctrl+K/`/` palette in the UI. Proposed diffs are
now `PENDING` until the protected gate approves or rejects them, and each gate run records its
check set as a numbered attempt. A second hardening pass makes the launcher run the candidate
in a child process whose record must match the written file, versions `worker-caller-path` to
v2 (live delegation plus observed worker idempotency), commits state changes with their events,
guards state writes on inactive audits, and computes every source, intake, dependency and
suite-lock hash over LF-normalized bytes; the held-out lock was re-frozen for that hashing with
unchanged assets (D-028).

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

Open http://127.0.0.1:5173. The UI shows the real mode, stores an opaque local owner
capability, and restores its last audit without issuing a second create request. Set
`BENCHPROOF_RUNNER=docker` in `.env` to have `/api/v1/ready` probe the local runner at
startup; daemon/image probe timeouts are reported as unavailable rather than crashing
the API.

## Checks

```powershell
Set-Location backend
.\venv\Scripts\python.exe -m pytest                                   # 175 passed on 14 Oct with the Docker image built (3 skips without it)
.\venv\Scripts\python.exe scripts\validate_fixtures.py --suite development-v2
.\venv\Scripts\python.exe scripts\provider_preflight.py               # real catalog + inference + JSON check
.\venv\Scripts\python.exe scripts\runner_preflight.py                 # Sandboxes permissions + Docker runs + timeout negative
.\venv\Scripts\python.exe scripts\freeze_suites.py --verify             # frozen held-out assets still match truth.lock.json
```

The fixture validator imports candidate code in-process. That is a development
tool only. The Docker runner is the tested isolated route for development; the
hosted route is still Nebius Sandboxes, pending beta access (see DECISIONS D-024).

## Layout

| Path | Purpose |
| --- | --- |
| `backend/benchproof/api` | FastAPI endpoints (owner-scoped audits, events, gate, bundles, replay) |
| `backend/benchproof/constraints` | Pinned owner-approved constraints, contract hash, manifest approval |
| `backend/benchproof/domain` | `benchproof/v2` typed records |
| `backend/benchproof/decisions` | Reviewed/proposed ledger, dependency invalidation and current-context rebuild |
| `backend/benchproof/evaluator` | Check registry, observation oracle, gate, development harness |
| `backend/benchproof/mutations` | Trusted versioned semantic templates, fresh-branch execution and strength scoring |
| `backend/benchproof/suites` | Frozen suite registry, truth-lock verification and agent-visibility leak scan |
| `backend/benchproof/evaluator/smoke.py` | Visible smoke gate (B0), kept separate from the protected gate |
| `backend/benchproof/execution` | Execution adapter contract, Docker runner, mock runner |
| `backend/benchproof/fixtures` | Fixture registry and source hashing |
| `backend/benchproof/providers` | Nebius Token Factory adapter |
| `backend/benchproof/trajectory` | Frozen action/failure fingerprints, stall policy and one bounded recovery |
| `backend/benchproof/storage` | SQLite migrations, audits, heartbeats, leases/events/immutability |
| `backend/runner/image` | Pinned candidate runtime image |
| `backend/runner/launcher` | Protected launcher that observes a candidate from inside its runtime |
| `backend/fixtures/development/<id>/app` | Candidate-visible synthetic service |
| `backend/fixtures/development/<id>/expected.json`, `reference/` | Trusted evaluator assets, never mounted into a candidate |
| `backend/fixtures/heldout/` | Frozen held-out suites, candidate diffs, manifests, `scope.json` and `truth.lock.json` |
| `backend/scripts` | Provider/runner preflight, worker, fixture validation |
| `frontend/` | Connected React/TypeScript/Vite assurance and evidence UI |
