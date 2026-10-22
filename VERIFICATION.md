# Verification — updated 22 October 2026

## Current status

### Production v3 rollout — 22 October

**Live:** https://benchproof.vercel.app, deployment
`dpl_4PGB22kBveDfE3obV57FjD25zSfx`, trusted runtime
`517e43f650c6e7575bd5e7a198dc4dd77d56be68032050164702b42123831a3d`.
The explicitly approved private production output limit is now **4,096**.
Daily coding limits stay **40 model calls / 60 executions**, shared demo actions
60 and documentation MCP queries five. The November 30 admission deadline,
provider key, candidate limits and Hobby plan are unchanged; no paid upgrade.

- Idle upgrade retains private WAL-consistent database/config backups and an
  exact 129-file rollback package for old runtime `49337c36…`. All 130 new deployed
  file hashes, actual worker output/daily settings and database integrity verify.
- Trusted-cloud checks pass actual network/metadata/secret/read-only isolation,
  timeout denial and enforced 256 MiB OOM kill. Audit, bundle, quotas and worker
  persist across stop/resume. No model call occurs in these infrastructure checks.
- Public cold gateway resume, readiness, clean gate, bundle integrity/fresh replay,
  SSE, faulty-candidate rejection and owner/secret-path boundaries pass. Actual
  production desktop/mobile UI creates one zero-spend draft pinned to v3/4,096;
  JSON/ZIP export and reload preserve zero counters and the new UI asset.
- Initial upload stopped on a root local cache EPERM; adding `.codex-*` to
  `.vercelignore` and its regression fixes the upload boundary. A read-only worker
  checker first had an invalid NUL argument; correcting its helper escaping makes
  it pass. Neither failure performs inference or alters candidate code.

[Sanitized rollout record](verification/policy-v3-rollout-2026-10-22.json).
Raw cloud record `artifacts/vercel/cloud-check-1792677648801.json`, public record
`artifacts/vercel/public-check-1792678015476.json`, and rollout/browser records in
`artifacts/policy-v3-live-20261022/`. **No fresh production model call is claimed**;
the separately frozen staging run below supplies genuine v3/4,096 model evidence.
Source publication follows successful tests/browser checks; Git records its commit
independently from deployment. Older production hashes/settings below are dated
historical snapshots, not the current rollout.

### Separate v3 live acceptance — 22 October

The owner separately authorized another bounded v3 staging regression: three
model calls, 4,096 output tokens/call, two edits and four isolated checks, no SDK
retry. Task **`coding-5e6be4746ce7479b` reaches REVIEW_READY / CHECKS_PASSED**.

- Same frozen public source, requested feature, protected tests and skill; exact
  tested source `83a74711…`, policy `34108fa5…`. Baseline passes three of six
  methods. The first physical-line response still uses an unquoted self-class
  annotation and fails import. Retain this failure: syntax parsing is not runtime
  correctness. The second model response quotes the annotation; candidate and a
  separate fresh final execution each pass all six imported methods.
- **Three calls / two edits / four isolated executions**, 72.65 active seconds;
  **5,496 prompt + 6,404 completion = 11,900 tokens**. All finish reasons `stop`,
  no SDK retries or manual/canned edits. Actual bill/current balance unknown.
  Shared daily quota reserved and consumed three calls/four executions. Original
  project/tests remain unchanged; candidates run only in pinned, non-root,
  networkless cloud Docker with enforced limits and no secret environment.
- Saved JSON/ZIP, exact candidate hashes, all seven actions, usage and fresh run
  IDs reconcile. Genuine retained staging evidence passes desktop/mobile,
  policy/export/ZIP and reload through a disabled local API/UI without spending.
  The first browser checker expected `REVIEW_READY` instead of the UI's displayed
  `REVIEW READY`; only its selector changed and the failed report is retained.
- Both edit completions exceed 2,048 tokens (2,729 and 2,566). This run does not
  prove success at the old production allowance. The owner explicitly approved
  **4,096 for production, daily limits unchanged**; library defaults remain 2,048.
- Full backend result remains **663 passed / three skipped**, those three Docker
  integrations passing separately on the recorded snapshot. Fresh frontend 29,
  deployment 30, lint/build pass. Eight deployment socket tests initially hit
  sandbox EACCES and pass with loopback access allowed. The added deployment
  regression excludes root `.codex-*` cache/private-review folders from uploads.

