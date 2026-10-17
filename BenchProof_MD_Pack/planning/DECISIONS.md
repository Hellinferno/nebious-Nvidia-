# Architecture decisions and open choices

Research revision 3 October 2026. Accepted means selected for implementation, not already built. Evidence and actual status belong in [progress](PROGRESS_LOG.md).

## Retained decisions

| ID | Decision | Reason / revisit condition |
| --- | --- | --- |
| D-001 | BenchProof; Coding and Agentic Engineering track | Preserve project identity and research-directed fit; revisit on explicit change |
| D-003 | React/TypeScript/Vite, FastAPI durable worker | Simple usable product; revise for observed host mismatch |
| D-004 | Meaningful runtime NVIDIA inference on Nebius | Required planned provider path; resolve actual model/access |
| D-005 | Prefer Nebius Sandboxes behind adapter | Isolated execution; test alternate if access absent by 6 Oct |
| D-006 | Protected independent deterministic acceptance | Candidate cannot control its success; never remove for schedule pressure |
| D-007 | Curated public examples only | Bounded useful reviewer access; broader intake needs separate review |
| D-009 | Original synthetic fixture inputs | Reproducible rights and no private invoice data |
| D-010 | Single-instance SQLite plus durable artifacts | Small graph/record workload; revisit actual storage/scale limits |
| D-011 | Freeze 25 Oct; internal submit 28 Oct 20:00 IST | Protect release and form/access buffer; official changes govern |
| D-012 | No guaranteed-win/universal-proof claim | Evidence supports declared version/scope only |

## Superseded decisions

| ID | Previous scope | Replacement | Migration effect |
| --- | --- | --- | --- |
| D-002 | Python/scikit-learn tabular ML audit | D-013 assurance runtime on Python service | Retire ML data/split/label machinery from active build |
| D-008 | Target/metric leakage P0, group/replay faults P1 | D-014 engineering repair families | Rewrite cases, prompts, check contracts and claims; no measured result carries over |

The initial design had no completed implementation or benchmark to migrate. Independent verification, provenance and replay principles are retained. ML audit can be a later vertical, outside current release commitments.

## Research-aligned decisions

| ID | Accepted planning choice | Evidence/revisit condition |
| --- | --- | --- |
| D-013 | Agentic Engineering Assurance Runtime as product | Recovered latest research; validate working user decision and baselines |
| D-014 | P0 API/amount; P1 caller/idempotency repair families | Synthetic precise contracts; expand only after complete P0 |
| D-015 | AST/manifest typed graph in SQLite; provenance and gaps explicit | Aider/source research shows graph alone is familiar; no claim of universal impact |
| D-016 | Human-owned pinned executable constraints with external trusted oracle | Negative gate tests must establish protection before public use |
| D-017 | Hash-bound context; P1 decision dependency invalidation | F6 and delayed-proposal tests; never silently reuse stale state |
| D-018 | Ordinal risk with deterministic reasons | No calibrated probability; revise rules from development evidence before freeze |
| D-019 | Two repeated no-progress fingerprints stop; one P1 recovery | Validate W8 controls; original limits never reset |
| D-020 | P1 trusted pre-authored mutants, max three per live verification | Separate strength metric; omit with NOT_RUN if budget lacks room |
| D-021 | Provider-neutral diff/trace records; eight product integrations optional | Desk research is not API integration or performance ranking |
| D-022 | R12/V12/G8/F6/W8/M12 separated; explicit R6/V6 fallback | Freeze chosen scope and denominator before final runs |
| D-023 | Primary comparison same NVIDIA agent with/without assurance | Shared final evaluator and hard budgets; component claims need ablation |

## Open implementation choices

| ID | Choice | Evidence needed | Target |
| --- | --- | --- | --- |
| O-001 | Exact NVIDIA model and parameters | Actual catalog/card/license, five development preflight behaviors, usage | 4–8 Oct |
| O-002 | Contree auth/SDK/lifecycle and limits | Real image/command/fresh state/artifact/cancel observations | 5–6 Oct |
| O-003 | Tested alternate runner if needed | Resolved for development 5 Oct by D-024 (local Docker runner); hosted execution route still Sandboxes pending access | 6 Oct |
| O-004 | App host/persistence/lifetime | Proposal 5 Oct, untested: one Linux VM with Docker, persistent disk for SQLite/artifacts, HTTPS reverse proxy; decide after runner access is known | Select 6 Oct; deploy 19 Oct |
| O-005 | Actual usage/cost ceilings | Dated prices/grants/expiry and measured upper bounds | 6 Oct; finalize 20 Oct |
| O-006 | Supported graph forms and mappings | Fixture AST coverage, unknown-edge tests and reviewed manifest | 7–8 Oct |
| O-007 | Final suite/scope and fingerprint normalization | P0/P1 evidence, controls and budget forecast | Suite 17 Oct; configuration 20 Oct |
| O-008 | License/model/image/asset inventory | Actual component terms and top-level LICENSE | 25 Oct |
| O-009 | Mutation adequacy required or optional per release contract | Valid templates, survivor behavior, overhead and explicit accepted policy | 15–20 Oct |
| O-010 | Optional external-agent tools/configuration | Real access/versions/terms and remaining time | P2 only |

