# Implementation backlog

## Active coding-agent build — 17 October 2026

The user selected a task-centered coding agent after the expanded product/problem review. [BUILD_PLAN.md](../../BUILD_PLAN.md) is the active dependency-ordered implementation plan. It supersedes the future priority order of the legacy fixture-first backlog below, not its historical implementation/evaluation evidence. Implementation has started; the new application workflow is not shipped. Completion requires the recorded acceptance evidence, not the plan alone.

| Ticket | Required outcome | Target (IST) | State |
| --- | --- | --- | --- |
| C-01 | Reproduce provider/schema/truncation failures; bounded genuine generation | 17 Oct | DONE (development acceptance; new backend rollout pending) |
| C-02 | Versioned task/project/action contracts and a real durable worker | 17–18 Oct | DONE (contracts, durable store, leased worker, admission config, body limits, API routes) |
| C-03 | First real task -> model edit -> isolated test -> revision -> diff | 18 Oct | DONE (loop verification harness, multi-turn revision tests, repeated-candidate stall circuit breaker, and CLI evidence runner) |
| C-04 | Safe supported project intake and general Python test profile | 19–20 Oct | DONE (intake limits, path safety, manifest fingerprinting, isolated unittest runner, 2 sample projects, 441 passing tests) |
| C-05 | Real bug fix and small feature on distinct imported projects | 20–21 Oct | DONE (bug fix on StringCalculator, bounded feature on BankAccount, protected test refusal, stale base refusal, unauthorized path refusal) |
| C-06 | Persistent intent, resume/cancel, checkpoints, stall and budget controls | 21–22 Oct | DONE (immutable checkpoint log, CAS checkpoint restore, pause/resume/cancel controls, sanitized JSON/ZIP task bundle export, 455 passing tests) |
| C-07 | Primary task workspace with source, plan, activity, diff, checks and download | 22–23 Oct | TODO |
| C-08 | Cloud worker/session/quota acceptance, ownership, isolation and backup/restore | 23–24 Oct | TODO |
| C-09 | User sessions, new evaluation identity/results and genuine rehearsals | 24–26 Oct | TODO |
| C-10 | Clean-clone/rights/access, authentic video and actual owner submission | 26–28 Oct | TODO |

Targets assume the availability stated in the build plan and are not delivery guarantees. Each ticket's dependencies, acceptance artifacts and stop/cut rules are defined there. All historical freeze/configuration records remain immutable. Do not execute/publish untrusted projects, make paid upgrades or commit/push merely because the plan mentions those future steps.

C-01 evidence: strict completion and safe error tests; both retained AC-01 length-limited replies reproduce `MODEL_OUTPUT_TRUNCATED`; one approved NVIDIA generation yields a genuine patch, then the existing cloud gate rejects the original and accepts that exact edit. See `artifacts/coding/c01-live-20261017-1/` and [coding runtime notes](../../backend/benchproof/coding/README.md).
C-02 evidence: durable owner-scoped task/action/event storage with monotonic leases and fences; single-job worker heartbeats and background execution; FastAPI endpoints for brief/plan/approval/start/pause/resume/cancel/events/diffs/usage; 419 passing tests.
C-03 evidence: verified multi-stage task loop (Task -> Plan -> Approval -> Baseline -> Edit -> Candidate -> Final -> Review Ready); candidate failure feedback passed to subsequent revision attempts; repeated-candidate stall detection (`REPEATED_CANDIDATE` -> `STALLED`) without wasted executions; CLI evidence runner `backend/scripts/run_coding_loop.py` produces verified artifact pack in `artifacts/coding/c03-verification-20261017/`. Full regression 423 passing tests.
C-04 evidence: constrained project intake (<= 20 UTF-8 text files, 24 KiB/file, 128 KiB raw total, 256 KiB encoded body limit, path traversal rejection, secret exclusion, case collision rejection, canonical LF manifest fingerprinting); generic `unittest` runner with process isolation, network/secret denial probes; two sample projects (`StringCalculator` and `BankAccount`) pass unchanged; zero tests collected triggers `ZERO_TESTS_COLLECTED`; full end-to-end coding task loop executed against user project reaching `REVIEW_READY` with verified diff. Full backend suite 441 passing tests.
C-05 evidence: executed agent on imported projects for both a real bug fix (`StringCalculator` negative number handling) and a bounded feature (`BankAccount` transfer method) with complete vertical loop reaching `REVIEW_READY` and verified diffs; verified protected test refusal (`tests/` paths rejected from brief/plan/patch), unauthorized new path refusal (non-app / path traversal), and stale base rejection. Verified in `backend/tests/test_project_tasks.py` (5 passing tests).
C-06 evidence: implemented append-only immutable checkpoint history in `coding_checkpoints` table recording stage, state, and checkpoint data on approval, action completion, and manual updates; conflict-checked compare-and-swap (CAS) rollback via `/restore` resetting next stage and state to PAUSED while strictly preserving monotonic usage budgets (`model_calls`, `patch_attempts`, `executions`, `active_seconds`); sanitized export bundle via `/bundle` (structured JSON and `.zip` archive containing manifest, patch diff, plan, test reports, events, and markdown summary with strict exclusion of credentials); durability controls verified for lease expiry reconciliation, uncertain model action marking, explicit retry requirements without double-spend, and container cancellation reconciliation. Verified in `backend/tests/test_coding_checkpoints.py` (9 passing tests). Full backend suite 455 passing tests.