Sanitized [v3 result](verification/policy-v3-live-2026-10-22-results.json); raw
records `artifacts/policy-v3-live-20261022/`. All authorized calls are consumed.
This is one already-seen sample after one failed candidate, not first-pass success,
held-out evaluation, a competitor comparison, real-user study or proof beyond the
six imported checks. Earlier failures/denominators and historical pre-live policy
manifests remain unchanged. Production acceptance is recorded separately below.

### Earlier staging failure and local v3 correction — 22 October

The owner later said to proceed with live acceptance. One staging run was bounded
to three calls, 4,096 output tokens/call, two edits and four isolated checks.
**It failed**, and no further inference followed. Source remains local; production
runtime `49337c36…`, its settings and the 2,048-token default are unchanged.

- Task `coding-62c3821cedc44977`, v2 policy `0a9ec6ea…`, tested source `34bcf40f…`:
  first candidate `86648580…` parses but raises the same forward-reference NameError.
  Revision `8d5dd5f4…` quotes the annotation but encodes 28 line breaks as literal
  backslash-n sequences on one physical line, causing SyntaxError.
- Final **BLOCKED / HARNESS_STOPPED**, three calls / two edits / three executions.
  All provider responses finished `stop`; this is not another output truncation.
  Baseline passes three of six methods, both candidates fail import, final NOT_RUN.
  Original project/tests stay unchanged. Usage **5,302 prompt + 5,228 completion =
  10,530 tokens**; bill/balance unknown. Shared quotas reserve three calls/four
  checks conservatively; the unused execution reservation is not refunded.
- A private staging database and exact tested source were used, with the existing
  key only in the trusted cloud process and candidate image ID pinned. Public
  activity was checked before actions. No candidate ran on the laptop. A missing
  parent directory first stopped preflight before paid work; matching source and
  absence of a run directory were reconciled before resuming once.
- Local v3 policy `34108fa5…` requests physical source lines and joins them with LF.
  Explicit v1 compatibility retains literal source; no unescaping or guessed repair.
  Mixed encodings, embedded line breaks/NULs and size/path violations reject.
  Python 3.12 AST parsing rejects invalid changed source with **INVALID_PYTHON**
  before returning a patch or reserving candidate execution; usage is retained,
  with no paid retry. Parsing does not execute code or detect every runtime error,
  including the first NameError. Isolated candidate/final checks remain required.
- Bounded exhaustion now reports PATCH_ATTEMPT_LIMIT; historical HARNESS_STOPPED
  messages no longer incorrectly claim a single-pass/no-revision run.
- Final v3 suite: **663 passed / three skipped**, followed by **three separate Docker
  integration passes**, snapshot
  `83a74711f703faa741cb394e748c72323bcb950af407c1cb2874d702c8ae773c`.
  Frontend **29** and deployment **29** pass; lint/build pass. Local 130-file package
  `517e43f650c6e7575bd5e7a198dc4dd77d56be68032050164702b42123831a3d`.
- Saved parsed-file/diff replay rejects the malformed revision before execution;
  it does not reconstruct raw model output or establish live v3 success. A private
  WAL-consistent staging copy was inspected through the current local API/UI:
  desktop/mobile, original v2 policy export and reload preserve three-call counters
  without new spend. A fresh v3 draft passes the same no-spend browser checks.
  This is retained-result review, not continuous browser inference or production
  acceptance of the new code.

Sanitized [v2 staging failure](verification/policy-v2-live-2026-10-22-results.json)
and [v3 identity](verification/generation-policy-v3.json) are separate; earlier
denominators remain unchanged. Raw records: `artifacts/policy-v2-live-20261022/`.
Final full suite:
`artifacts/release-hardening-20261020/cloud-full-suite-1792658539472.json` / `.xml`.
At this earlier snapshot, **v3 live quality was NOT_RUN**. The separately
authorized v3 run above supersedes that status without changing the v2 failure.

### Earlier no-spend generation-policy candidate — 22 October

This subsection describes the earlier v2 snapshot before the separate resumed
bounded staging run above; its no-spend statements are historical.

