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
| Constraints/graph/current context | 6–8 Oct | Pending | Accepted manifest, graph/gaps, stale-base rejection |
| Complete P0 protected repair | 9 Oct | Pending | AC/MC repairs, clean control, invalid candidate rejection |
| Export/fresh replay | 10 Oct | Pending | Bundle and independent replay record |
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