## Legacy assurance backlog

Research-aligned v2. All tickets start TODO until actual evidence is recorded. Dependencies, outputs and cut lines below replace the active ML-audit work. Detailed behavior is in [runtime](../docs/25_ASSURANCE_RUNTIME.md); work dates are in [daily tasks](DAILY_TASKS.md).

## Board rules

Status is TODO / IN_PROGRESS / BLOCKED / DONE. DONE requires acceptance artifacts and a tested commit, not a written specification. Complete the earliest unmet P0 dependency; P1 and P2 cannot consume release buffer. Mixed-priority tickets retain their stated P0 minimum even if their richer feature is cut.

## B-01 — Event and account readiness · P0

**Owner:** Ravi. **Dependencies:** None. **Target:** 4 Oct. **Status:** IN_PROGRESS (registration confirmed 4 Oct; Nebius service-account static key present 5 Oct, expires 2031-10-04; credits/billing not yet recorded; sandbox access not requested).

**Work:** Review this event eligibility/registration; record actual inference/runner access, credits, expiry and billing controls. Keep account facts separate from offered resources.

**Acceptance/evidence:** Access and eligibility checklist has actual owner confirmations; no assumed grants or beta access. Save sanitized account/access record and unresolved blockers.

**Scope/cut line:** Never replace required eligibility/access facts with assumptions.

## B-02 — Source scaffold and configuration · P0

**Owner:** Ravi. **Dependencies:** B-01 account facts; docs can scaffold independently. **Target:** 4 Oct. **Status:** DONE 4 Oct (locked install, health/ready/worker heartbeat, explicit live-mode refusal; see progress log).

**Work:** Create installable Python package, React/TypeScript UI, locked dependencies, .env.example and safe ignore rules. Add domain/API/state/evaluator module boundaries from repository structure.

**Acceptance/evidence:** Locked install and health/worker startup work; missing live credentials fail explicitly instead of silently switching to mock. Save tested versions/commit.

**Scope/cut line:** Use one worker/store; defer infrastructure abstractions.

## B-03 — Executable constraints and development fixtures · P0

**Owner:** Ravi. **Dependencies:** B-02. **Target:** 4–6 Oct. **Status:** DONE 5 Oct for the P0 minimum (AC/MC/CI/ID/clean validated in-process and through the Docker runner; relaxed/unknown/incomplete manifests → CONTRACT_UNAPPROVED; missing oracle → REQUIRED_CHECK_MISSING; trusted assets verified absent from candidate snapshots). Shallow-candidate case deferred to the gate suite in B-18.

**Work:** Implement five visible development cases and original synthetic inputs; pin approved C-API/C-AMOUNT/C-CALLER/C-IDEMPOTENCY/C-INTEGRITY mappings. Write external trusted oracle and reference repairs.

**Acceptance/evidence:** Faulty cases fail intended checks, reference repairs pass, clean passes untouched. Unapproved/missing required check is blocked; hidden truth absent from candidate.

**Scope/cut line:** AC/MC/clean first; CI/ID can stay P1.

## B-04 — Real NVIDIA inference adapter · P0