## Decisions recorded during implementation

### D-024 — Local Docker runner as the tested development alternate to Nebius Sandboxes

- Date, owner, status: 5 October 2026, Ravi, accepted for development; hosted route remains open.
- Trigger and observed evidence: Sandboxes `GET /whoami` returned 200 with every permission `false` and `/images` returned 403 (`artifacts/runner/runner_20261005T181249.json`). Docker Desktop 29.7.2 (linux engine) available locally. Contract `6d5b95ce…`; no graph yet.
- Constraints and options investigated: (a) wait for Sandboxes beta access — blocks all execution work; (b) run candidates in-process — violates the protected boundary; (c) local Docker container with network none, read-only root, cleared env, resource caps, timeout kill — selected.
- Selected option, rationale and artifacts: (c). Candidate image `benchproof-candidate:dev@sha256:104ce828…` from `python@sha256:02108f5d…`; launcher `backend/runner/launcher/observe_invoice.py` mounted read-only outside `app/`; trusted oracle judges `observations.json` on the host. Evidence: clean VERIFIED, MC-01 REJECTED, timeout negative killed, isolation probes all denied.
- Cost, security, user, schedule and coverage effects: no provider cost; shared-kernel isolation only (not VM); unblocks Days 3–10 development; the final hosted story still needs Sandboxes or an isolated VM route per doc 07 — a local container is not accepted as the hosted route merely because it starts.
- Dependency hashes, affected documents/contracts and revisit condition: image digest above; docs 07/09, backlog B-05, O-003/O-004. Revisit when Sandboxes `spawn` permission is granted or by the 6 Oct fallback review.
- Superseded ID: none.

### D-025 — Opaque local owner capability for the bounded demo

- Date, owner, status: 12 October 2026, Ravi, accepted for local/demo use only.
- Trigger and observed evidence: B-13 required cross-session denial before hosted identity infrastructure exists. Earlier routes used one hard-coded owner and exposed all audits to any caller.
- Constraints and options actually investigated: (a) keep the shared owner — rejected; (b) add full OAuth before deployment — premature and outside the Day 9 cut line; (c) require a high-entropy browser-generated capability in `X-BenchProof-Owner`, bind all records and idempotency keys to it, and owner-filter every private route — selected.
- Selected option, rationale and artifacts: (c). The UI stores one capability in localStorage and sends it on API, SSE and bundle requests. Tests deny a different capability across audit, event, patch and bundle routes and prevent cross-audit patch verification.
- Cost, security, user, schedule and coverage effects: no external identity dependency and reliable reload behavior. The capability is bearer-like and localStorage-backed; it is not production authentication, revocation, account recovery or multi-device identity. Do not expose it in bundles, URLs or logs.
- Dependency hashes, affected documents/contracts and revisit condition: API/data contract, B-13, UI runtime and `test_api_day8_day9.py`. Replace or bind behind hosted authentication/reverse-proxy identity before claiming production multi-user security in B-20/B-23.
- Superseded ID: the Day 3 hard-coded single-owner development behavior.

### D-026 — Mutation adequacy remains an optional release signal

