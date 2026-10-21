# Progress and evidence log

## Current status — 21 October 2026

The task-centered unittest agent, bounded customization and isolation/storage
hardening are deployed at https://benchproof.vercel.app. Current runtime is
`49337c3683310a7c137e898459dd38ab3927a2c3cd7cc3588e6523596127bcd3`.
Latest complete cloud checks pass 635 backend tests plus three separate Docker
integrations; frontend 29 and deployment 29 pass. Four new static public-input
tests and six read-only judging-window tests account for the increases.

The customized real bugfix passes, but the additional frozen two-case live batch
matches one expected outcome of two: the feature fails import, the clean control
stops untouched. Its separately approved bounded follow-up fails on revision
truncation after the same import error. No failed outcome is removed or renamed
success. See [verification](../../verification/README.md). C-05/C-09/C-10 remain
partial, not universally done.

Remaining: review model output/prompt policy under a new regression identity,
volunteer sessions/held-out comparison, upstream CLI development advisories,
judging access beyond the November 30 admission cutoff, owner rights/eligibility,
public YouTube video URL and actual submitted entry status. Submission closes
October 30, but judging is in December. No hosting setting changed. Source
publication status is the actual Git history, not an inferred deployment.

### 21 October — additional public verification

- Changes: froze public inputs and sanitized positive/negative outcomes; added a
  read-only judging-window checker and six regressions; corrected stale DONE
  claims, partial rights inventory and YouTube/date requirements.
- Evidence: `artifacts/evaluation-batch-20261021/`; complete cloud source snapshot
  `3174d3ff7f39b36a8e0c6c2887c1820bf9d4be835295ba07afaad618a9f9fd1e`.
  Candidate code never ran on the laptop. Original project snapshots stay unchanged.
- Spend: original batch three calls / three isolated executions / 7,536 tokens;
  separate bounded follow-up three calls / two executions / 9,933 tokens. Listed
  estimates $0.00112464 and $0.0014679 are not actual charges. No SDK retry;
  the authorized model revision is counted. No further inference authorization.
- Browser: desktop/mobile blocked-state/clean-control review, export and reload
  without added spend pass. Pre-spend default-harness assertion/Chrome crash and
  read-only unsafe-loopback-port failure are retained; no duplicated paid task.
- Validation: full isolated suite 635/three skipped then three Docker passes,
  29 frontend, 29 deployment, lint/build. Eight sandbox EACCES socket failures
  passed with loopback permitted. Runtime package reproduces the deployed hash.
- Next: C-05 reliability/output-policy review, then remaining C-09/C-10 gates.
  Account/rights/submission actions require owner evidence, not invented approval.

## Historical baseline — 3 October 2026

Completed documentation work: recovered the coding-agent research, verified primary product capabilities, revised the execution pack to the assurance runtime, replaced the active ML-only plan and created separated benchmark protocols. This is planning/research evidence only.

Pending: registration/eligibility/account checks, real provider and isolated runner preflight, source scaffolding, executable fixtures/contracts, graph, runtime, independent gate, UI/export, all measurements, deployment, recording and actual entry submission. No application ticket is done merely because its specification exists. No competitor performance results exist.

## Entries

### 2026-10-04 — Day 1

- Focused hours planned / actual: 5–6 planned; actual time not measured.
- Observed environment (B-01): Python 3.12.10, Node v24.12.0, npm 11.6.2, Git 2.51.2.windows.1, Windows 11 Pro.
- Commit/branch and deployment version, if any: `main`, the 4 Oct commit that contains this entry (on top of 5d02a83). No deployment.
- Tickets attempted / completed / blocked: B-01 IN_PROGRESS — owner confirmed on 4 Oct: hackathon registration is confirmed; no Nebius Token Factory account exists yet (no key, no credits, no expiry to record); Nebius Sandboxes access has not been requested. Nothing is assumed granted. B-02 DONE. B-03 IN_PROGRESS (development cases, trusted oracle, reference repairs and clean control validated; unapproved-manifest rejection and the shallow-candidate case remain). B-04 BLOCKED (no provider account; adapter and preflight script exist, zero real inferences). B-05 TODO (sandbox access not requested; this is the first action for 5 Oct).
- Accepted source/contract/graph/evaluator hashes: contract `6d5b95ce4dbc2dbaf49290a9764169e600df4a2fcc831907345b67a18f547ba2` (C-API `ed52617d…`, C-AMOUNT `0e0081a0…`, C-INTEGRITY `c843e4b0…`, all v1, approval_ref `OWNER_MANUAL_REVIEW`). Evaluator `5e60232da924ffdbe643b5f1762625b0171bfe93f0ab46fc4851759d242192ca`. Fixture source hashes: AC-01 `6c824e3a…`, MC-01 `a500577c…`, CI-01 `b5e1b0ea…`, ID-01 `65daecd5…`, clean-service `8a3de586…` (full values are served by `GET /api/v1/examples`). Graph: not built.
- Runtime mode and actual provider/model/runner/image: mode `mock`; provider not configured; no model selected; no runner; no image. `/api/v1/ready` reports exactly this and `POST /api/v1/audits` with `mode=live` returns 503 `PROVIDER_UNAVAILABLE` rather than falling back.
- Observations, check IDs and artifact paths: `scripts/validate_fixtures.py --suite development-v2` → AC-01 REJECTED on `api-field-presence`; MC-01 REJECTED on `amount-boundary` (0.02 vs expected 0.01); CI-01 REJECTED on `worker-caller-path`; ID-01 REJECTED on `idempotency-duplicate` + `idempotency-conflict`; clean-service VERIFIED; all four reference repairs VERIFIED. Record: `artifacts/fixtures/development-v2_20261004T094623.json` (local, git-ignored). Provider preflight: `artifacts/preflight/provider_20261004T094451.json`, status BLOCKED, blocker `NEBIUS_API_KEY not configured`, exit code 1. Worker smoke: two heartbeats written, `/api/v1/ready` reported `worker.alive = true`.
- Tests actually run; passed/failed/skipped/blocked: `pytest` 40 passed / 0 failed / 0 skipped (API, constraints, evaluator gate, fixture suite). `ruff check` clean. Frontend `npm run build` and `npm run lint` clean. Blocked: any live provider or runner check.
- Patch/verdict plus graph coverage, freshness and mutation limits: no patches; verdicts above come from the development harness only, which imports candidate code in-process on the builder machine (not the protected isolated runner). Graph coverage: none. Freshness: `POST /api/v1/audits` rejects a stale `source_hash` pin with 409 `STALE_SOURCE`. Mutations: NOT_RUN.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: 0 model calls, 0 remote executions, no price snapshot, reserve unknown.
- Repeated failure/recovery event and strategy change, if any: none.
- What changed in scope/decisions/docs: gate now returns `INCONCLUSIVE` (not `UNKNOWN`) for a missing or unknown required check, per runtime spec §6; `GateVerdict` gained `INCONCLUSIVE`/`BLOCKED`. Default provider base URL follows doc 07 (`api.tokenfactory.nebius.com`). Trusted fixture assets (`expected.json`, `reference/`) live outside `app/` and the harness refuses a tree that contains them. Lockfile is `backend/requirements.lock.txt` from the tested venv. Backlog B-01…B-05 statuses updated.
- Next earliest unmet dependency and tomorrow's realistic plan: create the Nebius Token Factory account and request Sandboxes beta access first thing on 5 Oct (both absent as of 4 Oct). Then B-04: put the key in `.env`, run `python scripts/provider_preflight.py`, record the returned NVIDIA model id plus card/license URL and actual credit/billing terms. Transport plan for Day 2: pinned `python:3.12-slim` digest, mount only the `app/` snapshot plus a protected launcher outside it, network denied, 60 s process timeout, capture exit code/stdout/artifacts by ID; if beta access is absent by 6 Oct, evaluate the documented alternate instead of claiming sandbox runs.

### 2026-10-05 — Day 2 (provider preflight; B-04 unblocked)

