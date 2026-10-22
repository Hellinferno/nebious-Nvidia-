# BenchProof coding-agent build plan

Version: release-readiness revision, 22 October 2026 (IST).
Status: v3 is deployed and public infrastructure/browser verification passes. A separately authorized staging feature run passes after one bounded model revision at 4,096 output tokens; the owner approves matching production output without increasing daily limits. Earlier failed runs remain failures. Broader evaluation and owner submission gates remain open; no fresh production inference is claimed by the rollout checks.

## Current evidence and scope

- Latest v3 live gate, 22 October: task `coding-5e6be4746ce7479b` reaches **REVIEW_READY / CHECKS_PASSED** after one failed annotation candidate and a genuine model revision. Three calls / two edits / four isolated executions / 11,900 tokens; all six candidate and fresh final checks pass, original project/tests unchanged. Both edits use physical-line schema v2. This is one already-seen sample, not first-pass success, a held-out benchmark or a matched comparison. [Separate result](verification/policy-v3-live-2026-10-22-results.json). All three authorized calls are consumed; no additional inference is authorized.
- V3 runtime checks: **663 isolated backend tests + three separate Docker integrations, frontend 29 and deployment 30 pass**; lint/build, saved replay, retained-result desktop/mobile/export/reload pass. The extra deployment regression excludes root `.codex-*` private/cache directories from uploads. Policy pinning, syntax rejection, protected paths/limits and fail-closed truncation remain. Bounded exhaustion has its own message. The [v3 identity](verification/generation-policy-v3.json) is the historical pre-live snapshot; the separate live record supersedes its NOT_MEASURED status without overwriting it.
- Earlier resumed live gate: task `coding-62c3821cedc44977` uses v2, not v3: first candidate repeats the annotation NameError; revision double-encodes newlines and fails syntax. Result BLOCKED, **three calls / two edits / three isolated checks / 10,530 tokens**, no final pass. Actual bill is unknown. Shared quota reserved three calls/four checks conservatively; no unused reservation refunded. Production stayed at 2,048 during that run. [Separate failed result](verification/policy-v2-live-2026-10-22-results.json); that authorization is consumed.
- Live demo: https://benchproof.vercel.app. Deployment `dpl_4PGB22kBveDfE3obV57FjD25zSfx`; trusted runtime `517e43f650c6e7575bd5e7a198dc4dd77d56be68032050164702b42123831a3d`. Exact rollback/private backups, actual worker 4,096 configuration, isolation/OOM enforcement, stop/resume, public cold checks and desktop/mobile draft/export/reload pass with zero rollout inference. Daily limits and November 30 admission deadline stay unchanged. [Rollout record](verification/policy-v3-rollout-2026-10-22.json); source publication is recorded separately by Git.
- Implemented: owner-scoped project/task storage, leased coding worker, reviewed plans, isolated candidate checks, bounded revisions, checkpoints, export, browser-local profiles, instruction-only skills, two reviewed harnesses and read-only documentation MCP.
- Earlier 21 October suite: 635 passed, three Docker cases skipped and passed separately. The earlier fresh locked-dependency run passed 631; later source tests account for the current 663 above. These are scoped test results, not a model benchmark or another fresh dependency install.
- Earlier production inference acceptance: a real browser task with a pinned skill, single-pass harness and documentation MCP snapshot reached REVIEW_READY: two model calls, one patch, three isolated executions, unchanged original project, ZIP download and reload verified. See [RELEASE_REHEARSAL.md](RELEASE_REHEARSAL.md); this public sample with agent-assisted plan review is not a held-out benchmark or user study. Current v3 infrastructure/browser acceptance is separate from its staging model evidence.
- The corrected 2:18.28 video and genuine earlier inference/patch evidence exist; public YouTube upload and owner review remain. The six-task evaluation uses scripted gold answers and is not live-model performance. The additional public two-case batch matched one expected outcome: the clean control stopped untouched, while the feature failed. Its separately approved bounded follow-up also failed. See [verification records](verification/README.md); neither failure is removed from the record.
- Detailed audit: `artifacts/remaining-audit-20261020/REPORT.md`. Release evidence: [VERIFICATION.md](VERIFICATION.md).

## Ordered execution plan