This working-tree candidate is **not pushed or deployed**. Public production
remains on `49337c36…`; the owner declined any new inference spending. The earlier
feature failures remain failures; no new live feature completion is claimed.

- `coding-generation-v2`, policy hash
  `0a9ec6ead2f13956b9b5d9a97947bd4a6c3700587b849d4a6132324d080a00ce`,
  adds Python 3.12/forward-reference and concise complete-file guidance. A prompt
  instruction is not a guarantee of correct code or a provider reasoning switch.
- API creation pins exact policy identity; API enqueue and live-worker validation
  refuse missing/changed identity with `STALE_RUNTIME` before paid reservations.
  Exports preserve the task's policy, not whichever prompt is current later, and
  exclude unrelated private runtime fields. Existing task evidence is not rewritten.
- **160 focused tests pass**. Latest full non-root/networkless cloud suite:
  **646 passed / three skipped**; those **three Docker integrations pass separately**.
  Same 345-file snapshot:
  `34bcf40f96165ec819fd05374170b58f2fd1c80ac54af532662fea1130129787`.
  Dependencies reused from the tested environment; this is not another fresh install.
- **29 frontend / 29 deployment tests pass**, changed Python lint, frontend lint
  and production build pass. Candidate package is
  `32b96490f8002653a160c6cb097d2c05d9d0991933b8010dad44657c9a3e5301`
  (130 allowlisted files). The UI assets remain unchanged; no runtime upgrade ran.
- Static saved-diff replay reproduces both recorded candidate hashes and confirms
  the unquoted class-self annotation without importing/executing candidates. A fake
  client replays the saved truncated finish reason/usage: still rejected once,
  source unchanged, no patch or retry. Raw truncated content was not retained or
  reconstructed. This checks fail-closed handling, not improved model quality.
- A real local API and development UI use a disposable database, disabled coding,
  zero daily allowances, empty provider key, no worker and a provider-construction
  trap. Browser desktop/mobile draft inspection, policy JSON/ZIP download and
  reload with zero counters pass. No candidate code executes on the laptop.
  The seed helper first normalized Windows fixture newlines and was correctly
  rejected; preserving exact source bytes fixes the helper, not application policy.
  A final checker initially compared independent JSON/ZIP exports byte-for-byte;
  they differ only in the legitimate per-export `exported_at` timestamp. All
  other manifest fields, pinned policy and zero counters match.
- No output allowance, model, provider reasoning flag, SDK retry, protected test,
  candidate resource limit or hosting setting changes. NVIDIA's documented model
  reasoning options do not verify equivalent behavior on the exact Nebius endpoint;
  no unverified option is sent. See the
  [NVIDIA model reference](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-30b-a3b).

Records: `artifacts/generation-policy-20261022/` (`targeted.xml`, `saved-replay.json`,
`browser-check.json`, Docker report and build/test logs) and
`artifacts/release-hardening-20261020/cloud-full-suite-1792656061323.json` / `.xml`.
The [new policy manifest](verification/generation-policy-v2.json) is separate from
the immutable 21 October samples/results. Next gate: separately authorized live
regression and reviewed rollout; until then C-05 reliability remains partial.

### Additional public workflows and release checks

The deployed runtime remains `49337c3683310a7c137e898459dd38ab3927a2c3cd7cc3588e6523596127bcd3`.
No hosting setting, prompt, model, output limit or candidate boundary changed.
New frozen inputs, sanitized public outcomes and scope/reproduction notes are in
[verification](verification/README.md).

- Original owner-approved four-call batch used **three calls / three executions**.
  BankAccount feature `coding-84661e72c57d4f0e` is **BLOCKED / HARNESS_STOPPED**:
  its candidate used an unquoted self-class annotation and failed import on Python
  3.12. No final check ran. Correct-total control `coding-0958ac9e8ad94048` is
  **BLOCKED / BASELINE_ALREADY_PASSES**, with three baseline checks passing and
  zero edits. **One of two expected outcomes**, zero completed features.
- Separately approved known-sample follow-up `coding-9f3d69e13e1d4862` used
  `bounded-v1` with at most three calls, two edits and four executions, rather
  than the original single-pass budget. It consumed **three calls / two edit
  reservations / two executions**, again failed class import, then stopped
  **BLOCKED / MODEL_OUTPUT_TRUNCATED** when the revision hit 2,048 output tokens.
  No partial revision was accepted/executed and no fresh final check ran. It is
  not a matched comparison or a successful feature implementation.
- Provider reconciliation: original batch **3,800 input + 3,736 output = 7,536
  tokens**, listed-price estimate **$0.00112464**; separate follow-up **5,089 +
  4,844 = 9,933 tokens**, estimate **$0.0014679**. Actual billed charges/current
  balance remain unknown. All requests count, including the truncated revision;
  SDK retries are zero. No further inference is authorized by these checks.
- The follow-up checker initially expected an explicit default harness field;
  production intentionally omits `bounded-v1` during normalization. Corrected the
  checker and continued the same zero-counter draft; no duplicate planning.
  A Chrome crash occurred before planning. Later read-only browser inspection
  first hit a Chrome-unsafe ephemeral loopback port; allowing that test port in
  the isolated Chrome process fixed the harness. These are retained checker
  failures, not additional model attempts.
- Desktop/mobile retained-result inspection, original-project immutability,
  ZIP export and reload without extra usage pass on both failed feature tasks
  and the clean control. Zero browser errors in completed checks. These safety
  passes do not erase either feature failure. All three ZIPs match their retained
  JSON manifests/plans/counters/diffs under non-executing inspection.
- Latest complete non-root, networkless cloud suite: **635 passed / three skipped**;
  those **three Docker integrations passed separately** on source snapshot
  `3174d3ff7f39b36a8e0c6c2887c1820bf9d4be835295ba07afaad618a9f9fd1e`.
  Four static public-input tests account for the increase from 631. This run
  reused the tested cloud dependencies; the prior fresh locked install remains
  a distinct 631-test result. Candidate code never ran on the laptop.
- Frontend **29**, deployment/toolchain **29** pass; Python lint, frontend lint
  and production build pass. Eight deployment socket tests first failed with
  sandbox EACCES, then all 29 passed with loopback permitted. The build exactly
  reproduces the deployed 129-file runtime hash; no deployment is needed.
