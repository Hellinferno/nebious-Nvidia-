# Changelog

## 2026-10-17 — First coding-agent implementation increment

- Implemented shared fail-closed completion validation and distinct transport/protocol/truncation/incomplete/size/schema failures. Removed diagnosis JSON-ending guesses and invented required fields. The configured model/output allowance is honored; no automatic paid/format retry or mock substitution. Safe provider errors exclude raw transport exception text.
- Added atomic pre-call legacy diagnosis reservations, failed-attempt accounting, retained known/UNKNOWN usage and allowlisted provider metadata. Concurrent or crash-left in-flight requests cannot silently start another diagnosis. Additive storage migration and API failure/status documentation accompany the change; this is not the future fenced task worker.
- Started C-02 with source/task-bound brief/plan/edit contracts and a production one-call edit generator, separate from frozen trial logic. It produces a small deterministic policy-checked diff without applying/executing source. Durable task/project/action/usage persistence, endpoints and worker remain pending.
- One approved NVIDIA call generated a genuine MC-01 repair: 2,154 recorded tokens, 5,068 ms. The existing cloud gate rejected the original, then accepted the exact saved model diff with all seven protected checks passing in the resource-limited Docker runner. No second inference, local candidate execution, canned replacement, deployment or Git publication. Evidence `artifacts/coding/c01-live-20261017-1/`; original public 422 cause remains unconfirmed.
- Added opt-in one-call and no-inference cloud acceptance tools with exclusive reservations, artifact round-trip checks and no mutation retry. Both retained AC-01 truncations reproduce the new rejection contract. Full backend run: 294 passed / 3 local-Docker skips; Python lint clean. Final focused regression after accounting-display changes is recorded in progress. C-03's app-connected loop and all general-project/UI/release gates remain open.

## 2026-10-17 — Task-centered coding-agent build plan

- Added `BUILD_PLAN.md` with an implementation-aware gap analysis, narrow Python project scope, real agent/worker/test-runner architecture, versioned contract proposals, C-01–C-10 acceptance gates and a dated release plan. Prioritize actual model-written code and executed tests before more dashboard features.
- Made the new plan discoverable from AGENTS, backlog, requirements, architecture, runtime, API-contract notices, daily-plan entry points and README; D-032 preserves the rationale. Historical fixture contracts, frozen evaluation identities and results are not overwritten or claimed as evidence for the future project workflow.
- Planning only: new capabilities remain TODO, live deployment unchanged, no inference spend, implementation tests, paid resource, Git publication or submission. Timelines, credits and judging-period availability remain conditional.

## 2026-10-17 — Readable assurance workspace

- Replaced the cramped starter typography and automatic dark palette with explicit local sans-serif fonts, independent heading line heights, neutral panels, restrained teal actions, a compact brand/command bar and section navigation.
- Reworked case-card spacing, runtime status, result tables, evidence panels and phone layouts without changing endpoints, acceptance policy, saved owner/audit keys or model behavior. Pending runtime status is no longer shown as an offline/mock result before readiness arrives.
- Added six-width fresh-profile layout/font/keyboard checks and four-width active-audit checks to the browser journey. Frontend production build/lint and 15 deployment tests pass; sandboxed loopback test failures were rerun successfully with networking permitted. No inference call is required for this UI verification. Known live diagnosis HTTP 422 remains unresolved.
- Deployed at the same public URL after repeated cloud isolation/persistence checks. Public six-width layout checks and clean verification/export/hash/replay/download/SSE/reload journey pass with no duplicate create or browser error. Preserved the smooth-scroll click-timing harness failure and corrected the test helper; desktop/mobile screenshots inspected. Current package `6178ebac…`, deployment `dpl_8agnMEN2Wova7ZWKY714pggLtthy`; detailed artifact IDs in `VERCEL_DEPLOYMENT.md`.

## 2026-10-16 — Vercel cloud deployment verified