| ID | Priority / status | Work | Completion gate |
| --- | --- | --- | --- |
| R-01 | P0 · DEPLOYED / VERIFIED | Unittest-only intake, owned task creation, legacy project admission/action reservation and executor dispatch now reject unsupported profiles. Invalid legacy queues terminate BLOCKED without spending or holding the active slot. | Focused regressions, complete 631-pass isolated suite and current production acceptance pass. |
| R-02 | P0 · DEPLOYED / VERIFIED | Transactional 100-project / 16 MiB payload admission plus database/free-disk reservation checks for new projects/tasks. Retention policy explicitly avoids automatic deletion. | Cross-owner/concurrent limits, encoded-byte/free-space boundaries, probe failures, idempotent replay, API denials and preserved task snapshots pass. See DATA_RETENTION.md; admission is not a hard total-disk quota. |
| R-03 | P1 · PARTIAL | CLI updated within major; scoped compatible patches remove critical/moderate advisories. Remaining 23 high development-tool advisories require upstream or separately validated major fixes. | Deployment/toolchain tests, production build and CLI smoke pass; production-only npm audit is zero. See DEPENDENCY_REVIEW.md; no forced major replacement. |
| R-04 | P1 · TECHNICAL GATES PASS / OWNER REVIEW OPEN | Setup/runtime docs, worker opt-in example, C-10 status, export wording and retention policy corrected. Actual MP4 narration/embedded subtitles corrected; dated current-rehearsal still added. | Fresh independent clone of `7b7349a`: locked dependencies, editable install, pip check, API/worker/UI launch and desktop/mobile browser pass with zero paid/candidate actions. Corrected 2:18 video decodes and captions match. Owner final video/rights review remains; local real-Docker execution is not claimed by the no-spend clone smoke. |
| R-05 | P1 · DEPLOYED / PUBLIC ACCEPTANCE PASS | Focused/full isolated tests, Docker integration, package, mocked browser flows, private WAL-consistent backup, exact rollback package, explicit idle upgrade and restart/public checks pass. Source publication follows verified acceptance. | 631 backend + three separate Docker cases, 29 frontend, 23 deployment tests; browser 15/17/9 assertions; public audit `audit-646e9823447f`. Initial Linux lockfile failure retained; missing optional peers fixed and actual deployment build passed. |
| R-06 | P1 · STAGING FEATURE PASS / BROADER EVALUATION OPEN | Preserve all original public/control/follow-up failures and successful customized bugfix. V3 `coding-5e6be4746ce7479b` completes the same public BankAccount feature after one bounded model revision with six fresh final checks passing. | Separate v3 run: 3 calls / 2 edits / 4 executions / 11,900 tokens at output 4,096. Bill unknown, no SDK retries or further inference authorization. Both edit responses exceed 2,048 tokens; the owner explicitly approves 4,096 for production, with daily limits unchanged. This does not establish success at 2,048 or alter the original batch's 1/2 outcome. Volunteer sessions and held-out comparison remain open. |
| R-07 | OWNER / ACCOUNT GATE | Confirm credit reserve, judging-period access, rights/attribution, public YouTube upload and actual competition submission. | Submission closes 30 October at 22:30 IST; official judging is 1–15 December Pacific time. Coding admission currently ends 30 November at 23:59 IST, so the read-only judging check fails. No hosting deadline/limit changes approved or applied. Rights inventory is partial; actual submitted entry URL/status and public YouTube URL are missing. |

Prior approval to publish only after tests and browser verification still applies. The 21 October reports/checks were published as `9af885b`; actual Git history determines later publication. Rollout and source publication are separate gates and must not force-push over another change. The two separately resumed v2/v3 staging authorizations are consumed; no further paid call is authorized. Account access/user participation require actual evidence, not a DONE label.

## Release rules and cut lines

- Keep Python/unittest, the fixed Docker boundary, protected imported tests and lower-only budgets. Disable unsupported pytest; implementing a new runner is not required for this release.
- Existing shared daily mutation and provider/execution limits remain. New storage admission complements them; client-generated owner capabilities are not production identity authentication.
- Never run candidate/legacy fixture tests directly on the laptop. Full legacy/project suites execute inside dedicated non-root, networkless cloud test containers; socket-dependent tests run separately through the trusted Docker boundary.
- No forced dependency upgrades, paid hosting upgrade, automatic deletion, arbitrary MCP/harness plugins or claim of unlimited free hosting.
- Use layered evidence: implemented, locally tested, cloud-tested, deployed, live-model measured and submitted are separate states. C-09 and final C-10 acceptance remain incomplete until their actual gates pass.
- Do not claim a competition win, signature verification, superiority over other coding agents or a full MCP implementation without supporting work and evidence.

