# BenchProof — Agentic Engineering Assurance Runtime

Hackathon build for the Coding and Agentic Engineering track. The runtime audits a
synthetic Python invoice service against human-approved executable constraints,
uses NVIDIA model inference on Nebius for bounded investigation and repair, and
accepts a patch only through a deterministic protected evaluator.

The full specification and plan live in [BenchProof_MD_Pack](BenchProof_MD_Pack/README.md).
Status and evidence are tracked in [PROGRESS_LOG.md](BenchProof_MD_Pack/planning/PROGRESS_LOG.md).

## Next build: task-centered coding agent

The [active build plan](BUILD_PLAN.md) moves the primary experience to project/task input -> reviewed plan -> real NVIDIA-generated edits -> isolated tests and bounded repair -> reviewable patch. It reuses the assurance/runtime foundation without claiming the current fixture dashboard already provides general project coding. New C-01–C-10 milestones are planned, not deployed. See the [17 October product/problem research](CODING_AGENT_RESEARCH_2026-10-17.md).

## Current state (16 October 2026)

Public demo: [benchproof.vercel.app](https://benchproof.vercel.app), hosted on Vercel Hobby with a persistent trusted Sandbox/Drive and Nebius inference. It does not depend on the owner's laptop. Cloud isolation/persistence, public live API checks and a fresh-browser create/verify/export/replay/download/reload journey pass. See [Vercel deployment](VERCEL_DEPLOYMENT.md) for evidence, quotas and remaining release gates.

Known limitation: one subsequent live diagnosis returned HTTP 422, and its failure is
retained. Model diagnosis/repair reliability still needs work; hosting success is not
a claim that every inference or final evaluation passes.

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
not a claim of production identity authentication. Nebius Sandboxes spawn permission
is unavailable, but the Vercel-hosted route uses the verified Docker boundary. B-17 runtime
hardening is recorded in `INTEGRITY_REPORT_v1.md`. The final evaluation assets are
frozen (B-18): `backend/fixtures/heldout/` holds the held-out repair suite `repair-r12-v1`
(twelve opaque cases, eight faulty and four clean, built from four source styles), the fixed
candidate gate suite `gate-v12-v1` (four valid and eight invalid candidates that all pass
the visible smoke gate), and manifests for `graph-g8-v1`, `freshness-f6-v1`,
`trajectory-w8-v1` and `mutants-m12-v1`. Every asset is pinned in `truth.lock.json`; the
R6/V6 fallback is predeclared by id (D-027). Final held-out outcomes do not exist yet;
the committed local runtime configuration is frozen, while hosting and B-21 trials remain open.

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

The B-19 fair-baseline harness (`backend/benchproof/trials/`) runs B0 (visible smoke gate),
B1 (the NVIDIA repair agent with visible tests and the raw probe only) and B2 (the same agent
plus graph context, protected feedback, evidence-based confirmation, the protected gate and
repeated-candidate stopping) under one set of hard limits. Each trial writes a sealed,
write-once record and is judged afterwards by a fresh run of the frozen protected evaluator;
`scripts/summarize_trials.py` scores records against trusted truth. The evaluation
configuration `backend/evaluation/eval-config-v1.json` is **frozen** for committed runtime
`ad1955703ccc484e380f40edab33afe764beb3ba` and the tested Docker image digest. Its identity
hash remains `210affd887e92863543e4a2d2749534ba98e2c8a57203c5e0402016600d0460e`.
This identifies a local evaluation configuration, not a deployed release. A runtime,
prompt, model, budget or image change needs a new configuration version and affected reruns.

The Linux deployment required a snapshot output-permission fix and uses a different
candidate image. The historical configuration does not describe the current runtime:
verification correctly reports `runtime_code_hash changed`. A new reviewed/committed
release configuration is required before final measurements.

Three live development B2 trials on 16 October are preserved in
`artifacts/trials/dev-live-release-20261016-1`: MC-01 was repaired and VERIFIED;
AC-01 ended `MALFORMED_OUTPUT` after both repair replies reached the output limit;
the clean case kept its source and independently VERIFIED, but its model call failed
with a connection error. These are development observations, not held-out measurements
or three successful live rehearsals. Fresh canonical-reference API/amount/clean bundle
replays and tamper rejection passed under Docker in
`artifacts/release-replay/20261016-release-1`. Reference repairs are not model-generated repairs.

Azure hosting is unavailable because the owner's subscription expired. Token Factory
inference remains operational; its credits do not establish access to a compute host.
The primary demo is [BenchProof on Vercel](https://benchproof.vercel.app), with same-origin
UI/API, persistent cloud storage, one action at a time and a shared daily action ceiling.
See [Vercel deployment](VERCEL_DEPLOYMENT.md) for operations and verification.
The [laptop/ngrok route](DEMO_HOSTING.md) remains an optional fallback only. Backup/restore,
judging-period availability, credit/pricing review, final trials, clean-clone
installation, video and submission remain release work.

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
.\venv\Scripts\python.exe -m pytest                                   # 235 passed on 16 Oct with Docker; 3 tests require Docker
.\venv\Scripts\python.exe scripts\validate_fixtures.py --suite development-v2
.\venv\Scripts\python.exe scripts\provider_preflight.py               # real catalog + inference + JSON check
.\venv\Scripts\python.exe scripts\runner_preflight.py                 # Sandboxes permissions + Docker runs + timeout negative
.\venv\Scripts\python.exe scripts\freeze_suites.py --verify             # frozen held-out assets still match truth.lock.json
.\venv\Scripts\python.exe scripts\freeze_eval_config.py --verify        # currently detects drift from the historical v1 runtime
.\venv\Scripts\python.exe scripts\run_bundle_replay.py                # new evidence directory; Docker required; no application DB writes
```

The fixture validator imports candidate code in-process. That is a development
tool only. The Docker runner is the tested isolated route locally and inside the
trusted Vercel Sandbox. Nebius Sandboxes beta access is not required by this hosted route.

## License

Original BenchProof code, synthetic fixtures and documentation use [Apache-2.0](LICENSE).
See [NOTICE](NOTICE) and the [attribution inventory](BenchProof_MD_Pack/docs/22_LICENSE_AND_ATTRIBUTION.md)
for third-party components and outstanding release rights checks.

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