- Published `https://benchproof.vercel.app` on the verified Hobby plan, with server-only gateway, persistent trusted Sandbox/Drive, private origin and unchanged candidate isolation limits. Owner approved trusted-backend key storage and dedicated VM cgroup changes; no paid upgrade.
- Fixed uv interpreter permissions, cgroup memory delegation and private snapshot output permissions for the non-root Linux runner. Cloud preflight now passes isolation/timeout and actual OOM enforcement; persisted audit, ZIP, counters and heartbeat survive stop/resume with fresh replay. Original failures retained.
- Public clean gate/export/validation/replay/SSE and access negatives pass; real NVIDIA diagnosis supports the amount fault. Fixed concurrent timeout-extension failure without retrying mutations or accepting insufficient job windows. Fresh unauthenticated Chrome cold-start/create/verify/export/validate/replay/download/reload passes with no duplicate audit or browser error.
- Backend 235 passed; deployment 15 passed; lint/build/syntax clean, including actual Linux production builds. Production audit reports zero vulnerabilities; CLI development tree retains 33 warnings. Historical evaluation v1 intentionally fails current-runtime identity matching after the compatibility fix; a new reviewed release configuration/final trials remain pending. No commit/push/tag, backup/restore or final submission is claimed.
- Preserved a later live diagnosis HTTP 422 (cause not captured/confirmed), despite an earlier meaningful live diagnosis success. No blind paid retry. Final infrastructure-only check passes clean verification, faulty-candidate rejection, export/replay/SSE/access controls and explicitly labels inference NOT_RUN. Model reliability remains open.

## 2026-10-16 — Vercel migration preparation (not deployed)

- Added a same-origin Vercel gateway and named Sandbox/Drive provisioning with unchanged candidate Docker isolation, a private origin header, allowlisted runtime packaging and paid-plan refusal. Cloud stop/resume verification must pass before deployment is allowed; known missing state cannot be silently recreated by a public request.
- Pinned Sandbox SDK 3.8.0 and CLI 64.3.1. Local checks: 234 backend tests, 12 deployment tests, frontend production build/lint, Python lint and Bash syntax passed. No cloud acceptance result is claimed.
- Initial browser-authorized CLI sessions failed DNS resolution; a process-local workaround passed five API connection checks and a replacement login is pending. The existing ngrok demo remains the fallback. Added `VERCEL_DEPLOYMENT.md` with actual status, operations and unchecked cloud acceptance requirements.
- Follow-up: login succeeded and the actual Hobby plan was verified. Created/linked the single `benchproof` project, provisioned a 1 GiB Drive (the API minimum) and 1 vCPU/2 GiB Sandbox, and fixed Python's root-home permissions. Private origin readiness and unauthenticated 403 checks pass. Docker preflight remains INCONCLUSIVE: resource-limited containers exit 125 due to threaded cgroups. Original failed evidence retained; no controls removed, deployment still gated. Root cgroup adjustment awaits explicit approval after auto-review blocked it.
- Dependency checks now run: production SDK tree and frontend report zero vulnerabilities; CLI development tree reports 33 warnings. Normal build passes; local Vercel build fails on Windows with `spawn cmd.exe ENOENT`. Cloud Linux build, stop/resume, public gateway and cloud model checks remain open.

## 2026-10-16 — Guarded free demo and release verification

- Added a laptop/ngrok demo server with one origin for production UI/API, a separate persistent audit store, paired heartbeat lifecycle, persistent daily cap, one action at a time and cancellation access. Production UI defaults to live mode. Public HTTPS clean gate/export/validation/replay, SSE and access-denial checks passed; judging-period availability remains open.
- Fixed replay evidence generation to require Docker, use a fresh directory/database and actual diff hashes with PENDING policy, and fail on mismatches. Canonical-reference API/amount/clean replays and tamper rejection passed, without claiming model-authored repairs.
- Froze the existing committed local core/image without identity changes; preserved all three live development records, including API output truncation and clean-case provider failure. No held-out measurement run.
- Added planned Apache-2.0 LICENSE/NOTICE and direct package license inventory; updated README, judge guide, hosting/runbook and progress/decisions. Azure subscription expiry excludes that deployment path.
- Verification: 232 backend tests passed with Docker, ruff clean, frontend lint/build clean, frozen suite/configuration verification passed. Eight new tests cover demo static boundary/caps/concurrency and replay isolation/hash/non-overwrite. npm advisory lookup remains blocked by DNS.

## 2026-10-15 — Day 17 pulled forward: fair-baseline trial harness (B-19)