## Historical 17 October planning baseline

The material below preserves original requirements, targets and early acceptance. Statements such as “not deployed”, “worker not implemented”, and “first implementation session” describe that historical baseline, not current product status. Use the R-series plan above for current execution order.

### First implementation increment — 17 October

- C-01: strict provider completion validation, distinct safe failure codes, recorded rejected-response usage and atomic diagnosis reservations are implemented locally. Truncated JSON and missing claims are no longer guessed into valid diagnoses; failed attempts consume the original action allowance. Interrupted in-flight attempts block another call rather than silently repeating spend.
- One explicitly approved NVIDIA generation produced a genuine source-bound patch: 971 prompt + 1,183 completion = 2,154 tokens, 5,068 ms; monetary cost/reserve UNKNOWN. The plan for this acceptance sample was operator-scoped, not model-generated. No second inference request or canned replacement.
- The existing cloud API rejected the original MC-01 on `amount-boundary`, then accepted that exact model diff under its protected isolated checks: audit `audit-1ba1aab76133`, patch `patch-a2b556ff90cf`. Evidence: `artifacts/coding/c01-live-20261017-1/`. This imports a CLI-generated patch into the current cloud gate; it is not the completed app-connected C-03 loop.
- C-02 has initial `coding-brief-v1`, `coding-plan-v1` and `coding-edit-v1` primitives in [coding runtime notes](backend/benchproof/coding/README.md). Durable coding-task/project/action/usage tables, queued worker and new endpoints remain TODO. The old heartbeat helper is still not a coding-task worker.
- New backend code is not deployed. The original public HTTP 422 cause was not captured and remains unconfirmed; synthetic schema regressions are not a retroactive diagnosis. Local Docker is stopped; the isolated candidate checks above ran in the existing cloud runtime, not on the laptop. Remaining C-02–C-10 work retains its acceptance gates.

## 1. Product commitment

Build a web-based coding agent for small Python projects: **give it a task, watch it write and test real code, then review a tested patch**. Reliability features support this coding workflow; the assurance dashboard is no longer the primary product.

Primary audience hypothesis: developers fixing a reproducible bug or implementing a small feature in an existing Python service/module. Validate with real users; public issue reports are not customer validation. Keep the BenchProof name and the existing Vercel deployment path. NVIDIA inference stays on Nebius Token Factory; candidate execution stays in isolated cloud containers. No local GPU or always-on laptop is required by the current hosting design.

Research basis: [17-product landscape and five problems](CODING_AGENT_RESEARCH_2026-10-17.md). The opportunity is less supervision and more dependable delivery on a supported task, not a claim that memory, testing or rollback is unique.

### Main user journey

1. Open a sample project or select supported, non-sensitive project files.
2. Describe the task and confirm editable paths, required checks and limits.
3. Review a short model-generated plan before code changes.
4. Start the agent: it inspects source, generates actual edits, runs tests and revises failures within limits.
5. Follow concise progress, file changes, actual command output and usage.
6. Pause/resume/cancel safely; inspect the final diff and which requirements have evidence.
7. Download the patch and run report, or discard the task changes without losing the original project.

No automatic push, merge or modification of the user's local repository. Download/apply locally is a deliberate user action. No canned repair may masquerade as model generation.

## 2. What exists, and what does not

Code inspection for this plan is not a fresh validation run. Prior test/deployment results remain historical evidence for their recorded versions.