- Date, owner, status: 13 October 2026, Ravi, accepted for the current release contract.
- Trigger and observed evidence: B-16 produced twelve valid semantic templates and a bounded clean-control idempotency run with two killed mutants and one surviving cross-tenant-key mutant (`artifacts/mutations/development_strength.json`). The required acceptance gate still passes its declared checks, showing that mutation sensitivity and contract conformance answer different questions.
- Constraints and options actually investigated: (a) make every selected mutation mandatory for VERIFIED; (b) keep mutation strength optional and visibly separate; (c) omit mutation execution. Option (b) is selected because the accepted required contract does not yet declare a cross-tenant collision check, and retroactively changing gate policy would weaken comparability and conflate P0 acceptance with P1 diagnostic strength.
- Selected option, rationale and artifacts: report NOT_RUN, ADEQUATE_FOR_DECLARED_MUTANTS, WEAK or INCONCLUSIVE independently. A survivor yields WEAK; invalid/skipped/unknown coverage prevents adequacy; none of these values can promote or demote the protected gate verdict. Template/result records are immutable and included in bundles when run.
- Cost, security, user, schedule and coverage effects: each run consumes one baseline plus at most three mutant executions from `max_executions=12`; candidate hashes are checked before/after. The UI exposes every outcome count and labels policy OPTIONAL. `WEAK` is not hidden and adequacy is bounded to the named templates, never generalized to complete coverage.
- Dependency hashes, affected documents/contracts and revisit condition: `development-semantic-v1`, B-16, API/data contract, UI and evidence bundle. Revisit O-009 only when the final release contract and M12 manifest are frozen; making mutations required is a new versioned policy, not an in-place reinterpretation.
- Superseded ID: D-020's policy choice was previously open; its max-three trusted-template boundary remains.

### D-027 — Full R12/V12 scope with predeclared R6/V6 fallback and a hash-locked, public holdout

- Date, owner, status: 14 October 2026, Ravi, accepted before any final trial.
- Trigger and observed evidence: all four repair families, the protected gate, decision freshness, trajectory stopping and trusted mutations are implemented and tested, so the full suite breadth is buildable. Twelve held-out cases and twelve fixed candidates validated externally (`artifacts/suites/freeze_20261014T080352.json`); lock `37fc5d3f5ef981d4…`.
- Constraints and options actually investigated: (a) author only R6/V6 — saves authoring time but discards two implemented families from the headline measurement; (b) author R12/V12 and decide the fallback after seeing early results — forbidden by the evaluation plan; (c) author R12/V12 now, predeclare the R6/V6 subsets by opaque id and allow the fallback only before the first final trial for a stated reserve or time reason — selected. For truth handling: (i) keep truth outside the repository — loses tamper evidence and risks loss on one machine; (ii) encrypt truth in the repository — adds a secret and an external tool to the release path; (iii) commit truth and hash-lock it — selected.
- Selected option, rationale and prototype/check artifacts: (c) and (iii). `backend/fixtures/heldout/` holds agent-visible sources with opaque ids and no answer-bearing text, trusted `expected.json`/`reference/` assets, twelve candidate diffs, six manifests, `scope.json` and `truth.lock.json`. `scripts/freeze_suites.py --verify` and `tests/test_suites.py` prove the committed assets match the lock and the generators.
- Cost, security, user, schedule and coverage effects: no provider spend. The repository is public, so the holdout is "untouched by tuning since the lock commit", not secret; the model never has repository access and truth never enters prompts or candidate filesystems (tested). Worst-case model usage is estimated at about 1.7 M tokens for 72 model trials; a dated price snapshot is still missing, so cost remains unknown and 20% of any usable credit is reserved for judging.
- Dependency hashes, affected documents/contracts and revisit condition: lock hash above; evaluation plan, data/fixtures doc, B-18/B-19/B-21, release checklist. Revisit only if a harness defect requires versioned correction; any later change to a frozen asset invalidates the lock and must be recorded as a new suite version, never an in-place edit.
- Superseded ID: none. O-007 (final suite/scope) is resolved for suite assets; fingerprint normalization remains `trajectory-fingerprint-v1`.

### D-028 — Line-ending independent hashes, re-locked holdout, gate-owned patch policy and `worker-caller-path` v2