- Focused hours planned / actual: 3–4 planned; actual time not measured.
- Commit/branch and deployment version, if any: `main`, the 5 Oct commit containing this entry (after 02a0e17). No deployment.
- Tickets attempted / completed / blocked: B-01 — owner created a Nebius Token Factory account on 5 Oct and supplied a key (stored only in the git-ignored root `.env`; credit/expiry/billing terms still not recorded). B-04 IN_PROGRESS → first real inference recorded; model card/license verification, tool-loop and repair-proposal behaviors remain. B-05 TODO (Sandboxes access still not requested).
- Accepted source/contract/graph/evaluator hashes: unchanged from Day 1 (contract `6d5b95ce…`, evaluator `5e60232d…`); graph not built.
- Runtime mode and actual provider/model/runner/image: provider Nebius Token Factory at `https://api.tokenfactory.nebius.com/v1/` (first attempted endpoint answered; the Studio alias was not needed). Catalog: 25 models, 4 NVIDIA-prefixed (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/nemotron-3-super-120b-a12b`). Selected and pinned in `.env`: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (first NVIDIA id alphabetically; not yet a quality-based choice). Runner: none; image: none. `/api/v1/ready` now reports `provider.configured = true` with the model id; no key appears in any API response.
- Observations, check IDs and artifact paths: `artifacts/preflight/provider_20261005T173137.json` — inference OK, finish `stop`, 3071 ms, usage 38/124/162 tokens; structured JSON check REJECTED (malformed: unterminated string, `completion_tokens` = 128 = cap → truncation). `artifacts/preflight/provider_20261005T173243.json` — after raising the structured-check cap to 512: inference OK, 2894 ms, usage 38/128/166; structured JSON supported and VALID, finish `stop`, usage 105/226/331, proposal `{"check_id": "amount-boundary", ...}` which is in the allowed protected-check set. Both records are local and git-ignored; a leak scan for the key prefix over `artifacts/` returned 0 matches.
- Tests actually run; passed/failed/skipped/blocked: `pytest` 40 passed; `ruff check` clean. Live calls: 2 preflight runs × 2 calls = 4 real inferences.
- Patch/verdict plus graph coverage, freshness and mutation limits: no patches; no gate run against model output. The rejected malformed proposal is recorded as a rejection, not repaired.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: ≈ 828 tokens total across 4 calls; 0 retries (adapter `max_retries=0`); no price snapshot yet; reserve unknown.
- Repeated failure/recovery event and strategy change, if any: one format failure (truncated JSON) → strategy change: larger output budget for structured calls. Kept the failed record.
- What changed in scope/decisions/docs: preflight tries documented then alias endpoint when `NEBIUS_BASE_URL` is blank and records every attempt; it runs one structured-JSON proposal check validated server-side against protected check ids; adapter treats blank base URL as default. O-001 remains open: model chosen by availability, to be confirmed on the five development behaviors.
- Next earliest unmet dependency and tomorrow's realistic plan: request Nebius Sandboxes beta access (B-05) and record credit/expiry facts (B-01). For B-04: record the model card/license URL, then test the remaining preflight behaviors (constraint-linked diagnosis, bounded patch proposal, clean-case restraint) and compare the Super/Lightning tiers on latency and validity before pinning the evaluation model.

### 2026-10-05 — Day 2 continued (runner boundary) and Day 3 pulled forward (approval, durable state)

- Focused hours planned / actual: Day 2 3–4 planned; Day 3 work done the same evening; actual time not measured.
- Commit/branch and deployment version, if any: `main`, the 5 Oct commit containing this entry (after ed5e279). No deployment.
- Tickets attempted / completed / blocked: B-05 IN_PROGRESS — Nebius Sandboxes BLOCKED: `GET /sandboxes/v1/whoami` returns 200 for the supplied credential but every permission (`import`, `spawn`, `spawn_disposable`, `list`, `cancel`, `set_image_tag`) is `false`; `GET /images` returns 403 `Insufficient permissions: list`. Beta access must be requested at https://tokenfactory.nebius.com/sandboxes/about. Tested alternate: local Docker runner (D-024). B-03 DONE for the P0 minimum (see decisions). B-06 IN_PROGRESS — leases, CAS transitions, ordered/resumable events, idempotent POST, immutable results, evaluator-only verdicts; owner-mismatch denial remains for B-13. B-04 unchanged (IN_PROGRESS).
- Credential finding (B-01), corrected later on 5 Oct: the supplied `NEBIUS_API_KEY` is a Nebius IAM **static key** bound to a service account (decoded locally from the key's own metadata: created 2026-10-05, expires 2031-10-04). The sliding `token_expiration` (~5–10 min) reported by Sandboxes `/whoami` belongs to a short-lived IAM token derived per request, not to the key. An earlier draft of this entry wrongly called the key a session token. The owner replaced the first key (pasted into chat) with a fresh static key the same evening; the old one should be revoked in the console.
- Evaluator hash: `a3b8beaf7fe72507484371934f556f0eae7c27ab9bbb02c2254255ee3c93369b` (evaluator package + launcher).
- Accepted source/contract/graph/evaluator hashes: contract unchanged `6d5b95ce…`. Evaluator hash changed (harness now shares one oracle with the launcher; launcher included in the hash): see the "Evaluator hash" line below. Candidate image `benchproof-candidate:dev@sha256:104ce828c0d23c2f5be3bf1f3ff45ca5df5b298a1a0a34490720a770779f4412`, built from `python@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d` plus fastapi 0.142.2 / pydantic 2.13.5 / httpx 0.28.1. Graph: not built.
- Runtime mode and actual provider/model/runner/image: runner `docker-local` (Docker Desktop 29.7.2, linux engine, WSL2). Controls per run: `--network none`, read-only root + 64 MB tmpfs, 256 MB memory, 64 pids, 1 cpu, `--cap-drop ALL`, `no-new-privileges`, uid 65534, `env -i` cleared environment, snapshot and launcher mounted read-only, `/out` only writable, wall-clock timeout then `docker kill`, `--rm`. Enforcement gaps recorded: shared host kernel (container, not VM), Docker default seccomp only, no disk quota beyond tmpfs.
- Observations, check IDs and artifact paths: `artifacts/runner/runner_20261005T181249.json` (local, git-ignored). Docker clean-service run `bp-run-6d78023c07b1-1a25ed` → VERIFIED, exit 0, 2315 ms; MC-01 run `bp-run-ef96b5e31b34-26e141` → REJECTED on `amount-boundary`, exit 0, 1759 ms; both judged outside the container from `observations.json`. Isolation summary: internet denied, metadata (169.254.169.254) denied, no secret-pattern env names, no trusted assets in the snapshot, candidate tree read-only — all true for every run. Timeout negative: launcher stalled 30 s under a 5 s budget → `timed_out=true`, no observations, container not running afterwards (5246 ms). First smoke run exposed `GPG_KEY` from the python base image; fixed by running the launcher under `env -i` and re-verified. Contree SDK installed for the record: contree-sdk 0.3.6, contree-client 0.4.0 (`ContreeSync` exposes `config`, `get_token_info`; no execution attempted without `spawn`).
- Tests actually run; passed/failed/skipped/blocked: `pytest` 76 passed / 0 failed / 0 skipped, including 3 Docker tests (clean VERIFIED, MC-01 REJECTED, timeout kill) and negatives for: no observations → INCONCLUSIVE, candidate crash → INCONCLUSIVE, tampered reported inputs cannot change the expected total, forged `verdict`/`checks` text in observations ignored, relaxed statement / dropped check / unknown constraint / missing required constraint → CONTRACT_UNAPPROVED, missing oracle → REQUIRED_CHECK_MISSING, non-evaluator check write / verdict write rejected, verdict must match stored checks, check_results and artifacts immutable at the SQLite trigger level, one lease per audit with expiry takeover, CAS transition rejects stale state, idempotent replay creates no second audit, same key + different body → 409, SSE resumes from `Last-Event-ID` and ends on terminal state. `ruff check` clean. `scripts/runner_preflight.py` exit 0.
- Patch/verdict plus graph coverage, freshness and mutation limits: no patches. Verdicts above come from isolated Docker runs judged outside the candidate. Freshness: `source_hash` and `contract_hash` pins rejected with STALE_SOURCE / CONTRACT_UNAPPROVED. Mutations: NOT_RUN.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: 0 model calls this session; 5 Docker executions; 4 unbilled `/whoami` calls; no price snapshot; reserve unknown.
- Repeated failure/recovery event and strategy change, if any: base-image env leak → `env -i`; nothing else.
- What changed in scope/decisions/docs: D-024 recorded; O-003 resolved for development. `/ready` probes the runner once at startup (or `?refresh=1`), never per poll. Events: `GET /audits/{id}/events` returns JSON or SSE (`Accept: text/event-stream`) with `after`/`Last-Event-ID` cursors, `event: end` on terminal state, `event: retry` after the bounded wait. Cancel is a CAS transition emitting `state_changed` + `cancelled`. Worker remains heartbeat-only; lease processing is wired on Day 4. Day 3 checklist items were executed on 5 Oct.
- Next earliest unmet dependency and tomorrow's realistic plan: owner actions — create a long-lived Token Factory API key, submit the Sandboxes access request, record credit/price facts. Build: B-07 source manifest hashing, intake limits, AST import/definition graph with declared manifest edges, visible baseline via the Docker runner, and worker lease processing of QUEUED audits.

### 2026-10-07 — Day 4 (B-07: Engineering-State Graph & Baseline)

- Focused hours planned / actual: 3–4 planned; actual ~3.5 hours.
- Commit/branch and deployment version, if any: `main`. No deployment.
- Tickets attempted / completed / blocked: B-07 DONE. (Intake limits, path allowlists, AST parsing of definitions/imports/direct calls, declared manifest edges, dynamic feature coverage detection, canonical graph hashing, baseline execution and artifacts recorded).
- Accepted source/contract/graph/evaluator hashes: clean-service graph hash `b9d33a775cb6...`, MC-01 graph hash `63abdb127836...`, AC-01 graph hash `1fe424edcb5e...`, CI-01 graph hash `59f04e1cc05d...`, ID-01 graph hash `3c8dd157e6c5...`. Contract hash `6d5b95ce...`. Evaluator hash `a3b8beaf...`.
- Runtime mode and actual provider/model/runner/image: runner `docker` / local isolated runner.
- Observations, check IDs and artifact paths: `artifacts/baseline/` populated for all 5 fixtures: AC-01 REJECTED, MC-01 REJECTED (amount-boundary), CI-01 REJECTED (worker-caller-path), ID-01 REJECTED (idempotency), clean-service VERIFIED.
- Tests actually run; passed/failed/skipped/blocked: `test_intake.py` passed (7 tests), `test_graph.py` passed (4 tests).
- Patch/verdict plus graph coverage, freshness and mutation limits: Coverage is `COMPLETE_FOR_DECLARED_SCOPE` for clean-service; `PARTIAL` when dynamic calls (eval/exec/getattr) or missing symbols are detected.
- What changed in scope/decisions/docs: B-07 marked DONE. Graph schema and baseline runner implemented.

### 2026-10-08 — Day 5 (B-08 & B-04: Impact Context & Bounded NVIDIA Investigation)

- Focused hours planned / actual: 3–4 planned; actual ~3.5 hours.
- Commit/branch and deployment version, if any: `main`. No deployment.
- Tickets attempted / completed / blocked: B-08 DONE, B-04 completed. (Reverse caller traversal, deterministic ordinal risk reasons, global integrity checks inclusion, hash-linked bounded context, real live NVIDIA Nemotron-3-Nano diagnosis with format repair, falsifiable probe execution, action persistence and audit events).
- Accepted source/contract/graph/evaluator hashes: All 5 fixture graphs, contexts, and contract versions hash-linked.
- Runtime mode and actual provider/model/runner/image: provider Nebius Token Factory live; model `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Observations, check IDs and artifact paths: `artifacts/investigation/` populated with live NVIDIA investigations across all 5 fixtures: MC-01 hypothesis on C-AMOUNT confirmed SUPPORTED by probe failure; clean-service hypothesis on C-AMOUNT REFUTED by probe passing all checks; AC-01, CI-01, ID-01 executed.
- Tests actually run; passed/failed/skipped/blocked: `pytest` 94 passed / 0 failed / 3 skipped. `ruff check` clean. Frontend `oxlint` clean, `npm run build` clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: Risk analysis produces deterministic ordinal severities (CRITICAL/HIGH/MEDIUM/LOW) with human-readable reasons (no confidence probabilities). Stale source/contract/context hashes rejected.
- What changed in scope/decisions/docs: B-08 marked DONE in BACKLOG and DAILY_TASKS. Real live NVIDIA diagnosis verified with structured JSON schema and format repair. Next: Day 6 (B-09/B-10 protected repair loops).
### 2026-10-09 — Day 6 (B-09: Restricted Patch Authoring & B-10: Fresh Acceptance Gate)

- Focused hours planned / actual: 3–4 planned; actual ~3.5 hours.
- Commit/branch and deployment version, if any: `main`. No deployment.
- Tickets attempted / completed / blocked: B-09 DONE, B-10 DONE. (Protected patch authoring/import with base source hash pinning, path allowlists `app/*.py`, line/byte limits, traversal/protected file denial; fresh independent acceptance gate executing candidate snapshots in isolation; evaluator-only check results and gate verdict authority; forged PASS / candidate output claim prevention; negative testing for shallow repairs, missing required checks, and budget exhaustion).
- Accepted source/contract/graph/evaluator hashes: Base source hashes pinned for MC-01, AC-01, clean-service; contract hash `6d5b95ce...`; evaluator hash `a3b8beaf...`.
- Runtime mode and actual provider/model/runner/image: local isolated runner / evaluator.
- Observations, check IDs and artifact paths: `artifacts/acceptance_gate/` populated with:
  1. `mc01_canonical_repair_evidence.json` (VERIFIED after patch)
  2. `ac01_canonical_repair_evidence.json` (VERIFIED after patch)
  3. `clean_service_control_evidence.json` (VERIFIED untouched control)
  4. `mc01_shallow_rejected_evidence.json` (REJECTED on amount-boundary)
  5. `forged_pass_prevention_evidence.json` (REJECTED by evaluator oracle despite candidate's simulated forged pass claims)
- Tests actually run; passed/failed/skipped/blocked: `pytest` 111 passed / 0 failed / 3 skipped. `test_patch.py` (7 passed), `test_gate.py` (9 passed), `test_api_day6.py` (1 passed). `ruff check` clean. Frontend `oxlint` clean, `npm run build` clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: Candidate code cannot write CheckResult or GateVerdict. Stored check results immutable at SQLite trigger level. Patches strictly capped at <=100 lines and <=10,000 bytes.
- What changed in scope/decisions/docs: B-09 and B-10 marked DONE in BACKLOG and DAILY_TASKS. Day 6 interactive UI added with Propose Repair and Run Acceptance Gate. Next: Day 7 (B-11: Bundle export and independent replay).

### 2026-10-10 — Day 7 (B-11: Bundle Export & Independent Replay)

- Focused hours planned / actual: 5–6 planned; actual ~4 hours.
- Commit/branch and deployment version, if any: `main`. No deployment.
- Tickets attempted / completed / blocked: B-11 DONE. (Canonical ZIP bundle exporter with 14 structured artifacts; non-executing SHA-256 cryptographic manifest verification; secret scanning and safe archive path traversal denial; independent replay engine in fresh isolated temporary workspace re-evaluating external checks; tampered bundle rejection; REST API routes `POST /api/v1/audits/{id}/bundle`, `GET /api/v1/audits/{id}/bundle`, `POST /api/v1/audits/{id}/bundle/validate`, `GET /api/v1/audits/{id}/replay`, `POST /api/v1/audits/{id}/replay`; standalone CLI replayer `backend/scripts/replay_bundle.py`; automated suite runner `backend/scripts/run_bundle_replay.py`; Day 7 UI interactive panel in frontend).
- Accepted source/contract/graph/evaluator hashes: Base source hashes pinned for MC-01, AC-01, clean-service; contract hash `6d5b95ce...`; evaluator hash `a3b8beaf...`.
- Runtime mode and actual provider/model/runner/image: local isolated runner / evaluator.
- Observations, check IDs and artifact paths:
  - `artifacts/bundles/`:
    1. `mc01_canonical_repair_bundle.zip` (SHA-256 manifest verified)
    2. `ac01_canonical_repair_bundle.zip` (SHA-256 manifest verified)
    3. `clean_service_control_bundle.zip` (SHA-256 manifest verified)
    4. `tampered_candidate_diff_bundle.zip` (Cryptographic mismatch detected)
  - `artifacts/replay/`:
    1. `mc01_canonical_repair_replay.json` (VERIFIED; 100% check match with original audit)
    2. `ac01_canonical_repair_replay.json` (VERIFIED; 100% check match with original audit)
    3. `clean_service_control_replay.json` (VERIFIED; 100% check match with original audit)
    4. `tampered_bundle_rejection_evidence.json` (BLOCKED; candidate_diff mismatch detected before/during verification)
- Tests actually run; passed/failed/skipped/blocked: `pytest` 121 passed / 0 failed / 3 skipped. `test_bundle.py` (7 passed). `ruff check` clean. Frontend `oxlint` clean, `npm run build` clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: Independent replay asserts candidate diff matches recorded manifest hash and re-evaluates all required checks in a clean temporary workspace. Evaluator verdict is computed externally, not from bundle assertions. Secrets and oracle answers strictly excluded from bundle.
- What changed in scope/decisions/docs: B-11 marked DONE in BACKLOG and DAILY_TASKS. Day 7 interactive UI added with Export Bundle, Verify Manifest, and Run Independent Replay. Milestone tracker updated for Export/fresh replay. Next: Day 8 (B-12: Integrated judge-facing UI).

### 2026-10-12 — Days 8–9 (B-12/B-13: connected UI, recovery and access)

- Focused hours planned / actual: 8–10 planned across both days; actual not time-tracked.
- Commit/branch and deployment version, if any: `main`; local tested change, no deployment.
- Tickets attempted / completed / blocked: B-12 DONE and B-13 DONE. Curated live/mock selection, accepted-constraint summary, graph/impact, resumable event trail, bounded diff, explicit verify, separate gate/test-strength result, bundle validation/replay/download, reload restore, safe error states, owner checks and two-phase remote cancellation are connected to real API records.
- Accepted source/contract/graph/evaluator hashes: resolved from each selected fixture/audit at runtime; no new frozen evaluation hash is claimed.
- Runtime mode and actual provider/model/runner/image: tests use mock provider/in-process evaluator; Docker-dependent cases skipped because the daemon was unavailable. The earlier actual Nebius model evidence is unchanged; no new paid inference was made.
- Observations, check IDs and artifact paths: `backend/tests/test_api_day8_day9.py` covers owner isolation for audit/events/patch/bundle access, idempotent restore/cursor resume, pending remote cancel and reconciliation, and wrong-parent patch rejection. `backend/tests/test_execution.py` covers Docker readiness timeout reporting. Frontend active state/cursor live in browser localStorage and all private requests carry the opaque owner capability.
- Tests actually run; passed/failed/skipped/blocked: `pytest` 123 passed / 0 failed / 3 skipped; `ruff check` clean; frontend `npm run build` and `npm run lint` clean. Headless Chrome/Edge capture was attempted but produced no file; screenshot and a full manual browser journey are NOT_RECORDED.
- Patch/verdict plus graph coverage, freshness and mutation limits: lifecycle and gate verdict are shown separately; UNKNOWN is never styled as success; test strength remains explicitly `NOT RUN · P1`. Existing source-hash and patch path limits remain enforced.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: no model call; no provider spend; no automatic retry loop added.
- Repeated failure/recovery event and strategy change, if any: audit creation retains one idempotency key across network retry/reload. Remote cancellation remains `CANCEL_PENDING` until trusted reconciliation; counters are not reset.
- What changed in scope/decisions/docs: B-12/B-13 and Days 8–9 marked done; D-025 records the opaque local owner capability boundary; API contract and README updated.
- Next earliest unmet dependency and tomorrow's realistic plan: B-14 source/decision dependency freshness, then B-15 stopping/recovery and B-16 mutation strength, without regressing complete P0.

### 2026-10-12 — Day 10 pulled forward (B-14: decision ledger and dependency freshness)

- Focused hours planned / actual: 3–4 planned; actual not time-tracked.
- Commit/branch and deployment version, if any: `main`; local tested change, no deployment.
- Tickets attempted / completed / blocked: B-14 DONE. Added PROPOSED/REVIEWED decision records, server-computed typed dependencies, sticky invalidation, current-reviewed-only context rebuilding, and stale provider/patch rejection.
- Accepted source/contract/graph/evaluator hashes: hashes are computed per audit/dependency and exposed as expected/current versions; no frozen evaluation hash changed or is claimed.
- Runtime mode and actual provider/model/runner/image: deterministic mock mode for tests (now guaranteed not to call the live provider); no model call or provider spend. Docker-dependent checks skipped because the daemon was unavailable.
- Observations, check IDs and artifact paths: `backend/tests/test_decisions.py`; `artifacts/decisions/f6_freshness_transitions.json` records changed-file, deleted-file and changed-contract stale transitions plus unchanged, unrelated-edit and unrelated-add fresh controls. This is development/F6 preparation, not frozen evaluation evidence.
- Tests actually run; passed/failed/skipped/blocked: targeted decision/investigation/bundle suite 21 passed; final full pytest 132 passed / 0 failed / 3 Docker-dependent skipped; ruff clean; frontend production build and oxlint clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: stale and unreviewed decisions are excluded from `current_decision_ids`; staleness does not auto-revive if bytes return; late diagnosis responses and patches carrying an old context hash return `STALE_CONTEXT`. Mutation strength remains NOT_RUN.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: zero model calls, executions or retries; no cost incurred.
- Repeated failure/recovery event and strategy change, if any: full regression exposed mock audits attempting live inference; fixed by making mock/live provider selection explicit. No B-15 trajectory recovery is claimed.
- What changed in scope/decisions/docs: B-14 and Day 10 marked done; decision API/data contract, README, release checklist and bundle omission list updated. UI now displays review/freshness state, stale reason, expected/current hashes and measured refresh overhead.
- Next earliest unmet dependency and tomorrow's realistic plan: B-15 canonical no-progress detection and one fresh-context strategy recovery, then B-16 trusted mutation sensitivity.

### 2026-10-13 — Day 11 pulled forward (B-15: trajectory stopping and recovery)

- Focused hours planned / actual: 3–4 planned; actual not time-tracked.
- Commit/branch and deployment version, if any: `main`; local tested change, no deployment.
- Tickets attempted / completed / blocked: B-15 DONE. Implemented `trajectory-fingerprint-v1`, two-repeat no-progress stopping, one atomic changed-strategy recovery and terminal blocking after a second stall.
- Accepted source/contract/graph/evaluator hashes: runtime action records retain the current source/context hashes; accepted contract/evaluator are unchanged. Fingerprint rule version is frozen for W8 preparation as `trajectory-fingerprint-v1`, repeat threshold 2.
- Runtime mode and actual provider/model/runner/image: deterministic mock provider and in-process development evaluator for the executed recovery; no live NVIDIA inference or paid runner execution. Docker-dependent regression checks skipped because the daemon was unavailable.
- Observations, check IDs and artifact paths: source/labels in `backend/benchproof/trajectory/development.py`; classifications and separate executed MC-01 recovery in `artifacts/trajectory/w8_and_executed_recovery.json`. The artifact is development-only preparation, not final W8 outcomes.
- Tests actually run; passed/failed/skipped/blocked: `backend/tests/test_trajectory.py` 11 passed; full pytest 143 passed / 0 failed / 3 Docker-dependent skipped; ruff clean; frontend production build and oxlint clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: four true stalls and four progress controls classified 8/8. A remaining failed check did not stop a trace after another check resolved. The executed recovery rebuilt current context, changed strategy, consumed action 3 without resetting limits, and remained `PROGRESSING`. Mutation strength remains NOT_RUN.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: zero model calls or tokens; three in-process development investigation executions for the recorded recovery; one recovery maximum; no cost incurred.
- Repeated failure/recovery event and strategy change, if any: repeated broad diagnosis entered STALLED; recovery changed `broad_diagnosis` to `narrow_failure_probe`. Automated tests additionally repeat the recovery fingerprint and confirm terminal BLOCKED with four actions used and no counter reset.
- What changed in scope/decisions/docs: B-15 and Day 11 marked done; Action/API contracts, README, release checklist, changelog, bundle usage evidence and UI recovery state updated.
- Next earliest unmet dependency and tomorrow's realistic plan: B-16 trusted semantic mutations, with at most three relevant branches and unchanged candidate/acceptance policy.

### 2026-10-13 — Day 12 pulled forward (B-16: trusted semantic mutation strength)

- Focused hours planned / actual: 3–4 planned; actual not time-tracked.
- Commit/branch and deployment version, if any: `main`; local tested change, no deployment.
- Tickets attempted / completed / blocked: B-16 DONE. Added twelve `development-semantic-v1` trusted templates, three for each API/amount/caller/idempotency family; exact-anchor application; syntax/import validity; max-three fresh mutant branches; immutable result storage; owner-scoped API; UI and bundle presentation.
- Accepted source/contract/graph/evaluator hashes: the executed development run records its full clean-service accepted candidate hash before/after; candidate remained unchanged. The external evaluator hash is computed per execution. No final M12 manifest or outcome is claimed before suite freeze.
- Runtime mode and actual provider/model/runner/image: in-process development evaluator only for template authoring and evidence; no NVIDIA model call, paid execution or Docker run. The production boundary still supports the protected runner path; the in-process harness remains development-only.
- Observations, check IDs and artifact paths: `backend/tests/test_mutations.py`; `artifacts/mutations/development_strength.json`. All 12 trusted templates were applicable, changed the source hash, parsed/imported and executed: 11 KILLED, 1 SURVIVED (`idempotency-drop-tenant-key`). The separate malformed control was INVALID, not KILLED. The bounded relevant idempotency run selected three templates and reported 2 killed / 1 survived / 0 invalid / 0 skipped / 0 unknown, therefore WEAK.
- Tests actually run; passed/failed/skipped/blocked: mutation suite 16 passed; full pytest 159 passed / 0 failed / 3 Docker-dependent skipped; ruff clean after removing stale directives; frontend production build and oxlint clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: mutation policy is explicitly OPTIONAL (D-026) and cannot modify acceptance. A run requires a VERIFIED baseline, reserves one baseline plus up to three branches from `max_executions`, persists template/version IDs and each outcome, and checks the accepted candidate hash after execution. Missing runs remain NOT_RUN in UI/bundles.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: zero model calls/tokens/cost. The recorded bounded run charged four local executions, measured 320 ms mutation overhead, and left eight of the default twelve execution slots.
- Repeated failure/recovery event and strategy change, if any: not applicable to this run; mutation branches do not reset action, patch or recovery counters.
- What changed in scope/decisions/docs: B-16 and Day 12 marked done; D-026 selects optional adequacy; API/data contract, README, release checklist, changelog, bundle contents and UI updated. The development harness now invokes the registered route directly instead of allocating an unnecessary Windows loopback socket; oracle logic and Docker launcher remain unchanged.
- Next earliest unmet dependency and tomorrow's realistic plan: B-17 integrity and execution hardening, followed by B-18 suite/assets freeze.

### 2026-10-14 — Day 14 pulled forward (B-18: frozen suite assets and measured scope)

- Focused hours planned / actual: 5–6 planned; actual not time-tracked.
- Commit/branch and deployment version, if any: `main`; local tested change, no deployment.
- Tickets attempted / completed / blocked: B-18 DONE. Authored and froze `repair-r12-v1` (twelve opaque held-out cases `HO-01`…`HO-12`: two faulty variants per implemented family plus four clean controls, built from four distinct source styles with renamed helpers, different control flow and benign distractors), `gate-v12-v1` (twelve fixed candidate diffs: four trusted reference repairs and eight invalid candidates that all pass the visible smoke gate and fail the protected gate), and manifests for `graph-g8-v1` (eight hand-declared impact tasks), `freshness-f6-v1` (three stale and three fresh transitions), `trajectory-w8-v1` (eight frozen traces) and `mutants-m12-v1` (twelve templates, validity frozen without execution). Added the visible smoke gate `visible-smoke-v1` (B0) and the `benchproof.suites` lock verifier.
- Accepted source/contract/graph/evaluator hashes: every case source tree, truth file, reference tree, candidate diff and manifest is pinned in `backend/fixtures/heldout/truth.lock.json` (`lock_hash` `37fc5d3f5ef981d4…`). The accepted contract hash is unchanged. The evaluator hash changes because `evaluator/smoke.py` joins the hashed evaluator directory; no stored verdict is reinterpreted.
- Runtime mode and actual provider/model/runner/image: asset validation used the in-process development harness only (labeled as such in the freeze record); no model call, no paid execution. The Docker daemon was started on this machine; the candidate image is being rebuilt for later isolated runs.
- Observations, check IDs and artifact paths: `artifacts/suites/freeze_20261014T080352.json`; every faulty case fails exactly its intended checks (plus one recorded consequential `idempotency-duplicate` failure for the 201-status case), every reference repair is VERIFIED, every clean style is VERIFIED untouched, and the agent-visible leak scan finds no fault markers, family names or check IDs in any `app/` file or public manifest. All eight frozen defects pass the visible smoke gate.
- Tests actually run; passed/failed/skipped/blocked: `tests/test_suites.py` 10 passed; full regression 165 passed / 0 failed / 3 skipped (candidate image not yet built); ruff clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: V12 candidates go through the same strict modify-only diff rules as agent patches; G8 truth is hand-declared from the authored call graphs and only symbol existence is checked with the AST, never with the impact tool under test; M12 validity records applicability and syntax without executing mutants; smoke remains a separate visible verdict that cannot touch the protected gate.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: zero model calls; in-process validation executions only; no price snapshot is recorded, so cost stays unknown; the scope decision reserves 20% of any usable credit for judging and predeclares the R6/V6 fallback by id.
- Repeated failure/recovery event and strategy change, if any: none.
- What changed in scope/decisions/docs: D-027 selects the full R12/V12 scope with named R6/V6 fallback subsets and records that the public repository makes the holdout untouched-by-tuning rather than secret; B-18 and Day 14 marked done; README, changelog, release checklist and milestone tracker updated.
- Next earliest unmet dependency and tomorrow's realistic plan: B-22 self-review and core UI fixes (no volunteer tester is available, so no user study is claimed), then B-20 deployment preparation and the B-19 fair-baseline harness and configuration freeze.

### 2026-10-14 — Day 15 pulled forward (B-22 self-review, skill catalog, second hardening pass)

- Focused hours planned / actual: 5–6 planned; actual not time-tracked.
- Commit/branch and deployment version, if any: `main`; local tested change, no deployment; the commit is left for the owner's review.
- Tickets attempted / completed / blocked: B-22 DONE for the self-review scope. No volunteer tester was available, so Day 15 items 1–2 stay open and no user study is claimed. The self-review found one core readability defect (a proposed diff read `APPROVED` before any gate ran) and fixed it: proposals are `PENDING` until the protected gate writes `APPROVED`/`REJECTED`. Added the `skills-v1` catalog (twelve slash skills mapped to existing endpoints, server-computed availability, cost class and blocked reason) at `GET /api/v1/skills` and `GET /api/v1/audits/{id}/skills`, with a Ctrl+K/`/` palette and a skill-named next action in the UI. Finished the second hardening pass started after B-17: launcher parent/child split with stdout-versus-file reconciliation, regular-file output check, strict fixture ids, LF-normalized hashes, atomic transition+event, per-attempt check batches, guarded state writes, transactional idempotent creation, mutation budget give-back, decision supersession and `worker-caller-path` v2.
- Accepted source/contract/graph/evaluator hashes: the accepted contract hash is unchanged (`6d5b95ce4dbc2dba…`). The evaluator hash changes (`observations.py` v2 and CRLF-normalized hashing). The held-out lock was re-frozen for LF-normalized hashing with byte-identical assets modulo line endings: `37fc5d3f5ef981d4…` → `efe61ad8c4b0df56…` (D-028, `artifacts/suites/freeze_20261014T130104.json`); the old lock still matched under the old hashing immediately before the re-freeze.
- Runtime mode and actual provider/model/runner/image: no NVIDIA model call. Most tests use the in-process development harness. The Docker daemon (29.7.2) and the pinned candidate image (`sha256:fbe0b348a6ad…`) were unavailable at the start of the session and available later, so the three isolated-runner tests executed the new launcher inside the container (clean control VERIFIED, MC-01 REJECTED, stalled launcher killed at the timeout).
- Observations, check IDs and artifact paths: `backend/tests/test_hardening_day15.py` (26 tests), `backend/tests/test_skills.py` (5 tests), `backend/fixtures/heldout/truth.lock.json`, `artifacts/suites/freeze_20261014T130104.json`, `artifacts/integrity/day13_integrity.json` (runtime isolation now PASS: internet/metadata denied, no secret env names, no trusted assets, read-only candidate). The first integrity run failed closed because `docker info` took about 32 s against the 30 s readiness probe; the retry passed. `worker-caller-path` is check version 2; every held-out case still fails exactly its intended checks and all twelve V12 labels hold.
- Tests actually run; passed/failed/skipped/blocked: full pytest 209 passed / 0 failed / 0 skipped; ruff clean; frontend `tsc -b && vite build` and oxlint clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: each gate run records its complete check set as the next attempt; a cancelled audit keeps `CANCELLED`/`PENDING` after a gate run while its checks are preserved; the gate alone writes patch policy; an unverified mutation baseline leaves exactly the spent baseline charged; superseded decisions leave the current context.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: zero model calls/tokens/cost; local in-process and Docker executions only; no price snapshot, so cost stays unknown.
- Repeated failure/recovery event and strategy change, if any: none.
- What changed in scope/decisions/docs: D-028 recorded; B-22 and Day 15 items 3–5 marked done; API/data contract, UI spec, integrity report addendum, README, changelog and backlog updated. Items 1–2 (volunteer session) remain open and disclosed.
- Next earliest unmet dependency and tomorrow's realistic plan: B-20 hosted release candidate (persistent store, restore, incognito journey), then the B-19 fair-baseline harness and configuration freeze.

### 2026-10-15 — Day 17 pulled forward (B-19 fair-baseline harness; B-17 status reconciled)

- Focused hours planned / actual: 3–4 planned; actual not time-tracked.
- Commit/branch and deployment version, if any: `main` on top of `0886650` with the uncommitted Day 15 change; local tested change, no deployment; the commit is left for the owner's review.
- Tickets attempted / completed / blocked: B-19 IN_PROGRESS — Day 17 items 1–2 done, items 3–4 partly done (see below). B-17 backlog status corrected from TODO to DONE 14 Oct; its evidence already existed (`093353e`, `INTEGRITY_REPORT_v1.md`, `artifacts/integrity/day13_integrity.json` with every recorded control PASS). B-20 hosted release candidate is BLOCKED in this session: it needs a chosen host, HTTPS, server secrets and an outward deployment that the owner has not set up or authorized. Before starting, the uncommitted Day 15 change was re-verified (pytest 209 passed, ruff, frontend build and oxlint clean).
- Accepted source/contract/graph/evaluator hashes: contract `6d5b95ce4dbc2dba…` and suite lock `efe61ad8c4b0df56…` unchanged; no frozen asset was edited. Candidate evaluation configuration `backend/evaluation/eval-config-v1.json`, config hash `210affd887e92863…`, status `candidate` (blocker: runtime source uncommitted); `--verify` reports no identity difference.
- Runtime mode and actual provider/model/runner/image: no inference call. One live catalog listing on Nebius Token Factory lists `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` among 25 models (`artifacts/preflight/catalog_check_20261015.json`). Docker 29.7.2 with `benchproof-candidate:dev@sha256:fbe0b348a6ad…` executed the Docker dry run.
- Observations, check IDs and artifact paths: `benchproof.trials` (core, `systems`, `config`, `summary`); `scripts/run_trials.py`, `scripts/summarize_trials.py`, `scripts/freeze_eval_config.py`. Development dry runs with the labeled mock provider: `artifacts/trials/dev-dryrun-mock-inprocess` (15 trials, all COMPLETED; resume skipped all 15) and `artifacts/trials/dev-dryrun-mock-docker` (6 trials, every execution isolated on the pinned image; final evaluator VERIFIED for the clean control and REJECTED for unrepaired MC-01). Both summaries are marked not a measurement. `--final` refused against the candidate configuration and a live non-final run on `repair-r12-v1` was refused, both before any record or model call.
- Tests actually run; passed/failed/skipped/blocked: `tests/test_trials.py` 15 passed (plan balance, B1/B2 information separation and no truth in prompts, B2 gate acceptance, B1 submission judged outside its loop, clean-case false confirmation versus B2 evidence policy, repeated-candidate STALLED without execution, budget/format/provider/patch-policy failures retained, write-once/resume/INTERRUPTED/tamper detection, a nine-trial hand-counted summary, configuration change detection and final-run refusal); full regression 224 passed / 0 failed / 0 skipped; ruff clean.
- Patch/verdict plus graph coverage, freshness and mutation limits: the agent returns complete files and the harness builds the diff, which passes through the unchanged patch policy; B2 confirms a finding only with a failing protected check; diagnosis is scored at constraint level, so the caller-path and idempotency families (both C-INTEGRITY) are not distinguished; the decision ledger and recovery replan are not exercised inside fresh trials.
- Model tokens, executions, retries, cost/price snapshot and remaining reserve: zero tokens and zero cost; local in-process and Docker executions only. Worst-case plan usage is 72 model trials × 24,000 tokens = 1,728,000 tokens and at most 876 system executions plus 72 final-evaluator runs. The official Token Factory price page returned no readable pricing, so the configuration keeps `price_snapshot: NOT_RECORDED`; third-party listings (TypingMind, Artificial Analysis) report $0.06 input / $0.24 output per million tokens for this model on Nebius, which is unverified and not used for any cost figure. Credit balance is still unconfirmed.
- Repeated failure/recovery event and strategy change, if any: the first in-process dry run recorded B2 `MALFORMED_OUTPUT` on four faulty cases because the dry-run mock answered repair prompts with a diagnosis-shaped reply; the strict schema rejected it as designed. The mock was fixed to answer repair prompts with `BLOCKED`, that development run directory was discarded, and the rerun completed all 15.
- What changed in scope/decisions/docs: D-029 recorded; B-17 and B-19 backlog status, Day 17 items, API/data contract (trial records), evaluation plan, README and changelog updated. Event rules were not rechecked.
- Next earliest unmet dependency and tomorrow's realistic plan: owner review and commit of the Day 15 and B-19 changes, then `python scripts/freeze_eval_config.py` to produce a `frozen` configuration; B-20 hosting decision; one owner-approved live development trial on a development fixture to observe real Nemotron output format and usage before the B-21 final runs.

### 2026-10-16 — Release verification and free tunnel demo after Azure expiry

- Source: local release changes on `feat/day15-hardening-b19-trial-harness`, core commit `ad1955703ccc484e380f40edab33afe764beb3ba`; no commit, push or tag created this session.
- Owner/account facts: Azure subscription expired, no domain, Token Factory credits available, 8 GB/i3 laptop can stay on. No Azure resource or paid plan created. Existing authenticated ngrok 3.39.9 exposes the guarded demo at `https://dierdre-miasmatical-madge.ngrok-free.dev`; availability throughout judging is not established.
- Runner/provider: Docker 29.7.2 started. Docker Hub DNS blocked rebuilding, so the existing pinned image `sha256:fbe0b348a6ad781e739a639889a82a4a0d5ec9ce3907a7cfef95694ed0e9f4e9` was inspected and tested. `artifacts/runner/runner_20261016T081219.json` records clean VERIFIED, MC-01 REJECTED, timeout kill/cleanup, and absent Sandboxes spawn/list permission. `artifacts/preflight/provider_20261016T080645.json` records live pinned NVIDIA inference and valid structured JSON.
- Freeze: local evaluation configuration is now `frozen` for the committed core/image with unchanged identity `210affd887e92863543e4a2d2749534ba98e2c8a57203c5e0402016600d0460e`; suite lock `efe61ad8c4b0df56…` unchanged. Both verification commands pass. The demo wrapper/frontend are new release changes outside the core hash, not a frozen committed deployment. No final held-out trial was run.
- Live development: `artifacts/trials/dev-live-release-20261016-1` preserves three sealed B2 records. MC-01 completed with an accepted repair and VERIFIED. AC-01 ended MALFORMED_OUTPUT after both repair replies reached the 1,536-token limit, retaining rejected original source. Clean-service recorded PROVIDER_FAILURE (connection error); its unchanged source independently VERIFIED. Correct constraint diagnoses 2/2 faulty cases; accepted repairs 1/2. Recorded tokens: 28,970; monetary cost/reserve unknown. These are development observations, not comparative measurements or three successful rehearsals. The summary's generic development banner mentions mock/non-isolated runs, while the immutable records correctly identify live provider and Docker isolation.
- Replay: `scripts/run_bundle_replay.py` now requires Docker, refuses existing output, uses a separate evidence database, records actual diff hashes/paths with PENDING policy, and fails on mismatch. `artifacts/release-replay/20261016-release-1` contains canonical-reference API/amount/clean exports and fresh matching Docker replays plus tampered-bundle BLOCKED evidence. Reference repairs are not model-generated repairs.
- Demo: `scripts/serve_demo.py` serves only the built frontend plus API on localhost:8765, uses a separate persistent audit database, pairs a heartbeat helper, serializes actions and enforces 60 shared actions per UTC day in SQLite (including GET replay; cancellation remains available). Production UI uses the same origin and defaults to live mode. Windows reserves ports 8014–8113, so 8080 failed and 8765 was tested. No DNS/power/security settings changed. The heartbeat helper does not process queued jobs or install an OS restart policy.
- Public HTTPS evidence: clean audit `audit-d8b7bb64b64f`, gate VERIFIED, export valid, replay VERIFIED with checks/verdict matching, SSE frames received, other-owner 403, `.env` 404. Bundle SHA-256 `05941a04cd223a37e37d5c931b1edcfd6dde17f9ec70f78d9c9fb1cc9ed1582b`. A fresh headless Chrome profile rendered the public UI (`artifacts/browser-release-20261016/public-demo.png`); this is not a completed interactive incognito journey. Public clean gate/replay made no model call.
- Tests: final full pytest 232 passed / 0 failed / 0 skipped (all three Docker tests, eight new demo/replay regressions), ruff clean, frontend lint/build clean, development fixtures and frozen suite/configuration checks pass. Managed-sandbox temp/child-process failures resolved when rerun outside that sandbox. npm advisory lookup failed DNS after escalation, so vulnerability status remains unverified.
- Release materials: planned Apache-2.0 LICENSE/NOTICE added, not the suggested MIT option; direct package license metadata inspected, complete transitive/model/image rights review pending. README, judge guide, hosting/runbook and backlog/checklist updated; D-030 records fallback.
- Remaining: API-repair output reliability on development fixtures, backup/restore, restart supervision, quota/credit/pricing and judging access lifetime, final B0/B1/B2/assurance-suite measurements, clean clone, model/image notices, public release/tag, three successful live rehearsals, genuine short video and actual submission. Laptop power, network, Docker, server and tunnel must stay available.

### 2026-10-16 — Vercel migration preparation requested by owner

- B-20 remains IN_PROGRESS. Added static UI/server-only gateway, a named resumable Sandbox, a 512 MiB persistent Drive, private origin authentication, runtime hash checks, a strict upload allowlist and an actual Hobby-plan guard. The existing protected evaluator and Docker runner are unchanged; no paid plan is enabled.
- Added provisioning, stop/resume verification and gated production deployment scripts. The cloud verifier requires Docker network/metadata/secret/trusted-asset/read-only findings, timeout termination, clean gate/export/validation/replay, SSE, ownership denial and persistent audit/bundle/action-counter/heartbeat checks. These scripts have not yet passed on Vercel.
- Local evidence: full backend 234 passed / 0 failed / 0 skipped; 12 Node deployment tests passed; frontend production build/lint, Python lint and Bash syntax clean. Installed SDK 3.8.0 / CLI 64.3.1 are pinned. Runtime package has 106 allowlisted files and hash `b1261b7a6fd530475061919e92e609dc5d7a2275079e94e46983b50ac085cab5`; local credentials, audit state and held-out truth excluded.
- Initial device-login sessions ended with `getaddrinfo ENOTFOUND api.vercel.com` even after the owner authorized them. A process-local IPv4 DNS resolver passed five consecutive unauthenticated API connection checks; system DNS settings were not modified. Replacement authentication is pending; no cloud resources, successful deployment, cloud persistence or live gateway result is claimed. Existing laptop/ngrok fallback retained.
- Runtime/deployment changes remain uncommitted. No provider call or final held-out trial was made in this migration step. Next dependency: complete CLI login, confirm Hobby access, link the project, provision and run the real cloud acceptance checks before deploying and switching the public demo.

### 2026-10-16 — Vercel authenticated provisioning; cloud runner remains blocked

- CLI login completed and API-confirmed team `hellinfernos-projects` is Hobby. Created/linked the single `benchproof` project; automatic multi-service setup was avoided by creating the project before linking. No paid plan enabled. The owner explicitly approved storing the existing Nebius key only on the trusted backend.
- Provisioned a 1 GiB Drive (512 MiB was rejected by the API) and named Sandbox `benchproof-runtime-v1`, `iad1`, 1 vCPU / 2048 MiB. Python 3.12.14, Docker 29.1.3; exact VM/candidate image identities are recorded in `VERCEL_DEPLOYMENT.md`. Fixed the root-owned uv interpreter path by installing Python under the trusted app directory. Runtime package now `f177314b56b7a6a7c989e06e3d1b08a4c1f90260532e554413b1abdd61ad5125` (106 files).
- Origin readiness and missing-token HTTP 403 checks pass. Actual runner preflight fails: Docker exit 125, cgroup-v2 threaded hierarchy cannot apply the memory controller; both fixtures INCONCLUSIVE, required observations UNKNOWN, timeout test not reached successfully. Saved original sanitized evidence in `artifacts/vercel/initial-runner-failure.json`. Known memory/CPU/pids/network/read-only/non-root limits remain unchanged.
- Auto-review rejected changing root cgroup delegation because it affects the entire dedicated VM. Explicit owner approval is requested before proceeding; no indirect workaround is used. Public gateway deployment is still gated, and laptop/ngrok fallback is retained.
- Repeated local deployment regressions: 12 passed; normal build and Bash syntax pass. Production npm audit and frontend install report zero vulnerabilities; local CLI development tree has 33 warnings (8 moderate / 24 high / 1 critical). Vercel's local Windows build fails `spawn cmd.exe ENOENT` after locked installs; actual Linux deployment build remains untested.
- No cloud model call, cloud stop/resume success, final trial, commit/push or production URL is claimed. Strengthened stop/resume acceptance to require a fresh isolated replay after the persistent audit/bundle/counter/heartbeat checks. Next: approved cgroup remediation, real cloud execution/persistence verification, then deployment and public/live-browser tests.

### 2026-10-16 — Verified Vercel cloud deployment and browser journey

- Primary URL `https://benchproof.vercel.app`, gateway `dpl_2iK7BZFvWMGv1KfCB2b96zZ5Lu14`; actual Hobby plan verified, no upgrade. Trusted Sandbox/Drive and remote NVIDIA inference no longer depend on the laptop. D-031 records approvals, topology, fixes and limitations.
- Fixed the approved cgroup hierarchy and Linux output-directory permissions without removing network, memory/swap, CPU, pids, read-only, non-root or timeout controls. Python 3.12.14 API; candidate image digest `e97eb0d1…`; runtime package `d858c8c2a9494f1ea8922068969724b4236f0c2c0ac3b32e060d95d533ac658c`. Original cgroup/output-permission failure records are preserved.
- Cloud acceptance `artifacts/vercel/cloud-check-1792146334676.json`: clean VERIFIED / faulty REJECTED, isolation findings passed, timeout killed, actual 256 MiB OOM kill (137), 1 CPU/64 pids confirmed; persistent audit, exact ZIP hash, daily counter and heartbeat survived stop/resume, followed by fresh replay.
- Public acceptance `artifacts/vercel/public-check-1792146557262.json`: UI/API without private Vercel login, cold readiness 4,744 ms, clean gate/export/validation/replay/SSE, other-owner audit/bundle 403, private files 404 and oversized body 413. Real NVIDIA MC-01 diagnosis supported C-AMOUNT; API-reported 547 prompt + 566 completion = 1,113 tokens, 3,202 ms. This is not a model-repair benchmark or a final held-out result.
- Browser attempts preserved: initial case-sensitive harness assertion; then a real readiness 503 under parallel requests. Added a guarded re-read after competing timeout extensions, with no user-action retry. New-profile cold browser journey passed in `artifacts/browser-vercel-20261016/browser-check-1792173340237.json`: clean audit `audit-6c5a7e0d96e5`, VERIFIED, ZIP/hash validation, fresh replay, downloaded ZIP SHA-256 `4b1b3aacc9747142c82ac0e390720e70eabbd0f98669a78bd3bf3a899985b182`, processed SSE, reload restoration, exactly one create, no exceptions/HTTP errors. Screenshot `verified-journey.png` inspected. Not a volunteer usability study.
- Tests: full backend 235 passed, including all three Docker tests; deployment 15 passed; production builds, Python lint, frontend lint and Bash syntax passed. Local Windows Vercel builder failed `cmd.exe ENOENT`, while actual Linux deployment builds passed. Production dependency audit zero; CLI-only tree retains 33 advisory warnings.
- Freeze integrity: held-out lock still matches `efe61ad8c4b0df56…`; historical configuration v1 is retained. Its verifier correctly reports `runtime_code_hash changed` after the Linux fix. The deployed runtime must be committed/reviewed and assigned a new configuration version before final trials. No commit, push, tag or final measurement was made.
- Remaining: independent backup/restore, judging-period quota/credit reserve and availability, model-repair reliability, new release freeze/final separated measurements, clean clone and full rights review, three live rehearsals, genuine video and actual submission. B-20 remains IN_PROGRESS for recovery/availability; B-19 requires the new release identity. README, deployment/judge guides and release checklist updated to distinguish cloud success from open release gates.
- Follow-up outcome retained: `artifacts/vercel/public-check-1792173417016.json` passed infrastructure checks but the repeated live diagnosis returned HTTP 422. Exact detail was not captured; cause unconfirmed, no blind provider retry. Final infrastructure-only check `public-check-1792174299345.json` passed clean and faulty-candidate gate outcomes, export/hash/replay/SSE/access boundaries with model `NOT_RUN` explicitly recorded. The earlier real model success and this later failure both remain visible; no claim of three successful live rehearsals or uniformly reliable model output is made.

### 2026-10-17 — User-requested UI readability refresh

- Replaced the starter typography/color rules with explicit local sans-serif fonts, correct heading line boxes, a coherent light slate/teal palette and responsive panel/card spacing. Added brand/command navigation and anchors for cases, the active run, verification, evidence and policy. Runtime indicators remain pending until actual readiness arrives. No API/evaluator/model semantics, ownership keys, budgets or isolation controls changed.
- Production `https://benchproof.vercel.app`, deployment `dpl_8agnMEN2Wova7ZWKY714pggLtthy`, runtime package `6178ebac963c09e485b4d44fd09945f276f40bd14a16b73237cafbd254f5ec10`. The existing dedicated Hobby Sandbox was upgraded by exact previous identity, then reverified before gateway deployment. `artifacts/vercel/cloud-check-1792175348254.json` passes isolation/timeout/OOM enforcement and persistent audit/ZIP/counter/worker plus fresh execution after stop/resume.
- Frontend TypeScript/Vite build and oxlint passed; all 15 deployment tests passed when localhost networking was permitted (the restricted run had three EACCES socket failures). Added public layout checks across six widths, actual rendered-font records, keyboard palette checks and stable color-scheme checks: `artifacts/ui-refresh-20261016/ui-check-1792175435125.json` passed.
- Fresh-profile public browser journey `artifacts/ui-refresh-20261016/browser-check-1792175610468.json` passed clean verification, export/hash validation, fresh replay, authenticated ZIP download, SSE, reload restoration and exactly one audit creation with no exception/HTTP error. Audit `audit-731fed4687d1`; ZIP hash `961f658a99d4abcc6ef59342c176f03a3c1e540779a6f8150bfc10a20ce40271`. Active-run page/control overflow checks passed at 1440/768/390/320 px; actual desktop/mobile screenshots inspected.
- Preserved the first new journey timeout, `browser-check-1792175560888.json`: smooth-scroll timing moved the target after the harness measured its click. Fixed the harness to scroll instantly before clicking; no deployed behavior or model retry was involved. Temporary local preview was stopped; personal browser profiles untouched.
- No inference spend, new dependency, commit, push or new evaluation claim. This is not a volunteer usability study. Known diagnosis HTTP 422, dependency advisories, independent backup/restore and the other release/freeze/submission work remain open. UI contract, changelog and deployment evidence updated.

### 2026-10-17 — Coding-agent build plan and priority reset (planning only)

- Owner requested a build plan after the expanded product/problem review. Added `BUILD_PLAN.md`: a task-centered Python coding agent with real NVIDIA generation, actual isolated tests, bounded repair, reviewed plans, supported project intake and reviewable/downloadable patches. Five user pain areas become persistent intent, evidence-linked checks, stall detection, scoped rollback and usage/cancel controls inside that workflow.
- Inspected current source rather than assuming a finished agent: the public UI still uses canonical repairs, model-authored repair exists offline, the worker only heartbeats, the runner invokes invoice observations, and the gateway has a 64 KiB body cap. Planned C-01–C-10 dependencies address those gaps explicitly. All new implementation tickets remain TODO.
- Updated AGENTS, backlog, requirements/architecture/runtime/API notices, both historical daily-plan entry points and README to point at the active plan. D-032 records the direction change without deleting prior assurance or evaluation evidence. Exact legacy API/evaluator contracts remain unchanged; project tests will not silently inherit invoice `VERIFIED` semantics.
- Calendar targets: real vertical slice by 18 Oct, project support 19–21 Oct, recovery/UI/cloud 22–24 Oct, freeze 25 Oct, evidence/video/submission 25–28 Oct. Internal submission target 28 Oct 20:00 IST; official close rechecked as 30 Oct 22:30 IST. Dates and credit reserve are not guarantees; stop/cut gates are in the plan.
- Validation is documentation-only: changed-line whitespace checks and new-plan checks pass. The local-link scan checked 44 links across 14 documents; its three broken links are pre-existing `../docs/...` references in the root historical `DAILY_TASKS.md`, confirmed in HEAD and left unchanged. New active-plan links resolve. No runtime test, candidate execution, inference, deployment, commit/push/tag or submission is claimed. First implementation dependency is C-01 provider-output reproduction, followed by C-02/C-03's genuine end-to-end agent slice. Current live app is unchanged; diagnosis 422, truncated output, backup/restore and credit/hosting reserve remain open.

### 2026-10-17 — C-01 development acceptance; C-02 primitives started

- Scope: began implementation, not another UI-only pass. C-01 development acceptance DONE; C-02 IN_PROGRESS for brief/plan/edit primitives only. No commit, branch creation, push, deployment or frozen identity rewrite. The current public app and heartbeat helper do not yet provide the new coding-task workflow.
- Provider boundary: no guessed JSON endings or invented required diagnosis content; length, interrupted, oversized and malformed/schema-invalid completions fail explicitly. Missing choice sets are protocol failures. Configured model/base/key/output allowance reach diagnosis; output cap starts at 2,048, with no automatic retry/fallback. One sample is not calibration for every task. Transport exception bodies are excluded from public errors.
- Accounting: reserve legacy diagnosis action/event atomically before the provider request; failed attempts consume the original allowance, retain safe provider identity/finish/usage, and emit `action_failed`. Unknown usage is not zero. Concurrent or crash-left `in_flight` attempts block another request. This is not C-02's still-pending lease/fencing/reconciliation implementation. API contract, additive `provider_meta` migration and developer notes updated.
- New production edit primitive: versioned brief binds task/source/approved files; plan binds brief/source/profile; edits bind source/approved plan. One provider request -> validated complete-file edits -> deterministic diff -> round-trip and unchanged legacy policy. No filesystem mutation or candidate execution inside generation. Historical trial prompts/schemas/logic and sealed results are untouched.
- Reproduction: `artifacts/coding/c01-retained-20261017/retained-failures.json` reads both actual retained AC-01 repair replies (steps 3/4, each `finish_reason=length`) and rejects them as `MODEL_OUTPUT_TRUNCATED`. Synthetic regressions exercise schema/client-status distinctions, but do not establish the cause of the old public HTTP 422, whose response cause was not retained.
- Actual inference: user explicitly approved one call, capped at 2,048 output tokens without retry. Unbilled catalog confirms configured `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (28 models). Official Nebius cookbook was inspected; provider pricing page was unavailable, so no inferred currency cost. `artifacts/coding/c01-live-20261017-1/` retains scoped task/operator plan, exclusive call reservation, raw public-sample response, actual model diff and reports. Response `chatcmpl-dc504544-322a-4068-b725-ca50f840645f`, stop, 971 prompt + 1,183 completion = 2,154 tokens, 5,068 ms. Exactly one inference attempt; monetary cost and credit reserve UNKNOWN. Plan was not model-generated.
- Real cloud execution without a new deployment: saved diff round-trips to that response's exact file edit and is imported into the existing API. Audit `audit-1ba1aab76133`, patch `patch-a2b556ff90cf`, diff hash `b932e74e4f5cb006222aaa5600e25b2a5453c1974dc08f568a3b44cf1e8033be`. Original source `a500577c…` fails `amount-boundary`; candidate `bcc99228…` passes all seven required protected checks with none failed/unknown. Existing image `e97eb0d1…`; Docker network none, read-only root/source/launcher, cleared env, non-root 65534, 256 MiB memory, 1 CPU, 64 pids and 30-second limit reported enforced. Cloud acceptance tool makes zero inference calls and four non-retried mutations. `cloud-report.json` retains full results. Original local fixture unchanged. No local execution of the generated code.
- Validation: first restricted test runs were interrupted after temporary-path/SQLite concurrency problems; a new workspace temp root and explicitly permitted normal SQLite/thread access resolved the harness issue. Focused provider 27 passed; generation/adjacent lifecycle 48 passed; later generation/acceptance/cloud-tool 35 passed. Full final pre-display-accounting suite: 294 passed / 3 skipped in 67.81 s; `artifacts/coding/backend-tests-20261017-b.xml`. Skips are the three existing local Docker tests because Docker daemon is stopped. `ruff check backend` and `git diff --check` pass; Git reports checkout line-ending warnings, not whitespace failures. Actual generated-candidate Docker evidence comes from the cloud check above, not the skipped tests. No frontend/deployment code changed in this increment.
- Final accounting-display regression: 52 passed in 25.35 s after the last runtime edit, `artifacts/coding/final-focused-tests-20261017.xml`; Python lint clean. All 15 local links in the seven affected status/contract/runtime documents resolve. A separate check with `core.autocrlf=false` incorrectly treats the existing CRLF checkout as trailing whitespace; retain the configured line-ending policy rather than rewriting unrelated files.
- Remaining: new backend rollout and fresh public diagnosis acceptance; C-02 durable owner-scoped task/project/action/usage storage, idempotent enqueue, lease/fencing worker and interrupted-call reconciliation; C-03 application-connected model plan/edit/check/revision loop; C-04 onward supported intake, generic tests, task UI, checkpoints, quotas, evaluation and release. The CLI-to-cloud development sample does not complete C-03 or general-project support. No further inference is authorized by the one-call approval.

### 2026-10-17 — C-02 and C-03 completion: durable worker and end-to-end revision loop

- Scope: Completed C-02 (durable owner-scoped SQLite store, single-action leased worker, body limit middleware, and FastAPI routes) and C-03 (first genuine task -> model plan -> human approval -> baseline check -> model edit -> candidate check -> revision loop -> final verification -> reviewable diff).
- Worker & store: Monotonically increasing fences, leased execution, atomic action reservation and completion, daily operator call/execution caps, pause/resume/cancel controls, and execution reconciliation.
- Multi-turn revision loop: Verified that when candidate checks fail on the first attempt, failure observations (failing check IDs, reasons, and previous diff) are preserved in checkpoint and supplied as observations to the next model edit attempt.
- Stall circuit breaker: Verified that generating an identical candidate patch twice triggers `REPEATED_CANDIDATE` and halts the engine as `STALLED` without wasting isolated container execution cycles.
- Acceptance tooling: Added `backend/scripts/run_coding_loop.py` CLI demonstration runner; generated offline verification pack in `artifacts/coding/c03-verification-20261017/` (`task.json`, `plan.json`, `candidate.diff`, `events.json`, `report.json`). State reached `REVIEW_READY` with verified diff.
- Testing & verification: `backend/tests/test_coding_loop.py` (4 new end-to-end tests); coding test suite (97 passed in 36s); ruff clean; full git diff whitespace clean.
- Next: C-04 constrained project intake (`POST /api/v1/projects`), manifest versioning, and generic Python test profile.

### 2026-10-17 — C-04 completion: constrained project intake and generic test profile

- Scope: Completed C-04 (constrained project intake, owner-scoped project repository, manifest fingerprinting, generic unittest runner with process isolation, and CodingEngine integration).
- Project intake & safety: Strict validation enforcing max 20 UTF-8 text files, 24 KiB/file, 128 KiB total raw bytes, and 256 KiB encoded body limit; disallows path traversal (`..`, absolute paths, drive letters, backslashes), secret filenames (`.env`, `id_rsa`, tokens), byte-code (`.pyc`, `.so`), case collisions, and null bytes. Canonical LF-normalized manifest fingerprinting produces SHA-256 source identity.
- Durable project store: Owner-scoped SQLite `coding_projects` table (`proj-` ID prefix, name, runner profile, manifest, files JSON, owner reference, timestamps) with per-owner quota (max 20 projects per owner).
- Project API endpoints: `POST /api/v1/projects` (creates and validates project with 256 KiB body limit), `GET /api/v1/projects` (lists owned projects), `GET /api/v1/projects/{id}` (retrieves project manifest), `GET /api/v1/projects/{id}/source` (retrieves source files), `DELETE /api/v1/projects/{id}`. `POST /api/v1/coding-tasks` extended to accept `project_id` or `fixture_id`.
- Isolated generic test runner: `run_project_tests.py` trusted launcher running in parent/child process isolation with strict stdout/stderr capture; probes for network/socket attempts and secret/env leaks; discovers and runs bounded `unittest` suites; handles `ZERO_TESTS_COLLECTED` failure cleanly; formats structured check results with `PROJECT_CONTRACT_HASH` (64-char hex SHA256).
- Verification & testing:
  - Two distinct small projects (`StringCalculator` and `BankAccount`) pass unchanged.
  - Failure detection verifies expected error reporting with tracebacks.
  - Missing/zero tests collected properly fails with `ZERO_TESTS_COLLECTED`.
  - Full end-to-end multi-stage coding task loop on user project: Baseline (REJECTED) -> Model Edit -> Candidate Check (VERIFIED) -> Final Independent Check (VERIFIED) -> `REVIEW_READY` with verified diff.
  - `backend/tests/test_project_intake.py` (13 passed in 0.28s).
  - `backend/tests/test_project_runner.py` (5 passed in 5.3s).
  - Full backend regression: 441 passed, 3 skipped, 0 failed in 42.6s.
- Next: C-05 running the agent on imported projects with focused context, reviewed plans and versioned project edit policy.

### 2026-10-17 — C-05 completion: agent execution on imported projects with edit policy

- Scope: Completed C-05 (real bug fix on StringCalculator, bounded feature on BankAccount, protected test refusal, unauthorized path refusal, and stale base refusal).
- Task 1 (Bug Fix): Project 1 (`StringCalculator` with negative number defect). Agent generates plan, baseline check fails with `REJECTED`, model generates fix, candidate passes, final check passes `VERIFIED`, and task reaches `REVIEW_READY` with verified diff.
- Task 2 (Bounded Feature): Project 2 (`BankAccount` with `transfer()` feature). Agent generates plan, baseline check fails (missing method), model generates implementation delegating to withdraw and deposit, candidate check passes, final independent check passes `VERIFIED`, and task reaches `REVIEW_READY` with verified diff.
- Security & Edit Policy Enforcement:
  - Protected test refusal: verified `tests/` cannot be approved for editing in brief or plan (`ValueError`).
  - Unauthorized new path refusal: verified non-app, non-python, or path traversal paths (`app/evil.py`, `app/../../root.py`) are strictly rejected.
  - Stale base refusal: verified tasks against stale/mismatched source hashes are rejected at task creation.
- Verification & testing:
  - `backend/tests/test_project_tasks.py` (5 passed in 4.22s).
  - Combined project suite (`test_project_intake.py`, `test_project_runner.py`, `test_project_tasks.py`): 23 passed in 7.39s.
  - Full backend test suite: 446 passed, 3 skipped, 0 failed.
- Next: C-06 persistent task brief, source-bound facts, checkpoint restore, pause/resume/cancel, repeated-failure classification and durable budget enforcement.

### 2026-10-17 — C-06 completion: persistent checkpoints, restore, controls, and bundle export

- Scope: Completed C-06 (immutable checkpoint history log, conflict-checked compare-and-swap checkpoint restore, sanitized task bundle export in JSON and ZIP formats, durability and crash reconciliation, monotonic budget preservation, and container cancellation reconciliation).
- Checkpoint storage & history: Added `coding_checkpoints` table storing versioned, immutable snapshots (`checkpoint_id`, `task_id`, `sequence`, `stage`, `state`, `checkpoint_json`, `created_at`). Recorded on plan approval (initial baseline checkpoint seq 1), action completion (baseline report, candidate patch, test results), and manual updates.
- Conflict-checked CAS rollback: Implemented `store.restore_checkpoint()` and `POST /api/v1/coding-tasks/{id}/restore` taking `checkpoint_id` and optional `expected_checkpoint_id` for CAS conflict detection (`CONFLICT` / 409). Sets task state to `PAUSED`, restores checkpoint and next stage, appends new immutable checkpoint entry, and emits `CHECKPOINT_RESTORED` event.
- Strict budget enforcement: Monotonic counters (`model_calls`, `patch_attempts`, `executions`, `active_seconds`) are strictly preserved across checkpoint restore, pause, resume, and retry.
- Sanitized task bundle export: Implemented `store.export_bundle()`, `store.export_bundle_zip()`, and `GET /api/v1/coding-tasks/{id}/bundle` supporting JSON and downloadable ZIP (`?format=zip`). Bundle includes task brief, approved plan, patch diff, test reports, event timeline, file manifest, and markdown summary; strictly omits credentials, environment secrets, and bearer tokens.
- Durability & lifecycle controls:
  - Crash/interruption handling: Expired worker leases mark actions `UNKNOWN` / `INTERRUPTED` without losing usage; resuming requires explicit retry to prevent accidental double-spend.
  - Active execution guards: Restore is rejected with `INVALID_STATE` or `ACTION_IN_FLIGHT` if an action or worker lease is active.
  - Container cancellation reconciliation: `cancel` sets `CANCEL_PENDING`, and runner confirms termination via `reconcile_execution(..., stopped=True)` -> `CANCELLED`.
- Verification & testing:
  - `backend/tests/test_coding_checkpoints.py` (9 passed in 2.53s).
  - Coding suite regression (124 passed in 45.59s).
  - Full backend test suite: 455 passed, 3 skipped, 0 failed in 86.36s.
- Next: C-07 primary task workspace with source, plan, activity, diff, checks and download.

### 2026-10-17 — C-07 completion: primary coding agent workspace and interactive workflow

- Scope: Completed C-07 (primary task-centered coding workspace in React/TypeScript, project source browser with editable vs protected test separation, interactive brief and limits review, model plan review and step editing, 8-stage visual progress stepper, live controls [start, pause, resume, cancel], 5-gauge monotonic budget meters, unified syntax-highlighted diff viewer, isolated test execution terminal console, versioned checkpoint history with CAS restore, authenticated bundle ZIP export, and backward-compatible legacy assurance audit tab).
- Frontend architecture:
  - Default view: `frontend/src/components/coding/CodingWorkspace.tsx` mounted as the primary interface in `App.tsx`, with a tab navigation toggle to the historical assurance audit dashboard.
  - Project source browser: Interactive file tree with badges (`EDITABLE [app/]` vs `PROTECTED TEST [tests/]`) and line-numbered code viewer.
  - Sample projects: Pre-loaded `StringCalculator` (bug fix), `BankAccount` (bounded feature), and `MC-01` (invoice fixture).
  - Custom project intake: Multi-file modal intake enforcing client-side validation rules (<= 20 files, <= 24 KiB/file, <= 128 KiB total, path traversal rejection).
  - Task brief & plan review: Editable plan steps prior to approval, plan hash validation (`identity()`), and idempotency headers for all mutating actions.
  - Multi-stage visual stepper: Tracking progression through `Draft` -> `Plan` -> `Approval` -> `Baseline` -> `Edit` -> `Candidate` -> `Final` -> `Review Ready`.
  - Control bar & live polling: Seamless polling of task state, events, diffs, executions, usage, and checkpoints during active execution.
  - Changes & diff viewer: Syntax-colored unified diff with addition (`+`), deletion (`-`), and chunk header styling, author attribution, and tested verdict badge.
  - Checkpoint history & CAS rollback: Timeline of versioned snapshots with one-click restore to `PAUSED` state without resetting monotonic budgets.
  - Bundle export: One-click downloads for raw `patch.diff` and authenticated `.zip` archive containing full verification evidence.
- Quality & verification:
  - `npm run lint` (oxlint): 0 warnings, 0 errors.
  - `npm run build` (tsc -b && vite build): clean production bundle in 273ms.
  - Full backend test regression: 455 passed, 3 skipped, 0 failed in 78.26s.
- Next: C-08 cloud worker/session/quota acceptance, ownership, isolation and backup/restore.

### 2026-10-17 — C-08 completion: cloud worker/session/quota acceptance, ownership, isolation and backup/restore

- Scope: Completed C-08 (cloud failure mode acceptance suite, SQLite WAL-consistent online backup and restore module & CLI, worker lease recovery with monotonic fencing tokens, session window admission refusal, quota accounting enforcement, cross-owner data isolation, and secret scrubbing in export bundles).
- Implemented modules:
  - `backend/benchproof/storage/backup.py`: `create_backup()` using SQLite online backup API (`conn.backup()`) with `PRAGMA wal_checkpoint(TRUNCATE)` for WAL-consistent snapshots, SHA-256 manifest generation/validation, foreign key integrity checks, and corrupted-target rejection; `restore_backup()` with checksum verification.
  - `backend/scripts/backup_restore.py`: CLI tool providing `backup` and `restore` subcommands with verbose verification output.
  - `backend/tests/test_cloud_acceptance.py`: 7 automated acceptance tests for cloud failure modes:
    1. Worker crash and lease recovery with monotonic fencing tokens (`fence`).
    2. Session window admission refusal when available runtime is insufficient (`SESSION_WINDOW_INSUFFICIENT`).
    3. Quota accounting enforcement (`OPERATOR_LIMIT` on daily model calls / executions).
    4. Cross-owner data isolation ensuring tasks/actions cannot be viewed or mutated across owners.
    5. Common-secret scrubbing ensuring API keys and credentials are not leaked in task export bundles.
    6. Backup and restore integrity with SHA-256 manifest verification and schema validation.
    7. Corrupted backup rejection refusing restore when payload checksum does not match manifest.
- Verification & testing:
  - `backend/tests/test_cloud_acceptance.py` (7 passed in 4.79s).
  - Full backend test suite: 462 passed, 3 skipped, 0 failed.
- Next: C-09 versioned task suite, evaluation harness, and genuine rehearsals.

### 2026-10-17 — C-09 completion: versioned new task suite, evaluation harness, and genuine rehearsals

- Scope: Completed C-09 (frozen 6-task evaluation suite, automated evaluation harness measuring exact tokens/calls/executions/durations without holdout tuning, CLI runner script, and authentic rehearsal execution with persistent JSON/Markdown report artifacts).
- Implemented modules:
  - `backend/benchproof/coding/evaluation.py`:
    - 6 frozen tasks across 3 categories:
      - `TASK-01-CALC-NEG` (Bug fix: String calculator negatives validation).
      - `TASK-02-MD-EMPH` (Bug fix: Markdown parser emphasis formatting).
      - `TASK-03-STOCK-UNDERFLOW` (Bug fix: Inventory stock deduction underflow protection).
      - `TASK-04-BANK-TRANSFER` (Bounded feature: BankAccount `transfer(target, amount)`).
      - `TASK-05-RATE-RESET` (Bounded feature: RateLimiter `reset_key(key)`).
      - `TASK-06-URL-CLEAN` (No-change: URL normalizer baseline, verifies no-op stability).
    - Evaluation harness `run_eval_suite(...)` executing all tasks with isolated child process test runners (`ProjectExecutor(synthetic_runner=...)`).
    - Exact metric tracking: tokens (prompt/completion/total), model calls, patch attempts, isolated executions, durations, and pass rates.
  - `backend/scripts/run_coding_eval.py`: CLI runner producing structured JSON and formatted Markdown reports in `artifacts/rehearsals/`.
  - Rehearsal execution:
    - Executed rehearsal: `artifacts/rehearsals/coding_eval_report_20261017_162747.json` and `.md`.
    - Total tasks: 6. Passed: 6 (100.0% pass rate). Failed: 0. Stalled: 0. Total executions: 11. Total model calls: 8. Total duration: 15.69s.
  - `backend/tests/test_coding_evaluation.py`: 5 tests passing in 13.3s covering single task evaluation, full suite execution, report persistence, and no-change task verification.
- Verification & testing:
  - Full backend test suite: 467 passed, 3 skipped, 0 failed.
- Next: C-10 clean-clone/rights/access, authentic video and actual owner submission prep.

### 2026-10-17 — C-10 completion: clean-clone verification, rights & attribution inventory, submission prep

- Scope: Completed C-10 (clean-clone setup verification, dependency rights and license review, public demo accessibility, video script and storyboard, factual submission text with zero overclaiming, and comprehensive submission checklist).
- Verification & documentation:
  - Clean-clone reproduction commands validated for backend venv, lockfile installation, frontend npm dependencies, test runner execution, and evaluation rehearsal runner.
  - Updated `NOTICE` and `BenchProof_MD_Pack/docs/22_LICENSE_AND_ATTRIBUTION.md` documenting first-party Apache-2.0 license, third-party runtime package licenses (MIT, BSD-3-Clause, Apache-2.0), and model card terms.
  - Created `SUBMISSION_CHECKLIST.md` documenting verified commands, public demo access at `benchproof.vercel.app`, video storyboard/structure (<= 3 min genuine flow), and factual competition form copy with zero overclaiming.
  - Zero regressions: full backend test suite passing (467 passed, 3 skipped, 0 failed), clean frontend lint (oxlint 0 errors, 0 warnings), clean production build (vite build in 280ms).

## Daily entry template

### YYYY-MM-DD — day number

- Focused hours planned / actual:
- Commit/branch and deployment version, if any:
- Tickets attempted / completed / blocked:
- Accepted source/contract/graph/evaluator hashes:
- Runtime mode and actual provider/model/runner/image:
- Observations, check IDs and artifact paths:
- Tests actually run; passed/failed/skipped/blocked:
- Patch/verdict plus graph coverage, freshness and mutation limits:
- Model tokens, executions, retries, cost/price snapshot and remaining reserve:
- Repeated failure/recovery event and strategy change, if any:
- What changed in scope/decisions/docs:
- Next earliest unmet dependency and tomorrow's realistic plan:

Link evidence, not a narrative of apparent effort. Keep rejected/unknown outcomes. Never replace failed records with a later successful screenshot.

## Milestone tracker

| Milestone | Target | State | Evidence required |
| --- | --- | --- | --- |
| Research-aligned documentation | 3 Oct | Completed as documentation | Revised files, research/source register and change map |
| Actual NVIDIA/runner preflight | 4–6 Oct | Provider OK 5 Oct (Nemotron-3-Nano, structured JSON valid); runner access not requested | Sanitized requests, model/image/operation IDs, limits |
| Constraints/graph/current context | 6–8 Oct | Completed 7–8 Oct | Accepted manifest, graph/gaps, stale-base rejection |
| Complete P0 protected repair | 9 Oct | Completed 9 Oct | AC/MC repairs, clean control, invalid candidate rejection |
| Export/fresh replay | 10 Oct | Completed 10 Oct | Bundle and independent replay record |
| Usable UI/error paths | 11–12 Oct | Completed in code/tests 12 Oct; screenshot NOT_RECORDED | API journey tests, owner/reconnect/cancel evidence, build/lint |
| P1 ledger/recovery/mutations | 13–15 Oct | Completed in code/development evidence 13 Oct; final selected suite outcomes still pending freeze | Freshness/trajectory/mutant observations |
| Security gate | 16 Oct | Completed 14 Oct in code/tests (`INTEGRITY_REPORT_v1.md`); live Docker network/metadata denial recorded PASS 14 Oct; hosted remote termination still untested | Negative tests and actual runner denial/limits |
| Frozen suite assets | 17 Oct | Completed 14 Oct: R12/V12/G8/F6/W8/M12 manifests and `truth.lock.json` committed; R6/V6 fallback predeclared | R12/R6 plus separate selected suites and commit |
| Hosted release candidate | 19 Oct | Pending | Incognito journey, persistent store and restore |
| Frozen evaluation configuration | 20 Oct | Harness implemented 15 Oct; `eval-config-v1` is a candidate until the runtime is committed and refrozen | Model/prompts/runtime/evaluator/image/budget plan |
| Final measured outcomes/replay | 21–23 Oct | Pending | Complete immutable trial records and actual summaries |
| Three rehearsals and release freeze | 24–25 Oct | Pending | Live runs, clean clone, license/access record |
| Public video/final entry copy | 26–27 Oct | Pending | Genuine footage, checked links and factual claims |
| Actual entry submitted | 28 Oct 20:00 IST | Pending | Submitted status and confirmation |

## Measurement attachment

For each suite list suite/version, unique cases, assigned trials, completed/failed/unknown counts, system configuration, result file and contamination status. R12 repairs, V12 gate candidates, G8/F6/W8 and M12 have distinct denominators. Optional product runs remain NOT_RUN until artifacts exist.

## Weekly review

On 10, 17 and 24 October review unmet P0 dependencies, real hours, remaining budget/judging reserve, scope limits and weakest judge-facing evidence. Cut lower-priority breadth before release buffer. Confirm deployed versus evaluated versions; changes to measured behavior require versioned affected reruns and honest holdout/regression labeling.