| Area | Current evidence / limitation | Build action |
| --- | --- | --- |
| UI and cloud | React/TypeScript/Vite UI, same-origin Vercel gateway, named Sandbox/Drive, browser checks | Reuse infrastructure and visual system; introduce a task-centered workspace. |
| Provider | `backend/benchproof/providers/__init__.py` calls Token Factory with retries disabled | Reuse; improve bounded output handling and preserve provenance/errors. Recheck the configured model and prices before live work. |
| Real repair logic | `backend/benchproof/trials/systems.py` contains an offline model-driven repair loop | Extract suitable production logic without changing historical trial prompts/configuration or coupling tasks to trial fixtures. |
| Public repair | `frontend/src/App.tsx` currently submits `CANONICAL_DIFFS` for selected cases | Remove reference repairs from the primary live flow; retain clearly labeled examples only in the legacy assurance view. |
| Execution | `DockerRunner.run_observation` and `observe_invoice.py` are invoice-specific | Add a project test-runner profile; existing fixture execution is not a general-purpose runner. |
| Worker | `backend/scripts/start_worker.py` writes heartbeats; it does not claim/process queued jobs | Implement actual durable task execution, ownership leases and recovery. A live heartbeat is not evidence of agent progress. |
| Projects | Existing intake is local fixture-oriented and restricted to `app/`; public audits require a fixture ID | Add owner-scoped project snapshots and constrained browser file intake. No arbitrary URL cloning. |
| Patch policy | Existing parser limits paths/size and refuses file creation/deletion metadata | Preserve old fixture rules. Version a separate project-edit policy before supporting approved new `app/` modules. |
| Tests and verdicts | Protected invoice checks have known expectations | Do not apply invoice truth to user projects or call ordinary project tests proof of all requirements. |
| API transport | Gateway currently allows `/api/v1/`, caps bodies at 64 KiB and upstream requests at 180 seconds | Keep enqueue/control requests short; add a deliberately bounded project-intake limit and resumable progress reads. |
| Hosting | Sandbox session deadlines and a shared 60-action/day demo cap exist | Add job-level admission and provider/execution accounting. One enqueue cannot become an unlimited unmetered job. |
| Release | Historical v1 configuration no longer matches the Linux-fixed runtime; diagnosis 422 and repair truncation are preserved failures | Reproduce failures first. Use a new versioned release/evaluation identity; never overwrite historical freezes. |

## 3. MVP scope and cut lines

### Required for this release

- One real NVIDIA-powered agent; no multi-agent framework required.
- Small Python 3.12 projects using a documented layout: editable `app/`, protected imported `tests/`, and an approved runner profile. Support `unittest` first; enable a pinned `pytest` profile only after its image/collection behavior passes tests.
- Bug fixes and small feature changes in existing modules. Creation of explicitly approved new `app/` modules is a separate policy gate; no deletion/rename in the initial release. No unrestricted scaffolding or dependency upgrades.
- Source browser, task brief, editable plan, plan approval, live activity, readable diff, real test output and patch download.
- Persisted instructions/decisions, bounded repair, checkpoint restore, pause/resume/cancel, usage limits and evidence-linked status.
- One active coding task globally on the small public deployment. Clear busy/limit responses; no assumption of horizontally scaled jobs.
- Small user-selected file sets as well as samples. Samples alone are an internal milestone, not the completed project-input feature.

### Deliberately excluded

Private GitHub OAuth, arbitrary repository URLs or archives, arbitrary shell commands, network/package installation from user files, databases/production credentials, JavaScript/browser-app development, full IDE editing, code completion, multi-agent swarms, mobile remote control, automated deployment and automatic merge.

Generated regression tests are useful next work, not a shortcut to trust: proposals remain separate from imported protected checks until explicitly reviewed. Extra features cannot delay the real coding loop, safe execution or release work.

### Proposed starting limits, not current capabilities

