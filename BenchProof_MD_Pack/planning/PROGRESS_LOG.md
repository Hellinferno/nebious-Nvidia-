# Progress and evidence log

## Current status — 3 October 2026

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
| Usable UI/error paths | 11–12 Oct | Pending | Real API journey, owner/reconnect/cancel evidence |
| P1 ledger/recovery/mutations | 13–15 Oct | Pending | Freshness/trajectory/mutant observations |
| Security gate | 16 Oct | Pending | Negative tests and actual runner denial/limits |
| Frozen suite assets | 17 Oct | Pending | R12/R6 plus separate selected suites and commit |
| Hosted release candidate | 19 Oct | Pending | Incognito journey, persistent store and restore |
| Frozen evaluation configuration | 20 Oct | Pending | Model/prompts/runtime/evaluator/image/budget plan |
| Final measured outcomes/replay | 21–23 Oct | Pending | Complete immutable trial records and actual summaries |
| Three rehearsals and release freeze | 24–25 Oct | Pending | Live runs, clean clone, license/access record |
| Public video/final entry copy | 26–27 Oct | Pending | Genuine footage, checked links and factual claims |
| Actual entry submitted | 28 Oct 20:00 IST | Pending | Submitted status and confirmation |

## Measurement attachment

For each suite list suite/version, unique cases, assigned trials, completed/failed/unknown counts, system configuration, result file and contamination status. R12 repairs, V12 gate candidates, G8/F6/W8 and M12 have distinct denominators. Optional product runs remain NOT_RUN until artifacts exist.

## Weekly review

On 10, 17 and 24 October review unmet P0 dependencies, real hours, remaining budget/judging reserve, scope limits and weakest judge-facing evidence. Cut lower-priority breadth before release buffer. Confirm deployed versus evaluated versions; changes to measured behavior require versioned affected reruns and honest holdout/regression labeling.