**Owner:** Ravi. **Dependencies:** B-01/B-02. **Target:** 4–8 Oct. **Status:** IN_PROGRESS (5 Oct: real catalog + bounded inference + valid structured JSON proposal on `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, no credential leakage; model card/license, tool loop and repair-proposal behaviors remain).

**Work:** Discover actual model catalog; record model card/license. Validate structured constraint-linked actions, repair proposal, usage, timeouts and format rejection behind a narrow adapter.

**Acceptance/evidence:** Real call returns known NVIDIA model metadata; five preflight behaviors recorded; no credential leakage. A useful live action is traceable to the call.

**Scope/cut line:** One tested model; extra tiers/providers P2.

## B-05 — Isolated runner and protected transport · P0

**Owner:** Ravi. **Dependencies:** B-01/B-02. **Target:** 5–6 Oct. **Status:** IN_PROGRESS (5 Oct: Sandboxes token accepted but no spawn/list permission → BLOCKED pending the beta access request; local Docker runner tested as the development alternate, D-024: fresh snapshot, network none, read-only, env cleared, timeout kill, judged outside).

**Work:** Map tested SDK calls to prepare/run/cancel/artifacts; pin image, keep launcher outside editable app source. Verify fresh state, network/resource controls and remote-operation lifecycle.

**Acceptance/evidence:** Bounded real command/input-output run with IDs/artifacts; oracle absent from candidate; timeout/network/cleanup observed. Decide tested alternate if beta access fails.

**Scope/cut line:** Mocks enable development only; isolation cannot be dropped.

## B-06 — Typed records, jobs and events · P0

**Owner:** Ravi. **Dependencies:** B-02/B-03. **Target:** 6 Oct. **Status:** IN_PROGRESS (5 Oct: leases, CAS transitions, ordered resumable events + SSE, idempotent POST, immutable check results/artifacts, evaluator-only verdicts; owner-mismatch denial pending B-13; worker lease processing pending Day 4).

**Work:** Implement strict v2 domain schemas, SQLite ownership/leases/transitions, action budgets and resumable SSE. Persist remote IDs and reservations before follow-up work.

**Acceptance/evidence:** One lease per run, no duplicate POST action, restored snapshot agrees with events. Candidate records cannot write verdicts; owner mismatch denied.

**Scope/cut line:** Single-instance durable store; defer distributed scheduling.

## B-07 — Immutable intake, state graph and baseline · P0

**Owner:** Ravi. **Dependencies:** B-03/B-05/B-06. **Target:** 7 Oct. **Status:** DONE (7 Oct: intake limits/path validation, AST definitions/imports/calls, declared contract/check links, canonical graph hashing, dynamic feature coverage detection, baseline execution and artifacts saved).

**Work:** Hash approved source, parse supported AST forms, add reviewed typed manifest edges and coverage issues. Run visible baseline in isolation and map source changes to nodes.

**Acceptance/evidence:** Declared route/helper/worker links resolve; unknown dynamic edge is visible; stale source blocked. Graph hash and baseline artifact saved.

**Scope/cut line:** AST/SQLite and compact list; graph database/visual polish optional.

## B-08 — Impact, current context and bounded planner · P0

**Owner:** Ravi. **Dependencies:** B-04/B-07. **Target:** 8 Oct. **Status:** DONE (8 Oct: reverse callers/contracts/checks traversal, deterministic ordinal risk reasons, global integrity checks inclusion, hash-linked bounded context, real live NVIDIA Nemotron-3-Nano diagnosis with format repair, falsifiable probe execution, action persistence and audit events).

**Work:** Reverse-traverse changed callers/contracts/checks; apply deterministic risk reasons; build bounded hash-linked context. NVIDIA proposes at most two falsifiable hypotheses and named probes.

**Acceptance/evidence:** Probe returns relevant evidence; selected checks include mandatory integrity; missing critical mapping blocks. Delayed stale action cannot apply.

**Scope/cut line:** No universal graph or calibrated risk probability.

## B-09 — Restricted patch authoring/import · P0

**Owner:** Ravi. **Dependencies:** B-08. **Target:** 9 Oct. **Status:** DONE (9 Oct: base hash enforcement, app/* allowlist, line/byte ceiling enforcement, protected-file denial, clean candidate workspace patch application, canonical MC-01 and AC-01 repair diffs).

**Work:** Implement provider-neutral diff record and validated patch proposal. Enforce base hash, app-path allowlist, line/byte ceilings and protected-file/mode restrictions.

**Acceptance/evidence:** Useful AC/MC diff applies to intended source; protected/wrong-base/oversized patch rejected before code execution. Save original/candidate hashes.

**Scope/cut line:** External product adapters P2; neutral schema stays.

## B-10 — Fresh independent acceptance gate · P0

**Owner:** Ravi. **Dependencies:** B-03/B-05/B-09. **Target:** 9 Oct. **Status:** DONE (9 Oct: independent acceptance gate, trusted external evaluator computing expected values, MC-01 and AC-01 repairs VERIFIED, clean-service untouched VERIFIED, shallow candidate REJECTED, forged PASS prevented, missing check yielding INCONCLUSIVE, budget exhaustion stopping, evidence saved in artifacts/acceptance_gate/).

**Work:** Execute approved candidate fresh; trusted evaluator computes expected behavior externally and stores check/verdict. Required failure/unknown/missing result cannot pass.

**Acceptance/evidence:** Two distinct repair families pass; shallow invalid candidate rejected; clean untouched passes; forged PASS/protected edit rejected. Save check artifacts.

**Scope/cut line:** Acceptance authority and required-check integrity never cut.


## B-11 — Bundle export and independent replay · P0

**Owner:** Ravi. **Dependencies:** B-10. **Target:** 10 Oct. **Status:** DONE (10 Oct: canonical manifest, constraints, state, coverage, decisions, trajectory, candidate diff, source-manifest, checks, mutations, environment, usage, and Markdown reports in ZIP bundle; non-executing SHA-256 cryptographic manifest verification; secret exclusion and safe archive traversal denial; isolated temporary container/workspace replay with check re-evaluation and verdict match assertion; tampered diff detection blocks replay; REST endpoints and standalone CLI replayer scripts; evidence in artifacts/bundles/ and artifacts/replay/).

**Work:** Export canonical version/hash manifest, constraints, graph/gaps, decisions/actions, diff, results and REPLAY guide with safe paths/ownership and omissions.

**Acceptance/evidence:** Fresh isolated replay matches stated checks; tampered artifact fails nonexecuting validation; secrets/truth excluded. Preserve bundle/replay record.

**Scope/cut line:** Readable static report first; decorative export formatting optional.

## B-12 — Integrated developer-facing UI · P0

**Owner:** Ravi. **Dependencies:** B-06/B-10/B-11. **Target:** 11 Oct. **Status:** DONE 12 Oct (connected curated live/mock flow, real graph/impact/events, readable bounded diff, explicit independent verify, gate-versus-test-strength separation, authenticated evidence download and replay; responsive/keyboard semantics build and lint clean. Automated headless screenshot capture was attempted but did not produce an artifact, so no screenshot is claimed).

**Work:** Connect curated examples, constraint review, impact, events, diff/verify, separate verdict/test strength and export to actual API records.

**Acceptance/evidence:** Faulty/clean/rejected paths work from browser with readable failure and next action; no hardcoded success or arbitrary public intake.

**Scope/cut line:** Affected-path list before interactive graph.

## B-13 — Errors, reconnect, ownership and accessibility · P0

**Owner:** Ravi. **Dependencies:** B-12. **Target:** 12 Oct. **Status:** DONE 12 Oct (local capability owner required on every audit/patch/bundle route; owner-filtered listing; patch-parent binding; localStorage audit/cursor restore; header-authenticated resumable SSE; idempotent create recovery; explicit lifecycle/verdict/UNKNOWN/error states; two-phase remote cancel with worker reconciliation; Docker readiness timeout no longer aborts API startup).

**Work:** Restore audits after reload, resume SSE, handle provider/timeout/budget/cancel states and safe artifact access. Check keyboard/mobile core path.

**Acceptance/evidence:** Reconnect causes no duplicate spend; pending cancel reconciles; cross-owner routes denied; unknown check stays explicit.

**Scope/cut line:** Keep core navigation/readability; optional animation cuts first.

## B-14 — Decision ledger and dependency freshness · P1; source-hash guard P0

**Owner:** Ravi. **Dependencies:** B-07/B-08. **Target:** 13 Oct. **Status:** DONE (12 Oct: reviewed/proposed SQLite ledger with server-computed file/source/contract/graph hashes; changed/deleted dependency invalidation; sticky stale state; current-reviewed-only context rebuild; late provider response and old-context patch rejection; API, bundle and UI stale/version/overhead detail; three stale and three fresh transition tests; F6 preparation artifact).

**Work:** Record reviewed/proposed decisions with dependencies/evidence/revisit triggers. Invalidate changed/deleted hashes, exclude stale decisions and rebuild context.

**Acceptance/evidence:** Relevant change marks stale; unrelated control remains current; late proposal rejected. Save F6-ready development transitions.

**Scope/cut line:** If cut, retain P0 source/contract hash freshness and state that rich ledger is absent.

## B-15 — Trajectory stopping and one recovery · P1; hard stop/caps P0

**Owner:** Ravi. **Dependencies:** B-06/B-08. **Target:** 14 Oct. **Status:** DONE (13 Oct: `trajectory-fingerprint-v1` canonical action/failure/semantic-observation fingerprints; two-repeat no-progress stop; frozen development W8 source with four stalls and four progress controls; one atomic fresh-context `narrow_failure_probe` recovery preserving original counters/limits; second recovery stall blocks; owner-scoped API/UI state; executed mock recovery recorded separately from synthetic classification).

**Work:** Canonicalize action/failure fingerprints; detect two no-progress repeats. Preserve improving controls; add one fresh-context changed-strategy recovery within original limits.

**Acceptance/evidence:** Stall stops, progress does not; second stall ends blocked; counters never reset. Save synthetic trace labels separately from actual recovery runs.

**Scope/cut line:** Simple stopping P0; rich replan optional P1.

## B-16 — Trusted mutation test-strength probes · P1

**Owner:** Ravi. **Dependencies:** B-10; stable P0. **Target:** 15 Oct. **Status:** DONE (13 Oct: twelve `development-semantic-v1` trusted templates, three per API/amount/caller/idempotency family; exact-anchor validation; max-three fresh branches plus accepted baseline under `max_executions`; immutable run/results; explicit killed/survived/invalid/skipped/unknown counts; optional policy; API/UI/bundle integration; clean-control development run killed 2 and exposed 1 tenant-key survivor while preserving the candidate hash).

**Work:** Author semantic templates with external oracles, validate behavior changes, run max three relevant fresh branches and store killed/survived/invalid/unknown results.

**Acceptance/evidence:** Weak check set exposes survivor; invalid syntax is not killed; candidate remains unchanged. Strength/policy explicit and execution budgets respected.

**Scope/cut line:** If cut, NOT_RUN with no adequacy claim.

## B-17 — Integrity and execution hardening · P0

**Owner:** Ravi. **Dependencies:** B-09/B-10/B-13. **Target:** 16 Oct. **Status:** DONE 14 Oct (pulled forward; commit `093353e`, second pass in the Day 15 change). `INTEGRITY_REPORT_v1.md` with its addendum, `backend/tests/test_security_day13.py` and `test_hardening_day15.py`; `artifacts/integrity/day13_integrity.json` records forged-PASS, missing-output, hidden-truth, secret-exclusion and live Docker runtime-isolation controls as PASS. Limitations kept open: hosted Nebius remote termination is untested (no sandbox access) and the owner header is not production identity.

**Work:** Run prompt-injection, protected-edit, fake-PASS, stale-graph, secret, traversal/ownership and actual network/resource/termination negatives.

**Acceptance/evidence:** Every exposed trust control has tested evidence; failing capability blocked/narrowed. Save sanitized test report and remediation.

**Scope/cut line:** Never substitute documentation for backend enforcement.

## B-18 — Freeze evaluation assets and scope · P0 reduced; P1 full

**Owner:** Ravi. **Dependencies:** B-03/B-10/B-17. **Target:** 17 Oct. **Status:** DONE 14 Oct (pulled forward). `repair-r12-v1` (12 opaque held-out cases: 8 faulty, 4 clean; four source styles), `gate-v12-v1` (12 fixed candidates: 4 valid, 8 invalid, all smoke-passing), `graph-g8-v1`, `freshness-f6-v1`, `trajectory-w8-v1` and `mutants-m12-v1` manifests frozen under `backend/fixtures/heldout/`, hash-locked in `truth.lock.json` and validated externally; R6/V6 fallback subsets predeclared by id (D-027).

**Work:** Validate and freeze R12/V12/G8/F6/W8/M12 assets or explicit R6/V6 subset, reference repairs, private truth and manifests. Choose based on implemented scope/budget.

**Acceptance/evidence:** Original/reference/clean semantics validated; unique hashes; no truth leakage. Save suite commit and chosen counts before final runs.

**Scope/cut line:** No hidden denominator changes or post-result fixture replacement.

## B-19 — Fair baseline harness and configuration freeze · P0 reduced; P1 full

**16 October follow-up:** Historical local configuration v1 was frozen for its committed core/image, but the Linux output-directory compatibility fix changes `runtime_code_hash` and the Vercel image differs. Keep v1 immutable, commit/review the deployment changes, then create a new release configuration before final trials. Three live development records exist with mixed outcomes; none is a final held-out measurement.

**Owner:** Ravi. **Dependencies:** B-18/B-04/B-10. **Target:** 20 Oct. **Status:** IN_PROGRESS (15 Oct, pulled forward). Implemented in `benchproof.trials`: B0 visible gate, one NVIDIA repair agent shared by B1 (visible tests and raw probe only) and B2 (plus graph context, protected feedback, evidence-based confirmation, gate acceptance and repeated-candidate stop), shared hard limits, balanced predetermined R12/R6 plans, sealed write-once trial records with INTERRUPTED handling, a fresh frozen-evaluator final run per trial, and the truth-based summary (`scripts/run_trials.py`, `scripts/summarize_trials.py`); a hand-counted artificial record set matches the script (`tests/test_trials.py`). `backend/evaluation/eval-config-v1.json` is a **candidate** configuration (`210affd887e92863…`): it cannot be `frozen` until the runtime source is committed, and the plan sequences the final freeze after the B-20 deployment path. Pinned model present in the live catalog 15 Oct (listing only); the official price page could not be read, so the price snapshot stays `NOT_RECORDED` and cost unknown. No live repair trial has been run.

**16 Oct update:** The runtime is committed at `ad1955703ccc484e380f40edab33afe764beb3ba`; the local evaluation configuration is `frozen`, with unchanged identity `210affd887e92863…` and pinned Docker digest. Verification reports no difference. This identifies the local core, not a frozen deployed release. Price/credit reserve review and final held-out trials remain pending. Three live development records preserve an accepted amount repair, an API repair stopped by truncated JSON, and a clean case with a failed model call but independently VERIFIED unchanged source.

**Work:** Implement B0 smoke, B1 same agent minus assurance and B2, shared final evaluator and immutable trial/summary records. Freeze model/prompts/thresholds/image/budgets.

**Acceptance/evidence:** Small manual record counts match script; information/limits fair; setup/version/price snapshot saved. Failures remain assigned.

**Scope/cut line:** Optional component ablation/external products cut before core measurement.

## B-20 — Hosted product, persistence and recovery · P0

**Owner:** Ravi. **Dependencies:** B-11/B-13/B-17. **Target:** 19 Oct. **Status:** IN_PROGRESS (16 Oct: public Vercel Hobby deployment `https://benchproof.vercel.app`; persistent Sandbox/Drive, private origin, Docker isolation/OOM enforcement, stop/resume with fresh replay, live NVIDIA diagnosis, access denial and fresh-browser create/verify/export/validate/replay/download/reload passed). Independent backup/restore, full judging-period quota/credit reserve and unattended availability remain open. Nebius Sandboxes access and the laptop are not dependencies of this cloud route. See `VERCEL_DEPLOYMENT.md`; ngrok remains an optional fallback.

**Work:** Deploy exact working build with HTTPS, supervised worker, durable data, public curated mode, quotas and server secrets. Restore backup in separate location.

**Acceptance/evidence:** Incognito faulty/clean/rejected/export journeys pass; restart/reconcile and restore tested; access lifetime/credits documented.

**Scope/cut line:** No ephemeral-store assumption; choose tested host.

## B-21 — Frozen trials, separated analysis and replay · P0 reduced; P1 full

**Owner:** Ravi. **Dependencies:** B-19/B-20. **Target:** 21–23 Oct. **Status:** TODO.

**Work:** Run all assigned B0/B1/B2 trials and selected assurance suites, preserve failures/usage, inspect accepted diffs and replay preselected exports.

**Acceptance/evidence:** Actual counts/denominators link to immutable records; limitations and null results retained; evaluated/deployed versions reconciled.

**Scope/cut line:** Report explicit reduced scope rather than invent missing measurements.

## B-22 — User observation and product fixes · P1; critical UX fixes P0

**Owner:** Ravi. **Dependencies:** B-12. **Target:** 18/23 Oct. **Status:** DONE 14 Oct for the self-review scope (pulled forward). No volunteer tester was available, so no user study is claimed; the disclosed self-review found and fixed one core readability defect (a proposed diff read `APPROVED` before any gate ran; it is now `PENDING` until the protected gate judges it) and added the bounded skill catalog (`skills-v1`: twelve slash skills with server-computed availability, cost class and blocked reason, exposed at `GET /api/v1/skills` and `GET /api/v1/audits/{id}/skills`) with a Ctrl+K/`/` palette in the UI; the recommended next action now names its skill. A later volunteer session (23 Oct follow-up) can still be recorded here.

**Work:** Observe voluntary task sessions if available; record consent/confusion/completion without coaching. Fix the highest-value core decision/readability issue.

**Acceptance/evidence:** Actual session count and change evidence; no fabricated user study or unsolicited messages. Core journey understandable.

**Scope/cut line:** Self-review disclosed if volunteers unavailable.

## B-23 — Clean-clone release, license and docs · P0

**Owner:** Ravi. **Dependencies:** B-17/B-20/B-21. **Target:** 24–25 Oct. **Status:** IN_PROGRESS (16 Oct: top-level Apache-2.0 LICENSE/NOTICE added following the existing plan; README, judge guide and hosting instructions updated; direct dependency license metadata recorded). Clean-clone setup, transitive/model/image rights review, public license detection, tag and three successful live rehearsals remain open.

**Work:** Add actual LICENSE/notices, tested setup, accurate judge guide and results/limits. Clean clone the release, run appropriate checks and tag feature freeze.

**Acceptance/evidence:** Setup/replay/access work from final docs; claims match implementation; terms/inventory complete; three live rehearsals recorded.

**Scope/cut line:** After freeze only necessary fixes; functional ones need affected reruns.

## B-24 — Genuine short demo video · P0

**Owner:** Ravi. **Dependencies:** B-23. **Target:** 26 Oct. **Status:** TODO.

**Work:** Record real constraint/impact/rejection/repair/gate/export footage; disclose cuts/replay, caption and remove secrets/unsupported numbers.

**Acceptance/evidence:** Public video below three minutes with incognito playback and genuine run IDs; file/link retained.

**Scope/cut line:** Omit extra P1 screens before hiding the complete loop.

## B-25 — Final feedback and entry materials · P0

**Owner:** Ravi. **Dependencies:** B-21/B-23/B-24. **Target:** 27 Oct. **Status:** TODO.

**Work:** Write actual Nebius/NVIDIA observations; finalize entry from measured scope, fill required links/testing instructions and recheck live rules/form.

**Acceptance/evidence:** No achievement placeholders or unmeasured product rankings; all required fields and public links reviewed.

**Scope/cut line:** Future features remain explicitly future work.

## B-26 — Submission and access preservation · P0

**Owner:** Ravi. **Dependencies:** B-25. **Target:** 28 Oct 20:00 IST; buffers 29–30 Oct. **Status:** TODO.

**Work:** Ravi completes actual entry action, verifies submitted status, retains confirmation and keeps the tested version accessible through judging.

**Acceptance/evidence:** Submitted status/time/URL and incognito links saved; credit/host reserve and post-submit monitoring plan established.

**Scope/cut line:** A draft is not submitted; no silent replacement of submitted behavior.

## B-27 — Optional adapters, ablations and broader cases · P2

**Owner:** Ravi. **Dependencies:** All P0 complete; time/credits remain. **Target:** Only before freeze. **Status:** TODO.

**Work:** Consider one accessible external-agent adapter/trial, graph ablation, second NVIDIA tier or permissioned case. Use research benchmark protocol and rights checks.

**Acceptance/evidence:** Configured versions/access, fair trials and actual evidence; unrun tools stay NOT_RUN. Optional work does not delay release.

**Scope/cut line:** Cut all of this before any P0 or submission buffer.

## Daily board entry

| Ticket | Status | Commit | Acceptance artifact | Blocker/next action |
| --- | --- | --- | --- | --- |
| [ID] | TODO | None | None | Earliest unmet dependency |

When a scope decision changes a ticket, update its acceptance and linked docs rather than checking off a removed requirement. Record NOT_RUN/unsupported for omitted benchmark/features. Keep superseded decisions and failed attempts inspectable.