| Resource | Initial target / rule |
| --- | --- |
| Project intake | 20 UTF-8 text files, 24 KiB/file, 128 KiB total; actual encoded JSON body at most 256 KiB. Enforce both raw and encoded sizes. |
| File selection | Portable relative paths, no links, path traversal, case collisions, dot-secret/config files, binaries or generated/dependency directories. No filesystem path supplied by the client becomes a host path. |
| Model context | Focused source/log selection with a fixed byte ceiling; expose omitted files/coverage rather than silently truncating required context. Calibrate the ceiling before live acceptance. |
| Model calls | At most 4 per task initially, including plan, edits, revisions and any format correction. No hidden SDK retry or automatic paid retry. |
| Model output | Calibrate a bounded 2,048–4,096-token allowance with the selected model. `finish_reason=length` is an incomplete response, not an accepted edit. Freeze the tested setting. |
| Changes | At most 2 candidate patch attempts, 3 editable files and a separately validated size/line cap. Plan changes require reapproval. |
| Tests | At most 4 executions including baseline, candidate attempts and fresh final check; 30 seconds/execution initially. Missing/skipped required checks or zero collection cannot pass. |
| Task | At most 300 seconds of active work; pause does not reset consumed time/counters. Reject work without a sufficient Sandbox lifetime window. |
| Container | Retain network denial, read-only source/launcher/root, bounded scratch/output, non-root user, 256 MiB memory/swap, 1 CPU, 64 pids and timeout termination. Measure any profile incompatibility instead of removing controls. |
| Credits | Operator-configured daily provider-call/token/execution budgets and a reserve for judging. Actual remaining credits and affordable limits are unknown until checked. |

Token estimates are not hard token/currency guarantees. Use a verified tokenizer or an explicitly conservative reservation scheme, reconcile provider usage, and retain unknown-call reservations. Do not present the current characters/3 heuristic as a proven upper bound. If monetary prices are unavailable, show usage and cost UNKNOWN.

## 4. Architecture and execution contract

```text
Task-centered React workspace
  -> short owner-scoped API requests through Vercel gateway
  -> FastAPI + SQLite task state / event log / durable action reservations
  -> one trusted task worker in the existing named Sandbox
       -> bounded Token Factory inference (server-side credentials only)
       -> validated edits -> immutable candidate snapshot
       -> fresh isolated project test container
       -> observed results -> bounded next action
  -> persisted diff, checkpoints, usage and evidence -> UI/SSE/download
```

### Production modules to introduce or adapt

Use small modules, not a new orchestration framework. Proposed responsibilities:

- `backend/benchproof/coding/`: task schemas/store, action engine, worker, context and checkpoints.
- `backend/benchproof/projects/`: validated project manifests, snapshots and source browsing.
- `backend/benchproof/execution/project_runner.py` and a trusted `backend/runner/launcher/` entry point: fixed test profiles and bounded collection.
- `backend/benchproof/api/coding.py`: new router, included by the existing app without changing legacy audit semantics.
- Frontend task workspace components split from the current monolithic assurance view. Reuse existing styles where appropriate.
- Deployment packaging/startup: explicitly include new assets/profiles, launch the real worker, retain persistence and identity checks, and update route/body/quota tests.

### Typed actions and trusted boundaries

The agent can request bounded `inspect_source`, `propose_plan`, `propose_edits` and `run_checks` actions. Trusted code validates/dispatches them. It cannot choose arbitrary subprocess strings, install packages, edit policy/tests, read secrets or grant itself acceptance.

Return complete contents for a small bounded set of approved files; build the diff deterministically and verify applying it reproduces those contents. Record model/response identity and source hashes. Treat repository text, model text and command output as untrusted data. Display source/logs/diffs as escaped text.

For normal projects, report **project command/check results**, not the stronger invoice `VERIFIED` claim. Imported tests are user-provided code, not a trusted oracle. Record their identity, collection, exit status and provenance; distinguish required checks, optional checks, unverified requirements and proposed generated tests. A command reporting success does not independently prove the task's correctness. Protected external expectations remain available for controlled examples and evaluation.

### Durable worker and interruption semantics

- A short start request creates/approves/enqueues work idempotently and returns a task ID. No model loop runs inside a browser request, FastAPI background task or Vercel function lifetime.
- The worker atomically claims one job with a lease and fencing token. Commit action status, reservations and events together. A stale worker cannot publish a later result.
- Persist the approved brief/plan, source identities, candidate revision, last completed action, remaining budgets and provider/container operation identifiers. Check cancellation and deadline before every next action.
- Pause at a safe action boundary. Do not start further work; retain partial progress and budgets. Resume validates source/plan/check identities and continues the next known-safe action.
- Record a paid call as in-flight before sending it. If a crash leaves its result unknown, keep its reservation, mark the action INTERRUPTED/UNKNOWN, and require an explicit bounded retry choice. Provider calls are not magically exactly-once.
- Cancel stops scheduling new calls, kills/reconciles candidate execution and ignores late model output for mutation. An already accepted provider request may still be billed; disclose that limit.
- Browser close/reload does not create a second task or reset limits. A stopped Sandbox cannot work in the background: resume must reconcile interrupted work, not claim uninterrupted execution.
- Admission must confirm enough remaining Sandbox lifetime before starting; the browser is not a keepalive guarantee. Refuse a job near a session/quota deadline.