- Systems (`benchproof.trials.systems`): B0 runs the visible smoke gate on the original source. One NVIDIA repair agent serves B1 and B2 with the same prompts, schemas, model parameters and hard limits. B1 sees the task, accepted constraints, full source, visible test results and the raw probe record; B2 additionally sees graph context and contract-level protected check observations, confirms a finding only when a protected check of that constraint failed, repairs only after a protected failure, accepts only a gate-VERIFIED candidate and stops as `STALLED` before re-executing an identical rejected candidate. The agent returns complete files; the harness builds the diff and passes it through the unchanged patch policy (D-029).
- Records (`benchproof.trials`): balanced predetermined R12/R6 plans, sealed write-once trial records, resume without overwrite, `INTERRUPTED` for a trial that started without a record, product versus infrastructure failure classes, and a fresh frozen-evaluator run on every final candidate. `benchproof.trials.summary` alone reads trusted truth and keeps every assigned trial in its denominator.
- Configuration (`benchproof.trials.config`, `scripts/freeze_eval_config.py`): `eval-config-v1` pins model/parameters, prompt and schema hashes, budgets, patch limits, evaluator/contract hashes, graph and fingerprint rules, image reference, suite lock, plan hashes and a runtime code hash. `backend/evaluation/eval-config-v1.json` is a `candidate` (`210affd887e92863…`) because the runtime is uncommitted; `scripts/run_trials.py --final` refuses until it is `frozen` and matches, the lock verifies and Docker plus the live provider are used. Live non-final runs on held-out suites are refused.
- Status fix: B-17 was still `TODO` in the backlog although its evidence was committed on 14 Oct; it now reads DONE with its limitations.
- Verification: `tests/test_trials.py` 15 new tests; full regression 224 passed, 0 failed, 0 skipped; ruff clean. Development dry runs with a labeled mock provider (in-process and Docker, pinned image) — not measurements. One catalog listing confirmed the pinned model; no inference call, no spend. Price snapshot not recorded (official page unreadable), so cost stays unknown.
- Still open: commit and refreeze to obtain a `frozen` configuration, B-20 hosted release candidate, a first live development trial, B-21 frozen trials, release and submission work.

## 2026-10-14 — Day 15 pulled forward: skill catalog, gate-owned patch policy and second hardening pass

- Skills (B-22): `benchproof.skills` defines `skills-v1`, twelve named slash skills (`/start`, `/ready`, `/diagnose`, `/recover`, `/decision`, `/repair`, `/verify`, `/strength`, `/export`, `/validate`, `/replay`, `/cancel`) that each map to one existing owner-scoped endpoint and declare a cost class. `GET /api/v1/skills` and `GET /api/v1/audits/{id}/skills` return availability and a plain-sentence blocked reason computed from the audit record, the budgets and the cached runtime readiness; a test proves every skill endpoint is a registered route. The UI adds a Ctrl+K/`/` palette, the recommended next action names its skill, and every panel button calls the same skill (falling back to its local rule if the catalog is unavailable).
- Usability self-review (no volunteer tester was available; no user study is claimed): a proposed diff was stored and shown as `APPROVED` before any gate ran. Proposals are now `PENDING`; only the acceptance gate writes `APPROVED` or `REJECTED`, the UI explains the pending state, and the gate result names its verification attempt.
- Hashes: source manifests, intake, decision file dependencies, the suite lock and the evaluator hash are computed over LF-normalized bytes, and patched files are written with LF, so a CRLF checkout and an LF checkout agree. The held-out lock was re-frozen for the new hashing with unchanged assets (`37fc5d3f5ef981d4…` → `efe61ad8c4b0df56…`, D-028); every held-out truth label still holds.
- Runtime trust: the launcher runs the candidate in a child process with a cleared environment and exits without atexit hooks; the host accepts observations only when the parent's final stdout record equals `/out/observations.json`. `observations.json` must be a regular file; a timeout discards partial observations. Fixture ids are strictly validated. `worker-caller-path` is check version 2: a live call to `services.process_invoice` (dead-code and module-level calls do not count) plus observed worker idempotency across a repeated and a conflicting job.
- Lifecycle: a transition commits its state and `state_changed` event together; each gate run records its complete check set atomically as the next attempt and `checks.json` carries the attempt count; state writes after verification or investigation touch only active audits, so a cancelled audit keeps its state while the evidence is preserved; audit creation under an `Idempotency-Key` is one serialized transaction; mutation reservations are returned when the baseline is not VERIFIED; superseding a decision retires the prior record; zero-length diff ranges insert after the named line as GNU patch does.
- Verification: 31 new tests (`tests/test_hardening_day15.py`, `tests/test_skills.py`); full regression 209 passed, 0 failed, 0 skipped — the Docker daemon (29.7.2) and the pinned image were available, so the three isolated-runner tests executed the new launcher inside the container; ruff, TypeScript/Vite build and oxlint clean. No live provider call or paid execution.
- Still open: a volunteer usability session (Day 15 items 1–2), B-20 hosted release candidate, B-19 configuration freeze, B-21 frozen trials, release and submission work.

