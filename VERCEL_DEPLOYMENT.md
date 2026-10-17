# Vercel deployment

Status (17 October 2026 IST): the refreshed production UI is deployed at [benchproof.vercel.app](https://benchproof.vercel.app) on the Hobby team. Cloud isolation, memory enforcement and persistence/restart pass again for its packaged version; fresh-profile layout checks pass at six screen widths. Prior public gate/export/replay/SSE/access checks and one live NVIDIA diagnosis passed, but a later diagnosis returned HTTP 422, so model reliability remains open. The laptop demo is an optional fallback, not a dependency.

## Design

- Vercel serves the built React UI and a same-origin API gateway.
- A named Vercel Sandbox hosts the trusted FastAPI service and its SQLite database.
- Each candidate still executes in a fresh, resource-limited, network-denied Docker container, with no model/provider credentials mounted into it.
- Persistent sandbox state is resumed by name; it must never be silently replaced if its saved state is unavailable.
- The gateway uses project authentication for Sandbox operations. Only the Nebius inference credential and an origin-authentication secret reach the trusted API process; no Vercel control-plane credential reaches a candidate.
- Only an allowlisted runtime package is uploaded. Local secrets, audit databases, trial records and held-out evaluation truth are excluded.
- Sandbox sessions are bounded and on demand. New sessions must restart services, preserve limits/audits, and pass runner readiness before actions are enabled.

## Acceptance before switching the demo

- [x] Vercel Hobby account and Sandbox access verified.
- [x] Exact installed SDK API and lockfile verified (`@vercel/sandbox` 3.8.0, CLI 64.3.1).
- [x] Deployment package excludes secrets and hidden held-out truth (allowlist tests pass).
- [x] Docker isolation, cleanup and timeout controls pass inside Vercel Sandbox.
- [x] SQLite, artifact and daily-limit state survive a stop/resume cycle, followed by a fresh isolated replay.
- [x] Origin authentication rejects unauthenticated requests before the API (HTTP 403).
- [x] Public API, model call, SSE, ownership, gate, export and replay verified without a Vercel account session.
- [x] Fresh-browser interactive UI journey and reload/download verified after the concurrency fix.
- [x] Quota bounds and observed cold-start behavior recorded; no paid upgrade enabled. Full judging-period usage reserve remains unconfirmed.

The frozen local evaluation configuration is retained as historical local evidence. A Vercel deployment has a different environment and cannot inherit measured claims without fresh checks.

## Deployment sequence

Run from the repository root after authenticating Vercel CLI with the intended Hobby account:

For a new account/project, first run `npx vercel project create benchproof --scope YOUR_HOBBY_TEAM`, then link that existing project. CLI 64.3.1 otherwise attempts to convert the frontend/backend directories into Services during automatic new-project setup, conflicting with this intentionally single-project gateway configuration.

```powershell
npm ci
npm --prefix frontend ci
npm run build
npm run test:vercel
npx vercel link --yes --project benchproof
npx vercel env pull .env.local
node deployment/vercel/provision.mjs
node deployment/vercel/verify.mjs
node deployment/vercel/deploy.mjs
```

The provisioner and deployer query the linked team's actual billing plan and refuse paid or unknown plans. They do not enable an upgrade. Local `.env` must contain the existing Nebius API key and pinned model; never use a `VITE_` variable for these values. `.env.local`, `.vercel/`, audit databases, artifacts and held-out fixtures are excluded from upload.

The provisioner creates one named sandbox and a 1 GiB Drive (the API's minimum size). SQLite, bundle artifacts and the daily action cap live under `/data/benchproof` on that Drive. Python 3.12 and the locked backend packages are installed in the trusted sandbox. The candidate image is built there; its actual digest must be recorded by cloud preflight, not copied from the local evaluation record.

The verifier checks the unauthenticated origin returns 403, all Docker isolation findings and timeout cleanup pass, the clean gate/export/validation/replay and SSE work, and another owner is denied. It then stops and resumes the sandbox and checks the audit, exact bundle hash, action counters and heartbeat persist. It records sanitized evidence under `artifacts/vercel/`. A failed check cannot authorize gateway deployment.

The deployer requires the same linked project and verified runtime hash, sends four gateway settings through CLI stdin, and deploys production. The provider key remains solely on the trusted origin. After deployment, verify the actual public UI and rewritten API paths, a bounded real NVIDIA diagnosis, SSE streaming, ownership denial and fresh replay through the gateway. Do not replace the fallback until those checks pass.

## Local evidence and limitations

- Full backend regression: 235 passed, including Docker, origin-authentication and Linux output-directory permission tests.
- Deployment tests: 15 passed, covering forwarding, SSE, request limits, fail-closed behavior, exclusions, known-runtime lookup, explicit upgrades, Hobby restrictions and concurrent lifetime-extension recovery.
- Frontend production build and lint, Python lint and Bash syntax checks passed.
- Current runtime package: 106 files, SHA-256 `6178ebac963c09e485b4d44fd09945f276f40bd14a16b73237cafbd254f5ec10`, including the refreshed UI assets. Previous package `d858c8c2a9494f1ea8922068969724b4236f0c2c0ac3b32e060d95d533ac658c` remains the identity of the earlier evidence. Python is installed under the trusted application directory, not root's private home. Only each private snapshot's output directory is made container-writable; candidate and launcher mounts remain read-only.
- Cloud VM: `iad1`, 1 vCPU / 2048 MiB, Python 3.12.14, Docker 29.1.3, managed image `vercel/sandbox/universal@sha256:c77f7436b9bc0a8b01ef7b09dbcea2de6a18a9fe2aafa89996d2da193da72cf0`. Candidate image `sha256:e97eb0d1e5902fe17fc632d0376d325d2584fb7f6cc1f919199c0c9a9bcbd68f` was built, but neither image presence nor API readiness proves resource-limited execution.
- Initial failures are retained: `artifacts/vercel/initial-runner-failure.json` (threaded cgroups, exit 125) and `artifacts/vercel/output-permission-failure.json` (non-root output write denied). These attempts were INCONCLUSIVE, never VERIFIED; subsequent fixes preserve all candidate limits.
- The owner explicitly approved trusted-backend key storage and the dedicated VM's root cgroup adjustment after auto-review required confirmation. Startup now moves this VM's services into a child cgroup before delegating memory/CPU/pid controllers; unknown child groups fail closed. The approved fix survives restart.
- Production dependency audit: root `npm audit --omit=dev` and the frontend install report zero vulnerabilities. The Vercel CLI's development dependency tree reports 33 warnings (8 moderate, 24 high, 1 critical); no forced upgrade/downgrade was applied.
- Local `vercel build` failed on Windows with `spawn cmd.exe ENOENT`; normal build and the actual Linux production deployment build passed.
- Stop/resume persistence, public gateway/SSE/model and fresh-browser checks pass, as recorded below. Near a session deadline, admission remains fail-closed if a safe action window cannot be reserved.
- Snapshot resume is not an independent backup or disaster-recovery test. Automatic recovery must fail closed if the known sandbox or runtime identity is missing.

Official references checked: [Sandbox SDK](https://vercel.com/docs/sandbox/sdk-reference), [managed images](https://vercel.com/docs/sandbox/concepts/images), [Docker support](https://vercel.com/sandbox), [persistence](https://vercel.com/docs/sandbox/concepts/persistence), [Drives](https://vercel.com/docs/sandbox/concepts/drives), and [pricing and quotas](https://vercel.com/docs/sandbox/pricing).

## Cloud and public verification

### Current UI refresh — 17 October IST

- Production deployment `dpl_8agnMEN2Wova7ZWKY714pggLtthy`, alias unchanged. Current runtime package `6178ebac…` differs only in frontend assets; API/worker/evaluator behavior and candidate isolation controls are unchanged.
- `artifacts/vercel/cloud-check-1792175348254.json`: origin authentication, isolation, timeout and memory enforcement, clean verification/export/replay, then persisted audit/bundle/counters/heartbeat and fresh replay after stop/resume passed again.
- `artifacts/ui-refresh-20261016/ui-check-1792175435125.json`: public fresh-profile rendering passed at 1440/1280/1024/768/390/320 px with no horizontal page/control overflow or heading overlap; actual Segoe UI faces recorded, Ctrl+K/Escape passed, dark OS preference did not break the fixed light palette.
- `artifacts/ui-refresh-20261016/browser-check-1792175610468.json`: clean audit `audit-731fed4687d1`, VERIFIED, bundle/hash validation, independent replay, ZIP download, SSE and reload restoration passed. Exactly one create, no browser exceptions or HTTP errors. ZIP SHA-256 `961f658a99d4abcc6ef59342c176f03a3c1e540779a6f8150bfc10a20ce40271`. Active-audit layouts also passed at 1440/768/390/320 px; desktop/mobile screenshots inspected.
- The preceding browser harness timeout (`browser-check-1792175560888.json`) is retained. Its click helper measured the target before smooth scrolling finished; explicit instant scrolling corrected the harness, without changing the deployed app or retrying model work. No inference call was made for this refresh; the earlier diagnosis HTTP 422 remains unresolved.

### Earlier deployment evidence

- `artifacts/vercel/cloud-check-1792146334676.json`: network/metadata denied, secrets/trusted assets absent, candidate read-only, timeout killed. Memory and swap are both 256 MiB, CPU 1 and pids 64; a deliberate 768 MiB allocation was OOM-killed (137). Audit, exact bundle hash, action counters and heartbeat survived stop/resume, and a fresh replay passed after restart.
- `artifacts/vercel/public-check-1792146557262.json`: cold gateway resume/readiness 4,744 ms; clean gate, ZIP hash, validation, replay and SSE passed; cross-owner audit/bundle access 403, private files 404, oversized body 413. Live Nemotron diagnosis supported the MC-01 amount hypothesis, with API-reported usage 547 prompt + 566 completion = 1,113 tokens (3,202 ms). This verifies diagnosis, not a measured model-authored repair result.
- Original production deployment: `dpl_8BdQHFuFQUAD4LTp3tv6EUGQAuFF`, alias `https://benchproof.vercel.app`. Subsequent gateway fixes retain the verified backend package and require public rechecks.
- Previous gateway deployment: `dpl_2iK7BZFvWMGv1KfCB2b96zZ5Lu14`. Fresh-browser record `artifacts/browser-vercel-20261016/browser-check-1792173340237.json` and screenshot `verified-journey.png`: cold parallel initialization, live-mode default, clean audit `audit-6c5a7e0d96e5`, VERIFIED gate, ZIP export/hash validation, fresh replay, authenticated ZIP download, processed SSE and reload restoration all pass. Exactly one create request, no browser exceptions or HTTP errors. Download SHA-256 `4b1b3aacc9747142c82ac0e390720e70eabbd0f98669a78bd3bf3a899985b182`. This is an automated fresh-profile test, not a volunteer usability study.
- Both failed browser records remain under `artifacts/browser-vercel-20261016/`: a case-sensitive harness assertion and a genuine readiness 503 under parallel reads. The lifetime fix rechecks control-plane state after a competing timeout extension and proceeds only if the full safe window remains. No user mutation is retried.
- The Linux output-permission fix changes runtime identity. Historical `eval-config-v1` is preserved; its verifier correctly reports `runtime_code_hash changed`. Commit/review the release and create a new configuration version before final measurements. Held-out assets still match lock `efe61ad8c4b0df56…`.
- A repeat public live diagnosis failed with HTTP 422 after the clean gate/export/replay/SSE/access checks passed: `artifacts/vercel/public-check-1792173417016.json`. The response detail was not captured, so the exact cause is unconfirmed. The original successful model record is not substituted for this failure; no blind model retry was made. Diagnosis/repair reliability remains a release gate.
- Final infrastructure-only public check `artifacts/vercel/public-check-1792174299345.json` passes the clean gate, ZIP/hash validation, fresh replay, SSE, access negatives and protected rejection of the faulty amount candidate. It explicitly records `--skip-provider` / model `NOT_RUN`, not a new inference success.

Repeat infrastructure checks without inference spend using `node deployment/vercel/public-check.mjs https://benchproof.vercel.app --skip-provider`. Omitting that flag performs a bounded real diagnosis and consumes provider credits; a model error must remain in its result record.

Hobby is quota-limited: documented allowances include 5 active CPU hours and 420 GB-hours of memory per month, with a 45-minute session maximum. This is not unlimited always-on hosting; no paid upgrade is enabled. Usage reserve, independent backup/restore, release publication, final measurements, complete rights review, video and submission remain release work.
