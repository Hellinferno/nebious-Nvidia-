# Product requirements

Version: research-aligned v2, 3 October 2026. All capabilities are planned until implemented and recorded. Detailed deterministic semantics live in [runtime specification](25_ASSURANCE_RUNTIME.md).

## Primary journey

Select a curated service and candidate/task → inspect pinned constraints → start bounded assurance → see impacted code and coverage → inspect a failure → review a proposed repair → request fresh verification → read an explicit acceptance decision → export evidence. A clean case should end without a gratuitous repair.

## Stories and acceptance

| ID | User need | Acceptance evidence |
| --- | --- | --- |
| U-01 | Know the check's scope | UI shows source hash, contract version, supported Python scope, input limits and live/mock mode before start |
| U-02 | Turn intent into enforceable constraints | Accepted manifest is pinned; each required contract maps to a protected executable check; candidate cannot edit it |
| U-03 | Understand change impact | Changed symbols link to affected callers/checks with edge provenance and unresolved-dependency notice |
| U-04 | Avoid outdated engineering context | Source/contract mismatch blocks reuse; P1 dependency changes mark ledger decisions stale and rebuild context |
| U-05 | Avoid endless attempts | Same source/action/failure fingerprint twice without new evidence triggers STALLED; caps stop every path |
| U-06 | Review a useful repair | Diff is small, source-hash-bound, within allowed files and linked to failed constraints |
| U-07 | Trust acceptance | Fresh runner plus separate trusted evaluator; failed, missing, timed-out or unverifiable required checks cannot yield VERIFIED |
| U-08 | Inspect verification strength | P1 trusted-mutant kill/survival counts are separate from contract results; invalid mutants are excluded and recorded |
| U-09 | Reproduce the decision | Export contains hashes, checks, versions, limitations and replay steps; tampered artifact is detected |
| U-10 | Use another coding agent later | Patch/trajectory records have provider-neutral schema; actual product adapters remain optional |
| U-11 | Recover from UI errors | Reload/reconnect restores existing run; cancellation reconciles remote work; no hidden paid duplicate |

## Priority scope

P0: curated synthetic service; API and exact-amount repair families; accepted contracts; Python AST/manifest graph; source freshness; deterministic impact/risk reasons; one real NVIDIA provider; isolated baseline/probe/repair; restricted diff; independent gate; repeated-failure stop; ownership, budgets and cancel; clean/rejected/blocked states; UI; evidence export and replay.

P1: cross-module caller and tenant-scoped idempotency families; decision ledger invalidation; eight trajectory tests and one bounded recovery; trusted mutation strength checks; full separated evaluation suites; observed usability fixes.

P2: additional external-agent adapters; second NVIDIA tier after measurement; deeper graph navigation; another language; an authorized small external repository case study. P2 never replaces release/access work.

## Decision vocabulary

| Field | Values | Meaning |
| --- | --- | --- |
| Run state | QUEUED, PREPARING, ANALYZING, INVESTIGATING, PATCH_READY, VERIFYING, STALLED, COMPLETED, FAILED, CANCELLED, TIMED_OUT | Lifecycle only |
| Gate verdict | VERIFIED, REJECTED, INCONCLUSIVE, BLOCKED, NOT_RUN | Required checks passed; definitive failure; insufficient evidence; prerequisite absent; not attempted |
| Finding | SUSPECTED, CONFIRMED, REFUTED, UNRESOLVED | Observation-backed diagnosis, distinct from patch acceptance |
| Graph coverage | COMPLETE_FOR_DECLARED_SCOPE, PARTIAL, UNKNOWN | Completeness within the explicit fixture manifest only |
| Decision freshness | CURRENT, STALE, UNREVIEWED | Dependency hashes valid; changed; not reviewed |
| Test strength | NOT_RUN, ADEQUATE_FOR_DECLARED_MUTANTS, WEAK, INCONCLUSIVE | Bounded mutation assessment, never a universal guarantee |

VERIFIED covers every required check in the accepted contract on that source/diff/environment. Optional checks and mutations are separate. For P1, when mutation adequacy is a mandatory release contract, a surviving required mutant prevents VERIFIED; when optional, a VERIFIED contract result may coexist with WEAK test strength, explained explicitly. No partial pass is renamed VERIFIED.

## Proposed resource contract

| Limit | Initial target | Enforcement |
| --- | --- | --- |
| Source | 10 MB, 100 text files | Intake before model/runner use |
| Candidate diff | 200 changed lines, 20 KB | Normalized parser and approved paths |
| Candidate execution | 60 seconds, 2 GB RAM | Tested runner policy; no assumed enforcement |
| Audit active work | 300 seconds | Deadline before every action and poll |
| Model calls / executions | 12 / 12 per audit | Includes retries, baseline, final and mutant runs |
| Patch attempts / parallel branches | 2 / 2 | Durable counters and reservations |
| Trusted mutants | Up to 3 relevant templates per verification | Counts within execution budget |
| Model input / output | 16,000 / 2,000 tokens per call initially | Adapter limits and measured tokenizer support |
| Cost | Configured after actual pricing | Worst-case reservation plus reconciliation |

Freeze or revise measured limits before final evaluation. A 300-second budget can stop work before the twelve-action caps; unfinished checks stay unfinished. A lower-scope live run is preferable to claiming a limit the backend cannot enforce.

## Release criteria

P0 must demonstrate two different defect repairs, a correct clean outcome, an independently rejected candidate, a no-success-on-unknown path, and a replayable export. Source/policy/evaluator tampering and cross-session access are blocked. Three live hero rehearsals pass. Benchmark claims use the actual selected suite. Deployment, free testing access, license, video, and entry requirements are satisfied separately; documentation alone satisfies none of those gates.