## 2026-10-14 — Day 14 pulled forward: frozen held-out suites and measured scope

- Held-out repair suite: `repair-r12-v1` with twelve opaque cases (`HO-01`…`HO-12`) generated by `scripts/author_heldout_r12.py` from four clean source styles; eight faulty variants (two per API/amount/caller/idempotency family) replace one module each and keep the trusted repair as the style's original module. Agent-visible files carry no fault markers, family names or check ids (`benchproof.suites.agent_visible_leaks`).
- Fixed-candidate gate suite: `gate-v12-v1` with twelve strict modify-only diffs (four trusted repairs, eight invalid shallow or harmful candidates). Every invalid candidate passes the new visible smoke gate `visible-smoke-v1` and is rejected by the protected gate.
- Separate assurance manifests: `graph-g8-v1` (eight hand-declared impact tasks), `freshness-f6-v1` (three stale/three fresh transitions on a held-out clean case), `trajectory-w8-v1` (eight frozen traces, rule `trajectory-fingerprint-v1`) and `mutants-m12-v1` (twelve templates, applicability and syntax frozen without execution).
- Freeze and lock: `scripts/freeze_suites.py` validates truth externally with the development harness, writes the manifests and `scope.json`, and pins every asset in `truth.lock.json`; `--verify` and `tests/test_suites.py` prove the committed assets are unchanged. D-027 records full R12/V12 scope, predeclared R6/V6 fallback ids and the public-holdout limitation.
- Runtime: mutation family resolution falls back to trusted truth for held-out cases. Verification: 10 new tests; full regression 165 passed, 3 Docker-dependent skipped (image not yet built); ruff clean. No live provider call or paid execution.

## 2026-10-13 — Day 12 pulled forward: trusted semantic mutation strength

- Templates: added `development-semantic-v1` with twelve evaluator-owned exact-anchor mutations, three each for API, amount, caller and idempotency behavior. All twelve apply to the clean accepted candidate, parse/import, execute, change the candidate hash and produce an adjudicated semantic result.
- Execution/scoring: a mutation run first requires a VERIFIED accepted baseline, reserves that baseline plus at most three relevant fresh branches against `max_executions`, and rebuilds every mutant from an immutable candidate copy. KILLED requires a valid intended deviation and a failing supporting protected check; invalid syntax/import is INVALID, never killed. Killed, survived, invalid, skipped and unknown remain separate.
- Policy/UI/evidence: mutation adequacy is OPTIONAL for this release, so strength never changes the protected gate verdict. Owner-scoped run/read endpoints, immutable SQLite records, UI counts/template versions, bundle export and a `mutation_completed` event are implemented. A missing run remains honestly `NOT_RUN` and `P1-mutations` stays in bundle omissions.
- Development evidence: `artifacts/mutations/development_strength.json` validates 12/12 templates. The bounded clean-control idempotency run killed 2/3 and exposed the intended cross-tenant-key survivor, reporting `WEAK`; four shared-budget executions were charged, 320 ms overhead was observed, and the accepted candidate hash stayed unchanged. A malformed test-only template was INVALID, not KILLED. This is development preparation, not a final M12 outcome.
- Verification: mutation tests cover registry cardinality/versioning, every template, invalid syntax, survivor honesty, budget exhaustion, owner scope, persistence and bundle contents. Full regression: 159 passed, 3 Docker-dependent skipped; ruff, TypeScript/Vite build and oxlint passed. No live provider call or paid runner execution was made.
- Still open: B-17 security hardening, Nebius Sandboxes spawn access/hosted execution, production identity, deployment, frozen final evaluations and release/submission work.

## 2026-10-13 — Day 11 pulled forward: bounded trajectory stopping and recovery

