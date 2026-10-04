# Deployment, operations, and recovery

The research revision adds protected contracts, graph/decision versions, trajectory records and mutation policy to deployment. A running UI alone is not a working assurance runtime. All deployment steps remain pending.

## Target topology and selection gate

Serve the built UI through HTTPS; run FastAPI and one supervised durable worker with persistent SQLite/artifact storage; execute candidates through the isolated provider adapter. Keep protected evaluator/oracle assets in the trusted worker/evaluator zone, never candidate mounts. Use real NVIDIA inference on Token Factory.

By 6 October choose a host with persistent disk, background-process supervision, secret configuration, supported request/event timeouts and affordable judging lifetime. An ephemeral/serverless filesystem cannot be treated as durable SQLite. If host requirements differ, record a tested database/artifact route before proceeding.

Confirm Contree access/controls or the actually provisionable isolated Nebius AI Cloud alternate. A requested beta account, untested container or mock does not satisfy the final path. Use allowlisted endpoints and pinned image digests; no candidate-selected provider URL.

## Pre-deploy configuration

- Record release commit, lockfiles, schema migration version, accepted contract/check registry, state-builder and fingerprint-rule versions.
- Build trusted candidate image with approved dependencies and protected launch transport; keep oracle code outside it. Record digest and enforcement tests.
- Set inference/runner secrets server-side; no frontend key. Configure model ID only after live preflight.
- Enable public curated mode, exact origin policy, session ownership and conservative global/session quotas.
- Set durable artifact/database directory, backup destination, action/time/cost limits and retention policy.
- Freeze public examples with source/contract/graph hashes. Preserve hidden evaluation assets outside public build context.

## Deployment sequence — 19 October

1. Back up current store/artifacts; record previous deployment and rollback configuration.
2. Install locked backend/frontend dependencies and build the exact candidate release.
3. Apply tested schema migrations; start API then worker; check heartbeat and configuration readiness without billed polling.
4. Run one real inference and bounded runner preflight; check image/model and cleanup.
5. Run public faulty/clean/rejected examples from incognito; inspect constraints, impact, diff, gate and export.
6. Test reload/SSE reconnect, owner checks, cancellation and budget-stop behavior.
7. Restart worker and reconcile remote operations; restore one backup in a separate test location.
8. Save URL, commit/configuration hashes, timestamps, checks and limitations in the progress log.

Use the same runtime for live demo and measured release. Do not deploy a hardcoded success path that bypasses the trusted gate.

## Modes and monitoring

LIVE runs actual inference/execution. RECORDED shows immutable genuine evidence and is clearly labeled. MOCK is development-only and not the default public judging route. A recorded fallback can keep evidence readable during outage, but does not replace a working test-build requirement.

Monitor API/worker health, lease age, queue wait, remote operation count, error category, stale-context blocks, stalls/recovery, verifier unknowns, budget exhaustion and artifact storage. Record model tokens/runner billing units; sample safe logs. Alert content must never include credentials or hidden truth.

Readiness fails when the required runner, accepted check registry or persistent store is absent. Catalog availability changes require an explicit tested model update; no silent fallback to another provider/model under the old result label.

## Persistence and backup

Back up SQLite consistently using its supported backup mechanism, artifact directory and accepted contract/evaluator versions. Keep a recovery manifest with hashes and release linkage. Verify restore before release. Graphs may be reproducible, but decision/action/result records must be retained; rebuild derived state from source plus accepted manifest without rewriting history.

Store partial failed/cancelled attempts. Public artifacts have bounded retention and owner access; frozen benchmark and submitted-release evidence are preserved longer. Remove secrets via prevention, not by assuming backups are private enough.

## Recovery procedures

| Incident | Action | Completion evidence |
| --- | --- | --- |
| Provider outage | Stop new paid actions, show clear error and recorded evidence, bounded retry when known safe | Live preflight restored; no duplicated unknown operation |
| Worker restart/lost lease | Reconcile persisted remote IDs, mark interrupted, offer linked resume | One owner/attempt, counters and artifacts retained |
| Stale graph/context | Invalidate dependent state, rebuild from pinned current source/contract | Current hashes and coverage report; old acceptance not reused |
| Evaluator/policy mismatch | Block verification, restore tested matching release or create versioned update | Negative integrity checks pass; affected claims rerun |
| Disk/storage failure | Stop new runs; restore tested backup and validate manifests | Result/artifact association and fresh smoke/export |
| Bad deployment | Roll back source plus compatible schema/config/image | Incognito core journey and live gate pass |

Do not call cancellation complete until termination/reconciliation is established. A job with unknown required check status cannot inherit the previous patch's VERIFIED label.

## Judging access

Keep the submitted release free to reviewers through the period in [event requirements](01_HACKATHON_REQUIREMENTS.md), plus an operational margin. Verify credit expiry, hosting payment conditions and reserve before 25 October. Retain stable URL, source tag, bundle and video. Maintain future work separately so the submitted behavior is not silently replaced.
