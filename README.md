# BenchProof — Task-Centered Coding Agent

Hackathon build for the Coding and Agentic Engineering track. Give the agent a
small Python task, customize its instructions, review its plan, then inspect a
real model-written patch and isolated test results. NVIDIA inference runs on
Nebius Token Factory. A secondary assurance workspace audits a synthetic invoice
service against a deterministic protected evaluator.

That protected gate applies to the curated invoice profile. Imported projects use their supplied unittest checks; passing them is scoped evidence, not independent proof of every requirement.

The full specification and plan live in [BenchProof_MD_Pack](BenchProof_MD_Pack/README.md).
Status and evidence are tracked in [PROGRESS_LOG.md](BenchProof_MD_Pack/planning/PROGRESS_LOG.md).

## Primary Experience: Task-Centered Coding Agent

BenchProof provides an end-to-end autonomous coding workflow:
**Project Intake -> Reviewed Plan -> Human Approval -> Isolated Candidate Execution -> Test Observation -> Bounded Multi-Turn Revision -> Checkpoint Rollback -> Verifiable Unified Diff**.

Implemented milestone areas (evidence scope matters):
- **C-01 to C-03**: Real model generation on Nebius, protected candidate execution, multi-turn revision feedback, and repeated-candidate stall detection.
- **C-04 & C-05**: Constrained project intake (manifest fingerprinting, path/secret protection), generic `unittest` runner, a real bugfix and a separate v3 staging feature pass after one model revision at output 4,096. Earlier failed feature runs remain recorded; imported checks establish only their declared scope.
- **C-06 & C-07**: Checkpoint history with CAS restore, pause/resume/cancel controls, unified diff viewer, test terminal console, and evidence ZIP export.
- **C-08 to C-10**: Mocked cloud failure-mode regressions, a frozen six-task scripted gold-answer regression, a recorded walkthrough, and a submission checklist ([SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md)). The scripted pass rate is not measured model performance; full held-out live-model evaluation remains open.
- **Customization**: Browser-local profiles, instruction-only SKILL.md import/export, reviewed versioned harness strategies, and an operator-allowlisted read-only MCP context bridge. See [AGENT_CUSTOMIZATION.md](AGENT_CUSTOMIZATION.md) for limits and setup.

The legacy assurance audit dashboard remains available as a secondary tab in the web interface.

## Public Demo & Status