- Fingerprints: `trajectory-fingerprint-v1` hashes normalized action intent and failure semantics while removing only unstable request/action IDs, UUIDs and timestamps. Stable semantic check observations prevent fresh row IDs from masquerading as progress.
- Stopping: two consecutive actions with the same source, action intent and failure and no new relevant observation transition to `STALLED`. Four true-stall and four legitimate-progress development traces are frozen in `trajectory-w8-v1`; the progress set includes a patch resolving one check while another remains failed.
- Recovery: a STALLED audit may atomically consume one `narrow_failure_probe` recovery. It rebuilds current decision context, records the strategy change and preserves original action/patch/time counters. A repeated recovery fingerprint transitions to terminal `BLOCKED`; exhausted original budgets block without recovery.
- API/UI/evidence: owner-scoped trajectory status and recovery endpoints expose rule version, recovery count and remaining limits. The UI presents the stopped state and single recovery action. Bundle actions and usage retain strategy, fingerprints and remaining limits. `scripts/run_trajectory_evidence.py` records synthetic classifications separately from an actually executed development recovery.
- Verification: W8 preparation classified 8/8 development traces correctly; the executed MC-01 mock recovery progressed with counters preserved. Full regression: 143 passed, 3 Docker-dependent skipped; ruff, TypeScript/Vite build and oxlint passed. No live provider call or paid execution was made.
- Still open: B-16 mutation strength, Nebius Sandboxes spawn access/hosted execution, production identity, deployment, frozen final evaluations and release/submission work.

## 2026-10-12 — Day 10 pulled forward: decision freshness and current-only context

- Ledger: SQLite-backed PROPOSED/REVIEWED decisions now retain evidence, revisit conditions and server-computed file/source/contract/graph dependency hashes. Only CURRENT + REVIEWED IDs enter a context packet.
- Freshness: changed and deleted dependencies become sticky `STALE`; unrelated file edits leave specifically declared dependencies current. Responses expose stale reasons, expected/current versions and refresh overhead. `decisions.json` now contains the actual ledger and no longer claims `P1-decisions` as omitted.
- Trust boundary: source, contract, graph and decision context are rebuilt after provider inference; a late response is recorded and rejected with `STALE_CONTEXT`. UI-authored patches carry the context hash and are rejected if the relevant context moved.
- UI/API: added owner-scoped decision create/list and current-context endpoints plus a reviewed-ledger panel showing dependency status and versions. Mock audits are deterministic and never call the live provider; live mode remains explicit.
- Verification: three stale transitions (file changed, file deleted, contract changed), three fresh controls (unchanged, unrelated edit, unrelated add), stale/unreviewed exclusion, late-response rejection and old-context patch rejection are covered. Full regression: 132 passed, 3 Docker-dependent skipped; ruff, TypeScript/Vite build and oxlint passed. F6 preparation evidence is in `artifacts/decisions/f6_freshness_transitions.json` (development-only, not frozen evaluation data).
- Still open: B-15 recovery, B-16 mutation strength, Nebius Sandboxes spawn access/hosted execution, production identity, deployment, frozen evaluations and release/submission work.

## 2026-10-12 — Days 8–9: connected UI, recovery and owner boundary

- UI: one connected curated journey for live/mock selection, run lifecycle and resumable events, graph coverage and affected paths, investigation observations, readable bounded diff, explicit acceptance, gate-versus-test-strength results, and evidence build/validation/replay/download. Active audit, fixture, opaque owner capability and SSE cursor survive reload; a pending create retains its idempotency key.
- Access: every audit, event, action, patch, gate, bundle and replay route now requires `X-BenchProof-Owner`; audit listing is owner-filtered, patch lookup validates the parent audit, and a patch cannot be verified against another audit. Public intake remains curated examples only. The opaque capability is a bounded demo mechanism, not production authentication.
- Cancellation/reliability: remote reservations enter non-terminal `CANCEL_PENDING`; only confirmed worker reconciliation produces `CANCELLED`. Repeated cancel requests do not duplicate events. Docker daemon/image probe timeouts report runner unavailability instead of aborting API startup.
- Presentation: lifecycle state and gate verdict are separate; required-check UNKNOWN remains explicit; mutation/test strength is `NOT RUN · P1`; known provider, runner, budget, stale-source and cancellation errors retain evidence and provide a next action. Keyboard focus treatments and narrow-screen layouts are implemented.
- Verification: 123 pytest cases passed and 3 Docker-dependent cases skipped with the daemon unavailable; ruff, TypeScript/Vite production build and oxlint passed. Installed headless Chrome/Edge did not produce a screenshot artifact in this environment, so no screenshot or full manual browser journey is claimed.
- Still open: Nebius Sandboxes spawn access/hosted execution, production identity, deployment, P1 decision ledger/recovery/mutations, frozen evaluations and release/submission work.

## 2026-10-05 — Days 2–3: isolated runner boundary, approved constraints, durable state