### Proposed storage and API contract

Add versioned tables/records for projects, immutable source revisions, coding tasks, approved plans, actions/leases, executions, checkpoints and usage. Extend by migration; do not relabel old audits as coding tasks.

| Route family under `/api/v1/` | Planned responsibility |
| --- | --- |
| `projects` | Bounded file intake, owned listing, manifest and source retrieval. |
| `coding-tasks` | Create a task against a pinned project revision, brief, editable paths and runner profile. |
| `coding-tasks/{id}/plan` and `/approve` | Generate/retrieve plan; approve its exact revision and resource envelope before edits. |
| `/start`, `/pause`, `/resume`, `/cancel` | Idempotent control with explicit preconditions and no hidden paid duplicate. |
| `/events`, `/changes`, `/executions`, `/usage` | Owner-scoped resumable progress and actual observations; reads do not trigger inference. |
| `/checkpoints`, `/restore`, `/bundle` | Immutable task history, conflict-checked internal restore and sanitized patch/report export. |

Final schemas/route naming belong to C-02 before implementation. Keep the existing gateway `/api/v1/` boundary. Increase request size only for validated project intake; retain strict limits for ordinary controls. The API must also bound bodies before parsing, regardless of `Content-Length` claims.

Task lifecycle and check outcome are separate. Proposed lifecycle: DRAFT, PLANNING, AWAITING_APPROVAL, QUEUED, RUNNING, PAUSED, REVIEW_READY, BLOCKED, FAILED, INTERRUPTED, CANCEL_PENDING, CANCELLED. Time/budget/stall causes are explicit stop reasons. Check status is NOT_RUN, RUNNING, PASSED, FAILED, STALE or BLOCKED. REVIEW_READY is not automatic human acceptance.

### Project privacy and rollback

Keep the existing owner-capability boundary on every new route, artifact and event. It is a demo bearer capability, not verified account identity; per-owner quotas alone do not prevent abuse because owners can be regenerated. Enforce global hard limits, disk admission and bounded active jobs too. No private/sensitive project hosting or enterprise-auth claim in this release.

Do not upload `.env`, credentials or unrelated local files. Let users preview the manifest before sending source to the service/model. Common-secret screening is best effort, never a guarantee that source is secret-free.

Imported base files are immutable; patches target task snapshots. Restore changes the internal selected revision using a compare-and-swap check, never resetting a user's local Git repository. Preserve original bytes and file existence independently of normalized source identity. Any later local-apply helper needs base-hash conflict checks. Retention/cleanup policy, disk reserve and deletion/export semantics must be agreed and tested before public intake; never delete historical measurement evidence as routine cleanup.

## 5. Dependency-ordered implementation backlog

All coding-agent tickets started TODO at the planning baseline. Current state is recorded above and in the backlog. Existing completed assurance tickets are historical work, not automatically completed coding-agent tickets. A ticket is complete only with its stated artifacts/tests; deployed acceptance is separate from local completion.