- Date, owner, status: 14 October 2026, Ravi, accepted (Day 15 pulled forward).
- Trigger and observed evidence: the first full test run after the second hardening pass failed `test_intake` and the V12 label test because candidate trees were hashed from raw bytes while Git rewrites line endings per checkout; the D-027 lock (`37fc5d3f5ef981d4…`) would therefore have failed on the first Linux clone (B-20/B-23), and `apply_patch_to_dir` produced platform-dependent candidate hashes on Windows. Separately, a proposed diff was displayed and stored as `APPROVED` before any gate ran, and the static `worker-caller-path` check accepted dead-code delegation.
- Constraints and options actually investigated: (a) keep raw-byte hashes and force LF checkouts through `.gitattributes` — leaves every already-recorded hash dependent on the author machine; (b) normalize CRLF to LF before hashing everywhere (source manifests, intake, decision dependencies, suite lock, evaluator hash) and re-freeze the lock — selected; (c) leave the lock and accept a known Linux failure — rejected. For patch policy: keep `APPROVED` on proposal, or store `PENDING` and let only the gate write `APPROVED`/`REJECTED` — the latter selected. For the worker check: keep v1, or version it to v2 (live call only, plus observed repeat/conflict idempotency) — v2 selected because the registry already versions checks and no stored verdict is reinterpreted.
- Selected option, rationale and prototype/check artifacts: before re-locking, the committed lock still matched the assets under the old raw hashing (full regression run earlier the same day), so the assets are byte-identical modulo line endings. `scripts/author_heldout_v12.py` recomputed the twelve candidate hashes and `scripts/freeze_suites.py` rewrote the manifests and lock (`efe61ad8c4b0df56…`, `artifacts/suites/freeze_20261014T130104.json`); every held-out case still fails exactly its intended checks under `worker-caller-path` v2 and all twelve V12 labels hold (`tests/test_suites.py`). Hash equality across CRLF/LF copies is tested in `tests/test_hardening_day15.py`.
- Cost, security, user, schedule and coverage effects: no provider spend. Hashes still detect every content change. Patches now read `PENDING` until judged, so the UI no longer shows an approval that never happened. The suite content and scope (R12/V12, R6/V6 fallback) are unchanged; only hash values moved.
- Dependency hashes, affected documents/contracts and revisit condition: new lock hash above; API/data contract, UI spec, integrity report, B-18/B-22. Revisit only if a binary asset is ever added to the holdout (normalization must then be limited to text) or if a later check version changes a frozen truth label, which would require a new suite version.
- Superseded ID and new version where applicable: amends the lock hash recorded in D-027; D-027's scope decision stands.

### D-029 — B-19 trial protocol: one shared repair agent, assurance as the only B1/B2 difference, candidate configuration until commit

- Date, owner, status: 15 October 2026, Ravi, accepted for implementation (Day 17 pulled forward); final configuration freeze still pending.
- Trigger and observed evidence: B1 and B2 need the same NVIDIA repair agent, but the runtime had no model-authored repair (the patch route accepts an externally supplied diff; B-04 lists repair-proposal behavior as remaining). The strict patch applier rejects any hunk whose context or counts are off by one, which would turn model formatting slips into apparent repair failures for both systems.
- Constraints and options actually investigated: (a) have the model write unified diffs directly — every formatting slip becomes an invalid patch; (b) have the model return complete new contents of at most three existing `app/*.py` files and let the harness build the diff with `difflib`, then pass it through the unchanged `validate_patch`/`apply_patch_to_dir` rules plus a check that the applied file reproduces the submitted content — selected, because the protected patch policy, size caps and base-hash check stay exactly as they are; (c) relax the applier — rejected as a weakened P0 boundary. For B1 information: give B1 only the source and constraints, or also visible tests and the raw probe record (route responses, worker receipts) that a developer could observe — the latter selected so B1 is not weakened by hidden task intent; launcher metadata is stripped. For B2 confirmation: trust the model's CONFIRMED label, or confirm a finding only when an executed protected check of that constraint failed — the latter selected and recorded per finding (`model_status` keeps the original label).
- Selected option, rationale and prototype/check artifacts: B2 receives everything B1 receives plus graph context and contract-level protected check observations; it repairs only after a protected failure, accepts only a gate-VERIFIED candidate, and stops as `STALLED` before re-executing an identical rejected candidate. B1 submits its latest applied candidate unless it withdraws; it never sees protected outcomes and cannot judge its own success. Shared hard limits: 6 model calls (one format-only repair per call inside the cap), 1,536 output tokens per call, 24,000 prompt characters per call, 24,000 tokens per trial (reserved before each call as prompt characters / 3 + output cap, reconciled with reported usage), 12 executions, 2 patches, 300 s, existing diff caps. Final outcomes come from a fresh frozen-evaluator run outside the loop; diagnosis is scored at the accepted-constraint level and counts as correct only with an executed probe whose trusted re-judgment shows an intended failure, otherwise claim-only. Live non-final runs on held-out suites are refused so no live model output is tuned on the holdout. Evidence: `tests/test_trials.py` (15 tests, including a nine-trial hand-counted summary), development dry runs `artifacts/trials/dev-dryrun-mock-inprocess` and `artifacts/trials/dev-dryrun-mock-docker` (mock provider, not measurements).
- Cost, security, user, schedule and coverage effects: no inference spend; one catalog listing. Full-file output costs more output tokens than a diff for large files; the held-out files are under 1.2 KB each. C-INTEGRITY covers both the caller-path and idempotency families, so constraint-level diagnosis does not distinguish them. The decision ledger and recovery replan are not exercised inside a fresh trial (no decisions exist); this is disclosed in the configuration. Temperature 0 makes three trials per case repeats of one configuration, not independent problems, as the evaluation plan already states.
- Dependency hashes, affected documents/contracts and revisit condition: candidate configuration `210affd887e92863…` (runtime uncommitted, so status `candidate`); suite lock `efe61ad8c4b0df56…`; evaluation plan, API/data contracts, B-19/B-21. Refreeze after the runtime is committed and after the B-20 deployment path is understood; any later prompt, schema, budget, model, image or runtime change produces a different configuration hash and needs a new configuration version with affected reruns.
- Superseded ID and new version where applicable: none; extends D-027's trial counts with the executable protocol.