Public demo: [benchproof.vercel.app](https://benchproof.vercel.app), hosted on Vercel with persistent storage and Nebius Token Factory inference.
Latest source verification (22 October): **663 backend tests passed in isolated Linux Docker; three Docker integrations passed separately; 29 frontend and 30 deployment/toolchain tests passed**. V3 adds line-based source transport, non-executing syntax validation, policy pinning and accurate stop messages. A separately authorized staging feature run reaches REVIEW_READY after one model revision: three calls, four isolated executions, all six fresh final checks pass at a 4,096-token response limit. Earlier failures remain in the record; this known-sample success is not a benchmark. The owner approves 4,096 for production without increasing daily limits. See [VERIFICATION.md](VERIFICATION.md) for rollout and version-specific evidence.
A customized real-model bugfix rehearsal reached REVIEW_READY with a pinned skill, reviewed harness and read-only documentation MCP snapshot: exactly **two model calls, one patch and three isolated executions**, with desktop/mobile download and reload verified. See [RELEASE_REHEARSAL.md](RELEASE_REHEARSAL.md). A later public feature/no-change batch matched **one of two** expected outcomes; the feature failed import, and its separately approved bounded revision was truncated. These are public integration checks, not a held-out benchmark or user study; [full outcomes](verification/README.md) retain both failures. Remaining work is tracked in [BUILD_PLAN.md](BUILD_PLAN.md).
V3 is deployed with the approved 4,096-token backend allowance; daily coding limits remain 40 model calls/60 isolated executions. Public cold-resume and desktop/mobile draft/export/reload checks pass without another inference call. Frontend: TypeScript / React 19. Future Git pushes do not automatically upgrade the trusted Sandbox runtime. The public documentation MCP endpoint is `/mcp`, with `read_guide` as its only tool; the bridge allows five MCP queries per UTC day.
The secondary assurance workspace includes audits, leases, ordered/resumable events and idempotent creation; Engineering-State
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
judging-period availability, confirmed credit reserve, broader trials, owner review
and actual submission remain release work. No-spend clean-clone API/worker/UI startup
and desktop/mobile checks pass. The corrected 2:18 walkthrough
labels its saved-task review and dated customization-rehearsal screenshot; exports
are not signed. See [video provenance](recordings/README.md); owner review remains open.

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

# terminal 2 — separately configured coding-task worker
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

### Enable live coding deliberately

The default `.env.example` is no-spend: the mock runner and disabled coding worker
cannot implement tasks. For live work, build/verify the isolated Docker runner,
set the exact Nebius model/key server-side, and set these operator values in the
root `.env` before starting both API and worker:

```dotenv
BENCHPROOF_RUNNER=docker
BENCHPROOF_CODING_ENABLED=true
BENCHPROOF_CODING_MODEL_CALLS_PER_DAY=4
BENCHPROOF_CODING_EXECUTIONS_PER_DAY=6
BENCHPROOF_CODING_OUTPUT_TOKENS=2048
BENCHPROOF_CODING_MAX_TASKS=100
BENCHPROOF_CODING_DEADLINE_EPOCH=REPLACE_WITH_APPROVED_UNIX_DEADLINE
```

Compute a one-hour admission deadline in PowerShell with
`[DateTimeOffset]::UtcNow.AddHours(1).ToUnixTimeSeconds()` and replace the placeholder
with that number. This is an admission deadline, not a guarantee of VM uptime or
remaining credits. Both processes must use the same configuration and database;
restart them after changes. These sample global allowances are request/execution
ceilings, not a currency guarantee. Creating a draft is free of inference; requesting
a model plan and starting implementation can spend credits. Do not run them without
an agreed envelope. A worker heartbeat alone does not prove coding admission.

Only **unittest** projects are supported. Pytest-labelled imports, including legacy
records used for new tasks, are rejected rather than silently run as unittest.
See [data retention and admission](DATA_RETENTION.md) for storage limits and deletion
semantics. Do not upload sensitive projects to this demo.

## Checks

```powershell
Set-Location backend
.\venv\Scripts\python.exe -m pytest tests/test_release_admission.py tests/test_coding_store.py tests/test_coding_api.py # no inference or candidate execution
.\venv\Scripts\python.exe scripts\run_coding_eval.py --scripted-smoke # gold-answer regression, Docker required; not a live-model benchmark
.\venv\Scripts\python.exe scripts\run_coding_loop.py                  # runs end-to-end coding loop verification with isolated runner
.\venv\Scripts\python.exe scripts\backup_restore.py backup --db-path benchproof.db --backup-dir ./backups  # WAL-consistent SQLite backup
.\venv\Scripts\python.exe scripts\validate_fixtures.py --suite development-v2
.\venv\Scripts\python.exe scripts\provider_preflight.py               # PAID: catalog + inference + JSON check; separate spending approval
.\venv\Scripts\python.exe scripts\runner_preflight.py                 # Sandboxes permissions + Docker runs + timeout negative
.\venv\Scripts\python.exe scripts\freeze_suites.py --verify             # frozen held-out assets still match truth.lock.json
.\venv\Scripts\python.exe scripts\run_bundle_replay.py                # new evidence directory; Docker required; no application DB writes
```

The complete backend suite includes legacy tests that import/launch fixture code.
Run that suite and the fixture validator only inside a dedicated isolated test
container, not directly on the laptop. The selected pytest command above uses mocks
and storage only. The scripted evaluation/replay and real coding loop require Docker
and are not live-model benchmarks. Nebius Sandboxes beta access is not required by
the hosted Vercel route. See [VERIFICATION.md](VERIFICATION.md) for dated test evidence
and [BUILD_PLAN.md](BUILD_PLAN.md) for remaining acceptance gates.

## License

Original BenchProof code, synthetic fixtures and documentation use [Apache-2.0](LICENSE).
See [NOTICE](NOTICE) and the [attribution inventory](BenchProof_MD_Pack/docs/22_LICENSE_AND_ATTRIBUTION.md)
for third-party components and outstanding release rights checks.
Submission guide and verification instructions are in [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md).

## Layout

| Path | Purpose |
| --- | --- |
| `backend/benchproof/coding` | Task-centered coding agent (store, worker, loop, evaluation suite, contracts) |
| `backend/benchproof/intake` | Constrained project intake, size/path validation, manifest fingerprinting |
| `backend/benchproof/api` | FastAPI endpoints (coding tasks, audits, events, gate, bundles, replay) |
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
| `backend/benchproof/storage` | SQLite migrations, audits, heartbeats, backup/restore, leases/events/immutability |
| `backend/runner/image` | Pinned candidate runtime image |
| `backend/runner/launcher` | Protected launcher that observes a candidate from inside its runtime |
| `backend/fixtures/development/<id>/app` | Candidate-visible synthetic service |
| `backend/fixtures/development/<id>/expected.json`, `reference/` | Trusted evaluator assets, never mounted into a candidate |
| `backend/fixtures/heldout/` | Frozen held-out suites, candidate diffs, manifests, `scope.json` and `truth.lock.json` |
| `backend/scripts` | Coding loop/eval runners, backup/restore, provider/runner preflight, worker |
| `artifacts/rehearsals/` | Persistent rehearsal evaluation reports (JSON and Markdown) |
| `frontend/` | Connected React 19/TypeScript/Vite task workspace & assurance UI |
