# Verification — 20 October 2026

## Current status

The approved fixture-case portability fix is implemented. **All 605 backend cases pass across the full isolated suite and the separate Docker integration run.** Frontend, browser and gateway checks also pass. These checks qualify the changes for the requested Git push; they are not a claim of a production source upgrade.

The new skills, MCP bridge and harness UI are implemented locally; do not assume the public demo already includes them. MCP external connections remain disabled until an operator supplies a trusted compatible endpoint and a daily allowance.

## Checks performed

| Check | Result | Scope |
| --- | --- | --- |
| Targeted backend regression | 280 passed | Worker/store/API, approvals, limits, coding loop, shared runner controls, mocked cloud recovery, extension controls and Vercel origin |
| Additional backend regression | 77 passed | Includes 46 extension/transport tests, project intake, saved generation/cloud evidence tooling and deterministic evaluator tests; overlaps the first run |
| Complete backend suite in Linux Docker | 602 passed, 0 failed, 3 skipped | All 605 collected tests, including the new fixture lookup regressions |
| Docker integration cases | 3 passed | The three cases skipped by the socket-free full-suite container were run separately against the dedicated cloud Docker daemon; candidate code stays isolated |
| Frontend unit tests | 29 passed | Profiles, immutable snapshots, SKILL.md validation, recipes and result presentation |
| Frontend lint / TypeScript / production build | Passed | Built frontend asset `index-CPvAL8Ig.js`; no new UI deployment |
| Changed Python files lint / whitespace check | Passed | Ruff and `git diff --check` |
| Vercel gateway/runtime regression | 15 passed | Local HTTP gateway, body limits, redirects, runtime identity and packaging exclusions |
| Browser: previous workspace flows | 15 assertions passed | Mocked APIs; recipes, draft creation, plan edit/approval, skipped results, uploaded project selection, stale-plan rejection and unavailable-service handling |
| Browser: profile workflows | 17 assertions passed | Mocked APIs; persistence, default selection, duplication, import/export, bounded budgets and plan-only restrictions |
| Browser: new extension workflows | 9 assertions passed | Mocked APIs; skills save/edit/export, unsupported metadata rejection, harness selection, explicit MCP consent/arguments, frozen task payload and profile exclusion of MCP context |
| Browser: public demo | Passed | Real public UI shows the saved live patch's VERIFIED result; desktop/mobile, no browser errors; network restricted to GET/HEAD |
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

Earlier attempts exposed test-harness packaging/output restrictions and transient Chrome navigation/screenshot races. These were corrected or retried before the successful checks; failed artifacts are retained. A suspended VM required its normal trusted startup before Docker was available. Production application source/configuration was not upgraded; only normal trusted startup and temporary test containers were used. The Vercel project has no Git integration, so pushing the repository does not itself deploy this runtime.

## Local evidence files

Generated records are intentionally Git-ignored and available in this workspace:

- `artifacts/coding/remaining-20261020/tests-final-1.xml`
- `artifacts/coding/remaining-20261020/tests-additional-1.xml`
- `artifacts/coding/remaining-20261020/cloud-full-suite-3.xml`
- `artifacts/coding/remaining-20261020/cloud-full-suite-4.xml`
- `artifacts/coding/remaining-20261020/cloud-full-suite-5.xml`
- `artifacts/coding/remaining-20261020/cloud-docker-integration.xml`
- `artifacts/coding/remaining-20261020/fixture-lookup.xml`
- `artifacts/coding/remaining-20261020/cloud-project-check.json`
- `artifacts/coding/remaining-live-20261020-1/report.json` and `cloud-report.json`
- `artifacts/coding/customization-20261017/customization-ui-1792501083800/result.json`
- `artifacts/coding/customization-20261017/agent-profiles-ui-1792501209419/result.json`
- `artifacts/coding/customization-20261017/extensions-ui-1792501230169/result.json`
- `artifacts/coding/customization-20261017/public-readonly-1792501354770/result.json`

Browser directories also contain screenshots. Their tests block external requests for local mocked flows; the public read-only check allows only GET/HEAD to the demo. No API keys, owner capabilities, private runtime configuration or raw credential files should be added to Git with these artifacts.

## Release limitations

- The fixture portability failure is resolved and verified. Git publication follows successful verification; no source upgrade to the public runtime has been performed.
- A production backend/runtime upgrade and deployment acceptance are separate from local validation and Git push.
- No real external MCP endpoint has been configured or interoperability-tested. This is a restricted read-only stateless context bridge, not full MCP runtime compatibility.
- SKILL.md support is instruction-only, and harness choices are reviewed built-in policies, not arbitrary executable plugins.
- The six-task evaluation CLI is explicitly a scripted gold-answer regression with synthetic usage. Full held-out live-model evaluation remains open.