| ID / target | Work and dependencies | Acceptance gate |
| --- | --- | --- |
| C-01 · 17 Oct | Reproduce diagnosis 422/output truncation using retained records and deterministic mocks; inspect configured provider behavior without blind retries. Confirm operator inference envelope before live calls. | Error codes distinguish transport, length and schema failures; malformed output never mutates code; one explicitly bounded live generation is demonstrated or the blocker is recorded. |
| C-02 · 17–18 Oct | Freeze development schemas for project/task/plan/action/execution/usage; implement owner-scoped durable state, idempotency and a real single-job worker. Depends on C-01's failure contract. | Duplicate start cannot spend twice; two workers cannot claim the same action; crash/lease recovery and paused/terminal guards pass. |
| C-03 · 18 Oct | Connect real generation to validated edits and existing isolated fixture execution for the first vertical slice. Depends on C-01/C-02; extract shared production logic without changing frozen trial identities. | User task -> actual model-written patch -> execution -> real test outcome -> reviewable diff. A deliberately rejected attempt feeds real observations to the bounded next attempt. Not the final general-project feature. |
| C-04 · 19–20 Oct | Add constrained project intake, manifest/versioning and generic `unittest` execution; add pinned `pytest` profile only if validated. Depends on C-02; integrate with C-03. | Two distinct non-invoice small projects run unchanged; invalid paths/secrets/common unsafe files, links, oversize bodies, unsupported dependencies and missing/zero tests fail clearly. Candidate code never runs on the host. |
| C-05 · 20–21 Oct | Run the agent on imported projects with focused context, reviewed plans and versioned project edit policy. Depends on C-03/C-04. | One bug fix and one bounded feature on different projects produce genuine diffs; imported tests/policy stay unchanged; stale bases and unauthorized/new paths are rejected. |
| C-06 · 21–22 Oct | Persistent task brief, source-bound facts, checkpoint restore, pause/resume/cancel, repeated-failure classification and durable budget enforcement. Controls are tested as they are introduced, not postponed until this ticket. | Restart continues known-safe work without repeating a paid action; uncertain calls stay uncertain; no budget reset; cancelled container termination reconciles; repeated identical failure stops while legitimate changed-source reruns continue. |
| C-07 · 22–23 Oct | Make coding tasks the primary web experience: source/task, reviewed plan, live activity, changes, checks, usage, checkpoints and download. Depends on C-05/C-06. | Fresh-browser create -> approve -> run -> inspect -> download and reload/resume works; desktop/mobile/keyboard and error/busy states pass; old assurance examples remain clearly labeled. |
| C-08 · 23–24 Oct | Cloud integration and release safety: worker lifecycle, VM-window admission, quota accounting, packaging/image pins, source retention and backup/restore. Depends on C-04–C-07. | Real cloud execution limits, lease recovery, restart persistence, control/data ownership, no secrets in candidate/export, actual restore and public abuse/cost boundaries pass. No paid-plan switch. |
| C-09 · 24–26 Oct | User sessions, versioned new task suite/configuration, matched-budget baseline if affordable, release regression and three genuine rehearsals. Depends on C-08 and an approved spend envelope. | Saved failures and denominators, no holdout tuning, exact runtime/model/image/prompt versions, honest completion/intervention/usage results. No superiority claim without a fair comparison. |
| C-10 · 26–28 Oct | Clean-clone/setup and rights review, authentic video, public access checks, factual entry text and owner submission. Depends on passing release gates. | Public repo/license and working demo, <=3-minute genuine video, actual submitted-status evidence. No automated commit/push/tag/submission is authorized by this plan. |

## 6. Calendar and stop rules

Dates are IST and targets, not guarantees. Assumption: one owner, roughly 3–4 focused weekday hours and 5–6 weekend hours, plus available coding assistance; actual availability is unconfirmed. If less time is available, narrow supported task breadth before cutting reliability or submission buffer.

| Dates | Visible milestone | Mandatory stop/cut rule |
| --- | --- | --- |
| 17–18 Oct | First genuine live model edit/run/test/revise journey | If generation/isolated execution is blocked, stop feature expansion and fix it. No more dashboard-only work. |
| 19–21 Oct | Supported project intake and two distinct real coding tasks | Keep Python and fixed test profiles; cut dependency installation, extra languages and Git hosting integrations. Do not silently present only samples as project support. |
| 22–24 Oct | Recovery/control workflow, usable task UI and real cloud acceptance | If safe public intake is not established, disable it and disclose the narrower prepared-project scope. If that no longer meets the intended product, state the milestone is missed. |
| 25 Oct | Target feature freeze and frozen evaluation configuration | No optional additions. If a core behavior changes later, version it and rerun affected checks/measurements. |
| 25–26 Oct | Bounded evaluation, usability fixes and three live rehearsals | Preserve failed attempts; reduce measurement scope before outcomes if credits are inadequate. Do not invent successful rehearsals. |
| 27 Oct | Genuine video, clean-clone/docs/license/access check | Keep the footage under 3 minutes and all claims matched to the release. |
| 28 Oct, 20:00 | Internal submission target | Owner confirms actual submission, not just a saved draft. |
| 29–30 Oct | Recovery buffer | Access/form fixes only, not new features. |

