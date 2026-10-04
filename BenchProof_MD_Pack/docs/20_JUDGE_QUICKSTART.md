# Judge testing guide — release template

This is a specification to finalize before submission. It currently provides no live URL or runnable application. Replace targets with actual tested instructions from the release; do not publish broken placeholder commands as setup.

## Purpose and supported scope

BenchProof checks a proposed Python service change against explicit engineering constraints and reports independent acceptance evidence. The example uses entirely synthetic invoice inputs. Its coverage is the declared API/amount/caller/idempotency scope actually implemented, not every possible software defect.

## Release information to fill

| Item | Release value |
| --- | --- |
| Demo/test-build URL and access path | Not deployed |
| Public repository, license, release tag/commit | Not published |
| Runtime NVIDIA model/provider | Not selected/tested |
| Candidate runner and image/policy | Not tested |
| Accepted constraint/evaluator version | Not implemented |
| Implemented P0/P1 features and exclusions | Fill from release |
| Evaluation suites/results | Not measured |
| Evidence bundle/replay instructions | Not implemented |

## Hosted path to verify

1. Open the final URL without signing into Ravi's account. Read scope and live/recorded mode.
2. Select the invoice boundary example and inspect the accepted amount/API constraints.
3. Start assurance. Inspect the affected route/helper/worker and any graph coverage limits.
4. Open the candidate failure: identify the required check and its concrete observation.
5. Review the model-proposed diff and request fresh verification.
6. Inspect PASS/FAIL/UNKNOWN rows, gate verdict and optional mutation strength.
7. Download evidence and open the manifest/replay guide.
8. Try the clean control and deliberately inadequate candidate. Confirm that clean behavior need not trigger a patch and a failed required check is rejected.

If P1 exists, a separate example can show a stale decision or stalled loop. Label absent features NOT_RUN/unsupported. A recorded evidence view is marked; give the working live test path separately.

## Local installation to complete

The final README must include exact tested Python/Node versions, locked dependency installation, server environment keys without secrets, database initialization, worker/API/frontend startup, provider/runner access requirements and public/developer mode restrictions. Add the actual clone URL and release tag after publication.

Prerequisites may include account access for real isolated execution and inference. Reviewer hosted access should remain free as required by the event. Mocks may support local development but do not reproduce live model/execution claims.

## Independent replay

First validate bundle schema/hashes without executing code. Then follow REPLAY.md in an approved isolated runner with the pinned source/diff, accepted constraints, evaluator and image. Recompute declared check outcomes and save a new replay record linked to the original.

No provider secret is embedded in the bundle. Hash consistency does not authenticate the author or prove every behavior correct. State any removed private assets, unavailable image, model nondeterminism or environment mismatch. Replay of accepted code checks does not necessarily regenerate an identical stochastic agent proposal.

## Interpreting results

VERIFIED means all required checks passed for the identified version/scope. REJECTED means a required behavior failed. INCONCLUSIVE means evidence was insufficient; BLOCKED means a prerequisite/mapping was absent. Run completion is separate from acceptance. Graph coverage, freshness and mutation strength are separate fields with explicit limits.

Benchmark claims identify R12/R6 and separate assurance suites with their own denominators. Do not infer general reliability from a small synthetic suite. “Proof bundle” is a convenient name for replayable evidence, not a formal universal proof.

## Access acceptance before submission

- [ ] Incognito hosted core journey works with no private account dependency.
- [ ] Release-only clean clone follows final README successfully.
- [ ] Faulty, clean and rejected/limited outcomes match instructions.
- [ ] Export/hash check and fresh executable replay pass for stated checks.
- [ ] Limits, errors, queue/cancel and recorded fallback are clear.
- [ ] Links and free access remain available through the judging period.

Support/contact details belong here only when Ravi selects an actual public contact. No contact message or invitation is sent by creating this guide.