- Provider: first real NVIDIA inference on Nebius (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`), structured-JSON proposal validated server-side; credential identified as a short-lived session token (owner must create a long-lived key).
- Execution: `benchproof.execution` adapter contract; `DockerRunner` (network none, read-only, cleared env, caps, timeout kill) and labeled `MockRunner`; protected launcher `runner/launcher/observe_invoice.py`; pinned candidate image `backend/runner/image/Dockerfile`; `scripts/runner_preflight.py`. Nebius Sandboxes recorded BLOCKED (no spawn permission); Contree SDK 0.3.6 installed for the record (D-024).
- Evaluator: single observation-based oracle shared by the in-process harness and the Docker runner; expected values never read from candidate output; forged PASS text ignored.
- Constraints: executable check registry; `approve_manifest` rejects relaxed/unknown/incomplete proposals (CONTRACT_UNAPPROVED) and missing oracles (REQUIRED_CHECK_MISSING); registry validated at API startup.
- Storage: leases, CAS transitions, ordered events, idempotency keys, SQLite triggers making check_results/artifacts immutable, evaluator-only check/verdict writes that must agree with stored checks.
- API: `Idempotency-Key` on `POST /audits` (replay vs 409 conflict), `contract_hash` pin, `GET /audits/{id}/events` as JSON or SSE with `after`/`Last-Event-ID`, CAS cancel with events, cached runner readiness.
- Tests: 76 pytest cases (3 Docker-backed, skipped without a daemon); ruff clean. No graph, patch, export, deployment or hosted sandbox run is claimed.

## 2026-10-04 — Day 1 scaffold (B-02 done; B-03 in progress; B-04 blocked)

- Backend: installable `benchproof-backend` package with `requirements.lock.txt`; FastAPI `health`, `ready`, `examples`, `constraints`/`contracts`, `audits` (create/get/list/cancel); SQLite migrations incl. worker heartbeats; lifespan-based startup.
- Constraints: pinned C-API, C-AMOUNT, C-INTEGRITY v1 with canonical hashes and a combined contract hash.
- Fixtures: five `development-v2` cases (AC-01, MC-01, CI-01, ID-01, clean-service) with public `fixture.json`, trusted `expected.json` and `reference/` repairs kept outside `app/`; source hashing per fixture.
- Evaluator: seven deterministic checks; gate returns VERIFIED / REJECTED / INCONCLUSIVE; development harness and `scripts/validate_fixtures.py` validate faulty, reference and clean behavior.
- Provider: Nebius Token Factory adapter (timeout, no retries); `scripts/provider_preflight.py` fails explicitly without a key and writes a sanitized record.
- Worker: `scripts/start_worker.py` heartbeat only; no candidate execution exists.
- UI: reads real `/api/v1` records and shows mode, provider/runner/worker state, constraints and examples.
- Tests: 40 pytest cases; ruff and oxlint clean. No model call, runner, graph, patch, export or deployment is claimed.

## 2026-10-03 — research-aligned planning pack v2

- Applied the recovered coding-agent research and checked comparison claims against primary product documentation.
- Kept the BenchProof name and Coding and Agentic Engineering track; changed the active product to an Agentic Engineering Assurance Runtime.
- Replaced ML leakage/metric fixtures with a multi-module Python service and API, exact-amount, caller-impact, and idempotency repair families.
- Added executable constraints, a typed state graph, source-linked decision freshness, deterministic risk reasons, trajectory stopping/recovery, independent adversarial verification, and bounded trusted mutations.
- Revised every previous Markdown document, the backlog, and all 28 daily sessions. Preserved freeze, submission buffer, provider integration, isolation, rights, and judging-access obligations.
- Separated repair, gate, graph, freshness, trajectory, and mutation evaluations; specified fair optional external-agent comparisons without fabricated results.
- Added research/positioning, detailed runtime, competitor benchmark, and migration-map documents. Rebuilt the pack archive.

This is a documentation revision. No feature, benchmark, competitor outcome, deployment, or submission is marked completed by it.

## 2026-10-03 — planning pack v1, superseded scope

Created the initial ML experiment-audit plan, event/source checks, execution schedule, independent verification concept, and early submission target. Its active ML/scikit-learn scope is superseded by v2; those original implementation tasks were not completed.

## Future release entry

- Date, tag, and full commit:
- User-visible behavior and supported contract families:
- Implemented assurance components and explicit exclusions:
- Model/provider and runner/image versions:
- Accepted contract/evaluator/suite hashes:
- Tests and measured result artifacts, including failures:
- Deployment and replay evidence:
- Known coverage limits and rollback reference:
