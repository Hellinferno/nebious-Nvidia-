# Verification — 21 October 2026

## Current status

### Deployed hardening revision

The R-series plan in `BUILD_PLAN.md` separates implemented, tested, deployed,
measured and submitted states. Current production rejects unsupported pytest project
profiles before task/model/executor dispatch and adds non-destructive global project
count/payload plus database/free-disk admission checks. See `DATA_RETENTION.md`.

Current-source verification:

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
