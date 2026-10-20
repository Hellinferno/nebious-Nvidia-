# Verification — 20 October 2026

## Current status

The approved portability fix and the latest customization release are deployed at **https://benchproof.vercel.app**. The latest full backend run has **611 passing cases and three intentionally skipped Docker cases**; those three cases passed separately, and the deployed runtime additionally passed fresh isolation, resource-limit, timeout and replay checks. Frontend, deployment, public API and real desktop/mobile browser checks pass.

The public demo now includes skills, reviewed harness choices and **BenchProof public guides**, a read-only MCP documentation connection. The bridge is configured for five queries per UTC day. The public `/mcp` function exposes only static guides, not private source or execution. Additional third-party MCP servers still require operator review/configuration and compatible protocols.

## Checks performed

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

## Live evidence

- Provider/model: Nebius Token Factory, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Provider-reported usage: 985 prompt tokens, 932 completion tokens, 1,917 total. Monetary charge and remaining balance were not measured.
- The generation used an operator-scoped plan, not a model-generated plan. It is a one-sample integration check, not a live held-out benchmark or proof of all workflows.
- Cloud audit: `audit-082f1e22bae9`; patch: `patch-268c0b142dfd`.
- Ordinary imported-project unittest success is scoped to user-supplied checks. It is not equivalent to the protected invoice acceptance gate.

## Resolved portability failure

The previous full run found six bundle cases requesting `mc-01`, while the committed directory is `backend/fixtures/development/MC-01`. Windows tolerated the mismatch but Linux did not. Fixture lookup now resolves the unique case-insensitive name to its canonical directory, rejects case collisions, and retains traversal/link containment checks. Existing bundle tests are unchanged and pass. Fifteen new lookup cases verify canonical names and hashes, invalid paths, missing fixtures, collisions and escaping links; all run in Linux, while three OS-dependent cases are skipped by the separate Windows-only lookup run.

Earlier attempts exposed test-harness packaging/output restrictions and transient Chrome navigation/screenshot races. These were corrected or retried before the successful checks; failed artifacts are retained. The subsequent production upgrade uses the existing verified Hobby project and Sandbox. Private WAL-consistent database/configuration backups and a rollback package were retained before replacement; no active coding tasks were interrupted. Existing coding limits remain 40 model calls/day, 60 executions/day and 2,048 output tokens/call, with the original session deadline. The Vercel project has no Git integration, so future Git pushes do not themselves deploy the runtime.

## Deployed release

- Production: [benchproof.vercel.app](https://benchproof.vercel.app).
- Deployment ID: `dpl_F6mnYCBAfR6i9zktWXVscS9NufrE`.
- Trusted runtime hash: `ebdb1ff5143c47bbee1407cfbc22f243e502eaa8544357c61a40d91893cb43e9` (128 allowlisted files).
- Read-only MCP endpoint: `https://benchproof.vercel.app/mcp`; tool: `read_guide`; configured connection: `benchproof-docs`; shared query allowance: five per UTC day.
- Actual browser-created smoke draft: `coding-90c1292b87074472`. Its skill, single-pass harness and reference hash are pinned; model and execution counters remain zero.
- No new inference calls were made for deployment acceptance. The earlier single-call generation evidence remains separate; configuring a provider is not a fresh inference test.

The build reports **33 existing development/toolchain npm advisories** (including one critical). A separate production-only `npm audit --omit=dev` query reported **zero** advisories, and the frontend install audit reported zero. Development advisories were not remediated in this deployment; this is not an exhaustive security certification.

## Local evidence files

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

## Release limitations

- The portability fix, runtime upgrade and production acceptance are complete. Source publication follows the successful deployed checks.
- The configured MCP endpoint is owned by this project and exposes only public guides. Third-party servers, older protocol initialization, OAuth, SSE and arbitrary tool/harness plugins are not claimed to work.
- Existing development/toolchain npm advisories remain open; production-only audit results are scoped and time-sensitive.
- SKILL.md support is instruction-only, and harness choices are reviewed built-in policies, not arbitrary executable plugins.
- The six-task evaluation CLI is explicitly a scripted gold-answer regression with synthetic usage. Full held-out live-model evaluation remains open.