Official close rechecked on the [competition page](https://nebiusglobalaihackathon.devpost.com/): **30 October 2026, 10:00 a.m. PDT = 10:30 p.m. IST**. Access throughout judging, credit reserve and stable hosting remain release obligations, not solved by a successful deployment today.

The critical path is **real agent loop -> supported projects -> interruption/scope/budget correctness -> cloud acceptance -> evidence and submission**. If those gates slip, revise the scope honestly; there is no promise that every date or a competition win is achievable.

## 7. Testing and acceptance evidence

### Required automated checks

- Intake: traversal/drive/UNC/alternate separators, case collisions, duplicate/linked files, secret/config exclusions, byte/file/body caps, unsupported layout/dependencies and owner isolation.
- Agent: real versus mock provenance, schema/length/transport failures, actual edit generation, valid source hashes, protected-test refusal, same-candidate loops, changed-candidate progress and no false completion.
- Worker: duplicate/parallel claim, event/record atomicity, stale fencing token, crash before/after a provider request, lease expiry, cancellation, pause/resume and monotonic usage reservations.
- Runner: baseline and modified project checks, test collection, failures/errors/skips, timeout, resource exhaustion, output flooding, network/metadata/secret denial and symlink artifact rejection.
- Recovery: restore exact task snapshot, preserve base bytes, refuse stale revision, repeat commands only when authorized, reconcile active container IDs and keep unknown paid calls accounted for.
- API/UI: short enqueue, replay-safe controls, SSE reconnect, source/diff/check/usage/download, no owner leakage, 320/390/tablet/desktop layout and keyboard navigation.
- Hosting: clean cold start, real queued execution without a heartbeat-only false positive, browser disconnect, Sandbox stop/resume, safe session deadline refusal, independent backup/restore and global public spend limits.

### Product evaluation, separate from old invoice measurements

Prepare six new small tasks: three bugs, two bounded features and one correct/no-change project, spanning more than the original invoice example. Freeze task assets and expected behavior before live measurement. If affordable, run a simple loop and the reliability-enabled loop once per task: 12 assigned runs, same model/configuration, inputs and hard budgets. This small sample is descriptive, not statistically conclusive. If budget permits only one system, declare that before outcomes and do not claim a comparative improvement.

Measure external task correctness/regressions, unnecessary changes, human interventions, repeated actions, recovery correctness, calls/tokens and elapsed time. Ordinary project tests and generated tests do not grade the agent's own benchmark success; keep evaluation expectations outside candidate control. At least three real user sessions are a target, not a claimed study. Record actual participation and confusion.

Preserve historical R12/V12/etc. assets, records and `eval-config-v1`. The new project workflow needs a new versioned task/config identity; do not inherit prior measurement claims. Release commits/tags/pushes require separate explicit owner instruction.

## 8. Risks, fallbacks and next action

| Risk | Mitigation / truthful fallback |
| --- | --- |
| NVIDIA output is incomplete or schema-invalid | First ticket reproduces this; bounded schema validation, source/log selection and calibrated output cap. Preserve failures, no canned fallback or silent model substitution. |
| Generic runner/intake exceeds the schedule | Restrict to the documented small layout and preinstalled test profiles. Do not execute unknown dependency/install scripts. |
| Long task outlives function or Sandbox session | Durable worker, short control requests, persisted checkpoints and lifetime admission. No claim of unlimited always-on Hobby execution. |
| Public users exhaust credits or disk | Operator-set global admission/call/execution/disk limits, clear busy/limit UI and required reserve; do not rely on easily regenerated owner IDs alone. |
| Restore destroys user work | Immutable base and task-only snapshots; no local repo mutation; stale/conflicting revisions block application. |
| Quality claims outrun the evidence | Match statements to source/config and actual execution. A passed test is scoped evidence, not proof of all requirements. |
| Scope expands into an IDE clone | Keep deferred features deferred. Stop at a useful tested patch workflow. |

**First implementation session:** C-01, then C-02/C-03's smallest end-to-end slice. Deliver a model-generated repair with real execution output through the application before undertaking broad project intake or UI restructuring.

The plan itself does not authorize additional inference, paid hosting, Git publication or submission. Actual implementation and acceptance evidence must be recorded separately, as in the first increment above.
