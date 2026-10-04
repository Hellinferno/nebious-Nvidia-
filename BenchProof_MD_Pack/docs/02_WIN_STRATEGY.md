# Competitive strategy and judge evidence

This is a build strategy, not a prediction of prizes. Official criteria are in [event requirements](01_HACKATHON_REQUIREMENTS.md); primary-source competitor findings are in [research](24_RESEARCH_AND_POSITIONING.md).

## Positioning

Use a concrete claim: “BenchProof checks whether an agent's change still satisfies the engineering contracts you accepted, then gives you the evidence.” Demonstrate a shallow passing patch rejected for a real missed constraint, a useful repair, and a clean result.

Avoid positioning ordinary memory, agents, cloud execution, or repository context as our invention. The proposed contribution is their connection to immutable checks, stale-state detection, constrained recovery, and replayable evidence. We must earn that claim in the implemented scope.

## Evidence by criterion

| Criterion | Claim to earn | Judge-visible evidence | Internal gate |
| --- | --- | --- | --- |
| Implementation | The runtime orchestrates useful code work and a trustworthy acceptance gate | Real NVIDIA action, bounded runner, graph-linked checks, rejected candidate, fresh verified repair | Complete P0 and three consecutive hero runs |
| Design | A developer can make a clear accept/reject/review decision | Plain constraint failure, impact view, diff, check table, limits and export | Tester completes the core path without coaching |
| Impact | A specific review failure is caught efficiently | Fixed invalid patch corpus, baseline comparison, observed tester task | Report actual counts and user observations; disclose unavailable study |
| Idea quality | Constraint/state/trajectory/evidence form a coherent layer | Source-linked constraint, decision freshness, recovery, independent result | Explain the linkage in 20 seconds; qualify exclusions |

## Four memorable moments

1. “Visible tests passed” is displayed alongside a protected contract failure, with one tiny counterexample.
2. The impact view shows the other caller affected by the changed helper and the check protecting it.
3. The NVIDIA repair passes a fresh independent gate; an unresolved check produces a limited or blocked verdict instead of a success badge.
4. The judge downloads evidence and sees exactly which version and checks the verdict covers.

If P1 is stable, insert one stale decision or repeated-failure example. Do not squeeze every component into the main video at the expense of a complete journey.

## Prove model contribution

Record the provider call that selects useful investigation or authors a repair. Compare the same NVIDIA agent with and without the assurance layer using shared information and budgets. Use a common external evaluator for outcome measurement so BenchProof does not judge itself more favorably.

Report deterministic rule contribution honestly. If a simple check catches a fault, that is useful engineering; it is not evidence that a model discovered it. If optional external-agent trials are unavailable, publish the documented landscape and internal baseline results without invented product rankings.

## Priority order

| Must work | Should work after P0 | Optional |
| --- | --- | --- |
| Real inference/execution, two repair families, clean/rejected paths, protected gate, UI/export | Four families, invalidation/recovery, mutations, frozen suites, user sessions | Extra model tier, more agent adapters, large graph visualization |

Keep one honest failure example in the report. A machine-readable ledger and an independent replay are more valuable than a crowded agent animation. Preserve the 25 October freeze and 28 October submission buffer.

## Readiness review

Score each criterion internally from 0 to 3: missing; partially demonstrated; complete once; repeatable with evidence and limitations. These are not the organizer's scoring formula. On 10, 17, and 24 October, fix the weakest criterion with an unmet P0 dependency before adding breadth.

Before publishing, every quantitative claim needs a saved numerator, denominator, suite/configuration version, and failures. Latency requires sample size and cold/warm definition; cost requires actual usage and a price snapshot. User value requires an observed task or explicit hypothesis label. No “better than Cursor/Codex/etc.” without the [fair optional protocol](26_COMPETITOR_BENCHMARK.md).
