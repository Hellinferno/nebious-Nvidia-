# Judge testing guide — current demo

Updated 16 October 2026. Open [BenchProof](https://benchproof.vercel.app), with no private Vercel account required. The UI and persistent backend run in Vercel independently of the owner's laptop; actual inference uses Nebius Token Factory. A fresh-browser cold-start/core journey passed. Hobby quotas and model credits still limit availability; see [cloud operations and evidence](../../VERCEL_DEPLOYMENT.md).

Known live limitation: a later diagnosis request returned HTTP 422 after an earlier
meaningful NVIDIA diagnosis passed. Both records are retained. Treat a model error
as a failed action, never a successful diagnosis; clean verification and evidence
replay remain independent of a model response.

## Purpose and supported scope

BenchProof checks a proposed Python service change against explicit engineering constraints and reports independent acceptance evidence. The example uses entirely synthetic invoice inputs. Its coverage is the declared API/amount/caller/idempotency scope actually implemented, not every possible software defect.

## Current release information

| Item | Release value |
| --- | --- |
| Demo/test-build URL and access path | https://benchproof.vercel.app ; public production alias, no private login required |
| Source/license | Repository remote: https://github.com/Hellinferno/nebious-Nvidia- ; local Apache-2.0 LICENSE/NOTICE added, not yet pushed or tagged |
| Runtime NVIDIA model/provider | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` on Nebius Token Factory; live inference tested 16 Oct |
| Candidate runner and image/policy | Docker inside trusted Vercel Sandbox, `sha256:e97eb0d1e5902fe17fc632d0376d325d2584fb7f6cc1f919199c0c9a9bcbd68f`; network none, 256 MiB memory/swap, 1 CPU, 64 pids, read-only candidate |
| Accepted constraint/evaluator version | Contract `6d5b95ce4dbc2dba…`, evaluator `279684675b8c44e3…`; full identities in the evaluation configuration |
| Implemented scope | Curated API/amount/caller/idempotency fixtures, graph/impact, bounded diagnosis, restricted patch import, gate, decision freshness, stopping/recovery, optional mutations, export/replay |
| Evaluation suites/results | Assets remain frozen; historical local configuration does not cover the Linux compatibility fix/image. A new release configuration and final held-out trials remain pending |
| Evidence bundle/replay instructions | Export/validate/replay available in UI; fresh clean public-API export/replay passed 16 Oct |

## Hosted path to verify

1. Open the final URL without signing into Ravi's account. Read scope and live/recorded mode.
2. Select the invoice boundary example and inspect the accepted amount/API constraints.
3. Start assurance. Inspect the affected route/helper/worker and any graph coverage limits.
4. Open the candidate failure: identify the required check and its concrete observation.
5. Review the proposed diff and its provenance, then request fresh verification. UI development repairs are canonical references, not newly model-generated patches; live model-authored repair evidence is recorded separately.
6. Inspect PASS/FAIL/UNKNOWN rows, gate verdict and optional mutation strength.
7. Download evidence and open the manifest/replay guide.
8. Try the clean control and deliberately inadequate candidate. Confirm that clean behavior need not trigger a patch and a failed required check is rejected.

If P1 exists, a separate example can show a stale decision or stalled loop. Label absent features NOT_RUN/unsupported. A recorded evidence view is marked; give the working live test path separately.

## Local installation

Follow the [repository README](../../README.md) for Python 3.12, Node, locked dependency installation and provider/runner setup. Follow [DEMO_HOSTING.md](../../DEMO_HOSTING.md) to build the UI and serve UI/API together. The current public demo has a separate SQLite store and a shared daily action cap; repeated actions may return `429 DEMO_BUSY` or `429 DEMO_DAILY_LIMIT`. A clean-clone installation and final release tag remain pending.

Prerequisites may include account access for real isolated execution and inference. Reviewer hosted access should remain free as required by the event. Mocks may support local development but do not reproduce live model/execution claims.

## Independent replay

First validate bundle schema/hashes without executing code. Then follow REPLAY.md in an approved isolated runner with the pinned source/diff, accepted constraints, evaluator and image. Recompute declared check outcomes and save a new replay record linked to the original.

No provider secret is embedded in the bundle. Hash consistency does not authenticate the author or prove every behavior correct. The command `python scripts/run_bundle_replay.py` from `backend` produces three new canonical-reference exports/replays and a tamper negative in a new directory, without changing the application database. These reference repairs are not model-generated repairs. Replay of accepted code checks does not necessarily regenerate an identical stochastic agent proposal.

## Interpreting results

VERIFIED means all required checks passed for the identified version/scope. REJECTED means a required behavior failed. INCONCLUSIVE means evidence was insufficient; BLOCKED means a prerequisite/mapping was absent. Run completion is separate from acceptance. Graph coverage, freshness and mutation strength are separate fields with explicit limits.

Benchmark claims identify R12/R6 and separate assurance suites with their own denominators. Do not infer general reliability from a small synthetic suite. “Proof bundle” is a convenient name for replayable evidence, not a formal universal proof.

## Access acceptance before submission

- [x] Automated fresh-profile hosted core journey works without a private account: clean create/verify/export/validate/replay/download/reload and SSE pass (16 Oct).
- [ ] Release-only clean clone follows final README successfully.
- [ ] Faulty, clean and rejected/limited outcomes match instructions.
- [x] Export/hash check and fresh executable replay pass: cloud fresh-browser audit `audit-6c5a7e0d96e5`; canonical-reference replays and earlier fallback checks remain separate evidence.
- [ ] Limits, errors, queue/cancel and recorded fallback are clear.
- [ ] Links and free access remain available through the judging period.

Support/contact details belong here only when Ravi selects an actual public contact. No contact message or invitation is sent by creating this guide.