- Read-only judging configuration check correctly returns
  **ADMISSION_ENDS_BEFORE_JUDGING**: admission ends 30 November 23:59 IST, while
  published judging ends 16 December 01:30 IST. Submission closes 30 October
  22:30 IST. No extension/limit change is approved or performed. This is not a
  website shutdown date or an uptime guarantee. See the
  [official rules](https://nebiusglobalaihackathon.devpost.com/rules).

Records: `artifacts/evaluation-batch-20261021/` (frozen records, original case
folders, separate `bank-transfer-bounded-followup/`, provider reconciliation,
ZIP inspection, browser reports and judging check) and
`artifacts/release-hardening-20261020/cloud-full-suite-1792591758895.json` / `.xml`.
Raw private state stays ignored. The public summaries contain no owner capability.
Live feature reliability, volunteer sessions/held-out evaluation, upstream CLI
advisories, judging access, rights signoff, public YouTube URL and actual entry
submission remain open; C-05, C-09 and C-10 are not all complete.

### Deployed hardening revision

The R-series plan in `BUILD_PLAN.md` separates implemented, tested, deployed,
measured and submitted states. Current production rejects unsupported pytest project
profiles before task/model/executor dispatch and adds non-destructive global project
count/payload plus database/free-disk admission checks. See `DATA_RETENTION.md`.

Earlier hardening-source verification (superseded test totals above):

- Focused no-inference/no-candidate backend tests: **213 passed**, including 20 new
  runner/storage regressions. The initial test invocation lacked its temporary
  parent directory; corrected runs pass and failed artifacts are retained.
- Complete backend suite in dedicated non-root, networkless Linux Docker:
  **631 passed, three skipped**. All three skipped Docker integration cases passed
  separately on the same source snapshot, with candidates still Docker-isolated.
- Source snapshot identity: `3f4960b40eaa0fe219bb09d7af05089e9b8eefd205e048e1db321c9af5ae9b36`.
- Fresh setup verification additionally installs the locked backend requirements
  and editable project into a new cloud Python environment, then repeats the full
  suite in non-root, networkless Docker: **631 passed, three skipped** again.
  This is the same source hash and is not additive. Clean root `npm ci
  --ignore-scripts` and CLI/toolchain checks also pass. The independent Git clone
  and no-spend three-process/browser launch below close the setup smoke gate.
- Frontend **29 passed**, deployment/toolchain **23 passed**; changed Python lint,
  frontend lint, TypeScript/Vite production build and CLI version smoke pass.
- Rebuilt UI mocked-browser regressions: **15 workspace**, **17 profile**, **nine
  extension** assertions pass, with zero browser errors and external requests
  blocked. These are not live-model or updated-production acceptance tests.
- Deployed package: `49337c3683310a7c137e898459dd38ab3927a2c3cd7cc3588e6523596127bcd3`,
  129 allowlisted files; UI asset `index-Bh_QKpW8.js`.
- Compatible development toolchain patches reduce npm advisories from 33 to
  **23 high, zero critical/moderate**; root production-only audit remains zero.
  Remaining upstream/incompatible-major paths are documented in `DEPENDENCY_REVIEW.md`.
- The clean-clone install surfaced a frontend Vite advisory despite an earlier
  zero report. Pinned compatible Vite 8.3.3 and a lock regression resolve that path;
  fresh frontend audit is zero, 29 frontend / 23 deployment tests and lint/build
  pass again. Generated assets/package exactly reproduce deployed hash `49337c36…`;
  no new backend source, deployment or model call was needed for this tool patch.
- Exactly two new inference calls were used for the separately recorded live
  rehearsal below. No automatic cleanup, paid hosting upgrade or inference retry.

New artifacts: `artifacts/release-hardening-20261020/targeted-4.xml`,
`cloud-full-suite.json` / `.xml`, `cloud-docker-integration.json` / `.xml`, and
`npm-audit-all.json` / `npm-audit-production.json`. Full-suite temporary scratch
uses 256 MiB so tests have headroom above the new 128 MiB free-space reserve;
candidate production limits remain unchanged.

### Production rollout and public acceptance

- Production: [benchproof.vercel.app](https://benchproof.vercel.app).
- Deployment `dpl_7SPDgfYC3M5HLPCThyCMWEPBRgi7` is READY and owns the production alias.
  Verified existing Hobby account; private provider/origin secrets, MCP allowlist,
  40-call/60-execution daily coding limits, 2,048 output-token allowance and original
  admission deadline preserved. No Git integration: a source push is not deployment.
- Before replacement, verified no active task/action, database integrity, private
  WAL-consistent database/limits/config backups and a reconstructed exact rollback
  package for old runtime `ebdb1ff5143c47bbee1407cfbc22f243e502eaa8544357c61a40d91893cb43e9`.
  Explicit reviewed-hash upgrade was used; historical task/evidence state retained.
- The first gateway deployment `dpl_6dmZjEdYRXbBvbGT6faLUv4QtWnD` failed Linux
  `npm ci`: optional peers `@emnapi/core` / `@emnapi/runtime` 1.11.3 were absent
  from the Windows-generated lockfile. Verified registry entries and a lockfile
  regression fix this. The subsequent actual Linux install/build/deployment passes;
  the failed deployment is retained, not described as a successful first attempt.
- Cloud acceptance passes: audit `audit-e98139f31c21`, including isolation,
  enforced memory/OOM negative, timeout cleanup, origin/owner restrictions,
  gate/export/validation/replay and stop/resume persistence.
- Fresh public acceptance on 21 October passes: audit `audit-646e9823447f`,
  readiness 9,349 ms, clean/faulty checks, bundle validation/replay, SSE, ownership,
  oversize and secret-path denials. This measurement is not an explicit cold-stop
  latency benchmark. Provider testing was skipped in this API check, then covered
  by the separately authorized live task below.

Rollout/public records: `artifacts/release-live-20261020/preflight.json`,
`artifacts/vercel/cloud-check-1792511226077.json`, and
`artifacts/vercel/public-check-1792588247301.json`. Backups contain private state and
must remain private. Full runtime verification is not an unrestricted security audit.

### Customized live browser rehearsal

Task `coding-d6450f348202421a` completed REVIEW_READY using a pinned instruction
skill, `single-pass-v1` harness and consented documentation MCP workflow snapshot.
The public StringCalculator baseline failed its negative-number check; a genuine
model-generated edit changed only `app/calculator.py`. All three candidate/fresh
final checks passed with protected imported tests and the original project unchanged.
Desktop/mobile layout, export download, ZIP inspection and reload/counter persistence
pass with no browser errors. The ZIP is not digitally signed.

Exactly two live Nebius/NVIDIA calls, zero retries: 2,773 prompt + 1,341 completion
= 4,114 tokens, one patch attempt and three isolated executions. The first browser
harness timed out on an underscore-versus-space state label after planning succeeded;
read-only reconciliation and continuation of the same task avoided repeating spend.
At the checked listed prices the estimated inference charge is $0.00048822; actual
billed charge, updated balance and enforcement of the intended $50 judging reserve
are UNKNOWN. The user reported $59 before the run. See [RELEASE_REHEARSAL.md](RELEASE_REHEARSAL.md)
for identities, recorded usage, failure retention and local evidence. Plan review was
agent-assisted under the owner's authorization, not a human user study. This one
public sample is not a held-out live-model benchmark or proof of every workflow.

### Corrected walkthrough

The actual tracked MP4 now has corrected local synthetic narration and embedded /
standalone captions, plus a dated still of the separate customized rehearsal.
Duration 138.28 seconds, H.264 1280×720, AAC stereo, mov_text subtitles. Full media
decode passes; all 17 embedded captions match the standalone SRT and the new final
frame is visually checked. SHA-256:
`0786795b7eeda243125e82d5f1674f44df3a6da2456743ae83908aca8ccc6d46`.
The original is retained privately. The first speech attempt was blocked by local
sandbox voice access; using the installed Windows voice outside that boundary
completed without inference/network calls. The clip truthfully describes saved-task
review, not a newly recorded inference/approval/rollback. See [recordings/README.md](recordings/README.md).
The legacy recording script no longer hardcodes its sample owner capability.

### Independent clean-clone setup smoke

An independent local Git clone of `7b7349aeaedbc9d98891492a306b554c57a6efd7`
installed the locked Python requirements, editable backend and both npm lockfiles.
`pip check` reports no broken requirements. API, separately disabled worker and
Vite development UI start together on loopback. Real desktop/mobile browser checks
pass, including CORS, honest disabled-coding messaging and no overflow/errors.
The clone's tracked tree remains clean. Its database has zero coding tasks/actions;
provider is unconfigured, coding disabled and model allowance zero. This is not a
local Docker or paid live-mode reproduction; cloud execution has separate evidence.

The first browser attempt blocked localhost CORS OPTIONS preflights in its test
allowlist. That failure is retained; allowing only the necessary local preflight
requests makes the check pass. Task/model POSTs remain blocked. No product workaround,
model retry or sensitive `.env` copy was used. Local test processes were stopped.
Records: `artifacts/release-hardening-20261020/clean-clone-smoke.json`,
`clean-clone-smoke-preflight-blocked.json`, `clone-*-install.log`, and
`artifacts/coding/customization-20261017/clean-clone-no-spend-1792590419941/`.
Follow-up release edits after that tested commit are documentation only.

Open gates: upstream development advisories,
owner final video viewing, broader live evaluation/user sessions,
judging credit/access reserve, final rights review and owner submission confirmation.
Do not infer their completion from test counts or this single rehearsal.

## Historical 20 October customization release

The following records describe the prior runtime and counts, not the current
hardening deployment. Later evidence and remaining gates are above.

The approved portability fix and the customization release are deployed at **https://benchproof.vercel.app**. That published release's recorded full backend run has **611 passing cases and three intentionally skipped Docker cases**; those three cases passed separately, and the deployed runtime additionally passed isolation, resource-limit, timeout and replay checks. Frontend, deployment, public API and real desktop/mobile browser checks passed for that release.

The public demo now includes skills, reviewed harness choices and **BenchProof public guides**, a read-only MCP documentation connection. The bridge is configured for five queries per UTC day. The public `/mcp` function exposes only static guides, not private source or execution. Additional third-party MCP servers still require operator review/configuration and compatible protocols.

### Historical checks performed

| Check | Result | Scope |
| --- | --- | --- |
| Targeted backend regression | 280 passed | Worker/store/API, approvals, limits, coding loop, shared runner controls, mocked cloud recovery, extension controls and Vercel origin |
| Additional backend regression | 77 passed | Includes 46 extension/transport tests, project intake, saved generation/cloud evidence tooling and deterministic evaluator tests; overlaps the first run |
| Complete backend suite in Linux Docker | 611 passed, 0 failed, 3 skipped | All 614 collected tests, including private MCP deployment configuration and request-header regressions |
| Docker integration cases | 3 passed | The three cases skipped by the socket-free full-suite container were run separately against the dedicated cloud Docker daemon; candidate code stays isolated |
| Frontend unit tests | 29 passed | Profiles, immutable snapshots, SKILL.md validation, recipes and result presentation |
| Frontend lint / TypeScript / production build | Passed | Built frontend asset `index-CPvAL8Ig.js`; no new UI deployment |
| Changed Python files lint / whitespace check | Passed | Ruff and `git diff --check` |
| Vercel gateway/runtime/MCP regression | 22 passed | Local gateway, private configuration, docs server validation, body limits, redirects, runtime identity and packaging exclusions |
| Browser: previous workspace flows | 15 assertions passed | Mocked APIs; recipes, draft creation, plan edit/approval, skipped results, uploaded project selection, stale-plan rejection and unavailable-service handling |
| Browser: profile workflows | 17 assertions passed | Mocked APIs; persistence, default selection, duplication, import/export, bounded budgets and plan-only restrictions |
| Browser: new extension workflows | 9 assertions passed | Mocked APIs; skills save/edit/export, unsupported metadata rejection, harness selection, explicit MCP consent/arguments, frozen task payload and profile exclusion of MCP context |
| Browser: public demo | Passed | Real public UI shows the saved live patch's VERIFIED result; desktop/mobile, no browser errors; network restricted to GET/HEAD |
| Browser: deployed customization | Passed | Real public APIs: save/select a skill, choose single-pass, consent to real HTTPS MCP retrieval, create an immutable private draft, verify pinned content hash and zero model/execution counters; desktop/mobile, no browser errors |
| Deployed cloud acceptance | Passed | Origin authentication, non-root/networkless Docker isolation, 256 MiB enforced OOM negative, timeout cleanup, protected checks, bundle integrity/replay, stop/resume persistence |
| Public cold-start acceptance | Passed | Cold resume in 8.5 seconds during this check, clean/faulty checks, replay, SSE, ownership, oversized-body and secret-path denials; provider call explicitly skipped |
| Production-only npm dependency audit | 0 advisories reported | Not an exhaustive security assessment; see the tooling note below |
| Current generic project runner in cloud Docker | Passed | Real failing baseline, passing candidate and cancellation, using the current local source in a temporary directory; production source unchanged |
| Live Nebius generation | Passed | Exactly one request, output allowance 2,048 tokens, zero automatic retries; no candidate execution on the laptop |
| Saved live patch through protected cloud gate | Passed | Original MC-01 fault reproduced, exact saved patch imported, candidate passed protected isolated checks; zero additional inference calls |

Counts from overlapping test selections are not additive. Mocked failure-mode tests are not claims of physically reproducing every cloud outage. The full-suite container intentionally has no Docker socket. All three skipped cases passed in the separate integration run: clean/faulty fixture execution, recorded isolation findings and timeout cleanup. The generic project runner additionally passed baseline/candidate execution and cancellation checks.

### Earlier live evidence

- Provider/model: Nebius Token Factory, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Provider-reported usage: 985 prompt tokens, 932 completion tokens, 1,917 total. Monetary charge and remaining balance were not measured.
- The generation used an operator-scoped plan, not a model-generated plan. It is a one-sample integration check, not a live held-out benchmark or proof of all workflows.
- Cloud audit: `audit-082f1e22bae9`; patch: `patch-268c0b142dfd`.
- Ordinary imported-project unittest success is scoped to user-supplied checks. It is not equivalent to the protected invoice acceptance gate.

### Resolved portability failure

The previous full run found six bundle cases requesting `mc-01`, while the committed directory is `backend/fixtures/development/MC-01`. Windows tolerated the mismatch but Linux did not. Fixture lookup now resolves the unique case-insensitive name to its canonical directory, rejects case collisions, and retains traversal/link containment checks. Existing bundle tests are unchanged and pass. Fifteen new lookup cases verify canonical names and hashes, invalid paths, missing fixtures, collisions and escaping links; all run in Linux, while three OS-dependent cases are skipped by the separate Windows-only lookup run.

Earlier attempts exposed test-harness packaging/output restrictions and transient Chrome navigation/screenshot races. These were corrected or retried before the successful checks; failed artifacts are retained. The subsequent production upgrade uses the existing verified Hobby project and Sandbox. Private WAL-consistent database/configuration backups and a rollback package were retained before replacement; no active coding tasks were interrupted. Existing coding limits remain 40 model calls/day, 60 executions/day and 2,048 output tokens/call, with the original session deadline. The Vercel project has no Git integration, so future Git pushes do not themselves deploy the runtime.

### Previous deployed release

- Production: [benchproof.vercel.app](https://benchproof.vercel.app).
- Deployment ID: `dpl_F6mnYCBAfR6i9zktWXVscS9NufrE`.
- Trusted runtime hash: `ebdb1ff5143c47bbee1407cfbc22f243e502eaa8544357c61a40d91893cb43e9` (128 allowlisted files).
- Read-only MCP endpoint: `https://benchproof.vercel.app/mcp`; tool: `read_guide`; configured connection: `benchproof-docs`; shared query allowance: five per UTC day.
- Actual browser-created smoke draft: `coding-90c1292b87074472`. Its skill, single-pass harness and reference hash are pinned; model and execution counters remain zero.
- No new inference calls were made for deployment acceptance. The earlier single-call generation evidence remains separate; configuring a provider is not a fresh inference test.

The build reports **33 existing development/toolchain npm advisories** (including one critical). A separate production-only `npm audit --omit=dev` query reported **zero** advisories, and the frontend install audit reported zero. Development advisories were not remediated in this deployment; this is not an exhaustive security certification.

### Previous local evidence files

Generated records are intentionally Git-ignored and available in this workspace:

- `artifacts/coding/remaining-20261020/tests-final-1.xml`
- `artifacts/coding/remaining-20261020/tests-additional-1.xml`
- `artifacts/coding/remaining-20261020/cloud-full-suite-3.xml`
- `artifacts/coding/remaining-20261020/cloud-full-suite-4.xml`
- `artifacts/coding/remaining-20261020/cloud-full-suite-5.xml`
- `artifacts/coding/remaining-20261020/cloud-full-suite-6.xml`
- `artifacts/coding/remaining-20261020/cloud-docker-integration.xml`
- `artifacts/coding/remaining-20261020/fixture-lookup.xml`
- `artifacts/coding/remaining-20261020/cloud-project-check.json`
- `artifacts/coding/remaining-live-20261020-1/report.json` and `cloud-report.json`
- `artifacts/coding/customization-20261017/customization-ui-1792501083800/result.json`
- `artifacts/coding/customization-20261017/agent-profiles-ui-1792501209419/result.json`
- `artifacts/coding/customization-20261017/extensions-ui-1792501230169/result.json`
- `artifacts/coding/customization-20261017/public-readonly-1792501354770/result.json`
- `artifacts/vercel/cloud-check-1792504176521.json`
- `artifacts/vercel/public-check-1792504437886.json`
- `artifacts/deployment-20261020/preflight-2.json`
- `artifacts/deployment-20261020/public-features.json`
- `artifacts/deployment-20261020/deployed-ui.json`
- `artifacts/coding/customization-20261017/deployed-extensions-1792504441739/result.json`

Browser directories also contain screenshots. Local mocked flows block external requests. The earlier public read-only check allows only GET/HEAD; the deployed customization check additionally allowlists only MCP-context, project and draft creation POSTs, blocking plan/start calls. No API keys, owner capabilities, private runtime configuration or raw credential files should be added to Git with these artifacts.

### Previous release limitations

- The portability fix, runtime upgrade and production acceptance are complete. Source publication follows the successful deployed checks.
- The configured MCP endpoint is owned by this project and exposes only public guides. Third-party servers, older protocol initialization, OAuth, SSE and arbitrary tool/harness plugins are not claimed to work.
- Existing development/toolchain npm advisories remain open; production-only audit results are scoped and time-sensitive.
- SKILL.md support is instruction-only, and harness choices are reviewed built-in policies, not arbitrary executable plugins.
- The six-task evaluation CLI is explicitly a scripted gold-answer regression with synthetic usage. Full held-out live-model evaluation remains open.