### D-030 — Laptop/ngrok demo after Azure expiry; local core configuration freeze

- Date/status: 16 October 2026, implemented demo fallback; final release availability remains open.
- Trigger: owner reports expired Azure subscription, no domain, Token Factory credits and an 8 GB/i3 laptop that can stay on. No provisionable Nebius compute account found; Sandboxes token lacks spawn/list permission.
- Options checked: Cloudflare free Workers cannot host the current Docker adapter; Containers requires Workers Paid; domain-free Quick Tunnels lack SSE. Named Cloudflare Tunnel requires a domain. Existing authenticated ngrok supplies a free assigned HTTPS domain; laptop retains tested Docker isolation and remote NVIDIA inference.
- Observed choice: `https://dierdre-miasmatical-madge.ngrok-free.dev` routes to localhost:8765. Public UI/API, clean gate/export/validation/replay, SSE, owner denial and `.env` denial passed. Only the built UI is static. SQLite shared limit 60 actions/day (UTC) survives restart; actions serialize and cancellation stays available. No cloud resource or paid plan created.
- Freeze: committed local core `ad1955703ccc484e380f40edab33afe764beb3ba` and image match unchanged identity `210affd887e92863…`, allowing the evaluation configuration to be frozen. This is explicitly a local core freeze with hosting preparation incomplete; new demo wrapper/UI is not a frozen committed deployment. No final holdout run started under an unreviewed cost/hosting assumption.
- Revisit: laptop power/network/Docker/tunnel, ngrok free quota/browser warning, backup/restore, supervision and access throughout judging remain operational constraints. Heartbeat does not process queued jobs. API JSON truncation and a provider connection failure remain preserved development failures. Revisit if a host/domain becomes available, quota is inadequate or model/prompts/budgets/runtime/image change.
- Superseded: Azure exploration blocked by expiry; D-024's Docker boundary and D-027/D-029's evaluation protocol remain intact.

### D-031 — Vercel Hobby gateway with persistent trusted Sandbox and unchanged candidate limits

- Date/status: 16 October 2026, implemented and functionally verified; final measured release remains open.
- Owner selected Vercel after Azure expiry and explicitly approved server-side storage of the existing Nebius key and the dedicated cloud VM's root cgroup adjustment. API-confirmed Hobby plan; no paid upgrade. Public alias: `https://benchproof.vercel.app`; current gateway `dpl_2iK7BZFvWMGv1KfCB2b96zZ5Lu14`.
- Topology: static React UI and server-only API gateway; named 1 vCPU/2 GiB Sandbox with a 1 GiB Drive for SQLite, bundles and UTC daily limits. Private origin header, allowlisted upload, exact runtime identity and explicit reviewed upgrades; no automatic creation/replacement of lost state. No provider key or control-plane credential enters candidate containers or browser output.
- Compatibility fixes: Python installed outside root's private home; approved cgroup delegation after moving this VM's own services to a child group; only the fresh private snapshot's output directory becomes writable by uid 65534. Candidate/launcher remain read-only; network denial, 256 MiB memory/swap, 1 CPU, 64 pids, dropped capabilities and timeout kill are preserved. Both original failed cloud preflights are retained.
- Observed evidence: `artifacts/vercel/cloud-check-1792146334676.json` includes clean/faulty judgments, isolation findings, actual OOM kill (137), timeout termination and audit/bundle/counter/heartbeat persistence followed by fresh replay. Public check `public-check-1792146557262.json` includes cold resume (4,744 ms), export/replay/SSE/access controls and meaningful live MC-01 diagnosis (1,113 API-reported tokens).
- Browser validation exposed a real concurrent timeout-extension 503 after a harness assertion correction. Gateway recovery now rechecks actual lifetime and still refuses insufficient windows. `artifacts/browser-vercel-20261016/browser-check-1792173340237.json`: new unauthenticated profile, cold parallel boot, clean gate/export/validation/replay/download and reload passed; one create request, no exceptions/HTTP errors. This is automation, not a user study.
- Identity/limits: package `d858c8c2a9494f1ea8922068969724b4236f0c2c0ac3b32e060d95d533ac658c`; candidate image `e97eb0d1e5902fe17fc632d0376d325d2584fb7f6cc1f919199c0c9a9bcbd68f`. Core compatibility change invalidates current reuse of historical configuration v1; its guard correctly reports runtime drift. Do not overwrite v1 or inherit its measured claims. New committed/reviewed configuration, final trials, independent backups, quota/credit reserve, rights review and submission remain open.
- Supersedes D-030 only as the primary hosting route; laptop/ngrok remains optional fallback. Hobby quotas and bounded session windows are operational limits, not an availability guarantee.

### D-032 — Make the real coding-agent journey primary; preserve assurance as supporting infrastructure

- Date/status: 17 October 2026, product direction selected by the owner; implementation details and dates are a planning baseline, not shipped capabilities or guaranteed delivery.
- Trigger: the owner clarified that the intended track experience is an agent that writes, runs and tests code through Token Factory, rather than primarily a verification dashboard. The 17-product research and five recurring problem areas are recorded in `CODING_AGENT_RESEARCH_2026-10-17.md`; they are desk research, not a competitor benchmark or validated market demand.
- Source inspection: the public frontend submits canonical reference diffs; real model-authored repairs exist in the offline trial harness. `start_worker.py` only heartbeats, `DockerRunner` runs the invoice observation launcher, and the gateway caps request bodies at 64 KiB. A generic coding agent therefore requires production task processing, supported project intake, a project execution profile and deliberate API/deployment changes, not just a renamed UI.
- Selected plan: `BUILD_PLAN.md`, C-01–C-10. First deliver genuine generation -> isolated execution -> observed tests -> bounded revision -> reviewable diff. Then add small non-sensitive Python project input, persistent task intent, pause/resume/cancel, scoped edits/checkpoints, usage limits and task-centered UI. Retain the BenchProof name, Vercel hosting path, meaningful NVIDIA Token Factory calls and candidate isolation. No new framework, model tier or paid host is selected by this plan.
- Trust/evidence effects: ordinary imported project tests are not the protected invoice oracle and cannot inherit its `VERIFIED` semantics. Version new task/action/check contracts, preserve old audit compatibility and all historical trial/freeze artifacts, and require fresh release/evaluation evidence. No candidacy, input or budget guard is removed to make a demo succeed.
- Scope/schedule: target first vertical slice 18 Oct, supported projects 19–21 Oct, reliability/UI/cloud acceptance 22–24 Oct, feature freeze 25 Oct, evaluation/rehearsal/video/access/submission work 25–28 Oct with 29–30 Oct buffer. Targets assume the owner's availability and budget checks; miss a gate honestly and cut optional breadth. Do not recreate a general IDE or enable arbitrary repository/shell execution.
- Authorizations/limitations: this planning update makes no model call, changes no deployment, adds no paid resource and authorizes no commit/push/tag/submission. Provider-output reliability, credits/judging reserve and backup/restore remain open. The owner must separately authorize publishing Git history and confirm actual entry submission.
- Supersession: replaces future fixture-first product/backlog priority where it conflicts with the task-centered journey. D-024's isolation boundary, D-027/D-029's historical evaluation identities and D-031's hosting safeguards are retained. Old results are not rewritten as new coding-agent results.

## Decision entry template

### D-[number] — title

- Date, owner, status: proposed / accepted / superseded.
- Trigger and observed evidence; source/contract/graph versions.
- Constraints and options actually investigated.
- Selected option, rationale and prototype/check artifacts.
- Cost, security, user, schedule and coverage effects.
- Dependency hashes, affected documents/contracts and revisit condition.
- Superseded ID and new version where applicable.

A proposed fallback/model/check remains proposed until tested. A model-authored decision cannot approve its own policy change. Keep historical decisions and invalidation reasons; do not rewrite them to imply the latest release was always the plan.
