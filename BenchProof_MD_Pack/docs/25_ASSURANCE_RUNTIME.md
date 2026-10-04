# Assurance runtime specification

Version v2, 3 October 2026. This is the detailed implementation contract for the research-driven scope. It complements [architecture](04_ARCHITECTURE.md) and [API records](11_API_AND_DATA_CONTRACTS.md).

## 1. Human-owned executable constraints

Accepted constraints express task intent and expected behavior; they are not arbitrary model instructions. A repository may propose `.benchproof/contracts.json`, but intake treats it as untrusted until an owner approves it. Copy the approved version into the trusted registry, pin its hash, and bind it to the source/task. Candidate edits cannot change that copy.

Each constraint has an ID, version, plain-language behavior, scope, required/optional flag, protected check IDs, owner approval, and dependencies. Reject required constraints without executable trusted checks. Proposed new checks with no oracle remain UNREVIEWED and cannot support VERIFIED.

| ID | Fixture constraint | Protected check behavior |
| --- | --- | --- |
| C-API | Preserve declared response/status and required keys | Validate response schema, success/error statuses and versioned example compatibility |
| C-AMOUNT | Sum line amounts using Decimal from strings; ROUND_HALF_UP once at invoice total to two decimals; output fixed two-decimal string | Compute expected exact totals outside candidate for boundary and ordinary values |
| C-CALLER | Route and worker use the accepted shared amount semantics | Exercise both entry paths and compare contract outputs |
| C-IDEMPOTENCY | Same tenant/request ID and same payload returns original receipt without double count; conflicting payload rejects; different tenant stays separate | Controlled duplicate/conflict/cross-tenant inputs; bounded two-request concurrency case |
| C-INTEGRITY | Accepted policy, evaluator, image and base source remain pinned | Reject protected changes, missing results, wrong hashes and forged verdicts |

These are our synthetic fixture choices, not production payment standards. Constraints may be changed through a reviewed new version, never inside the current agent attempt. A new version invalidates older context/acceptance results.

## 2. Versioned engineering-state graph

Node types: File, Symbol, Contract, Test, Decision, Run, Patch. Stable keys include source/contract version where relevant. Symbol identity is qualified module/name plus source span; handle renamed or deleted nodes explicitly rather than retaining stale positions.

| Edge | Direction | Provenance |
| --- | --- | --- |
| defines | File → Symbol | OBSERVED from AST |
| imports | File/Symbol → File/Symbol | OBSERVED for supported static import forms |
| calls | Symbol → Symbol | INFERRED for resolvable direct calls; uncertainty recorded |
| implements | Symbol/File → Contract | DECLARED by reviewed manifest |
| protected_by | Contract/Symbol → Test | DECLARED mapping, validated against check registry |
| depends_on | Decision → File/Symbol/Contract | DECLARED with content hashes |
| changes | Patch → File/Symbol | OBSERVED normalized diff mapping |
| checked_by | Patch/Run → Test | OBSERVED execution record |
| supports | Run → Decision/Contract | OBSERVED evidence link, not a guarantee of truth |

UNKNOWN represents a coverage issue rather than an invented concrete dependency. Build AST import/definition maps, resolve supported calls, add reviewed links, validate referential integrity, then serialize sorted canonical records and a graph hash. Store in SQLite tables and export JSON; no graph database required.

Manifest coverage must name entry points, supported import/call patterns and excluded dynamic features. `COMPLETE_FOR_DECLARED_SCOPE` is permitted only when all required fixture relationships are accounted for under that manifest. Dynamic imports, reflection, monkeypatching, unresolved dispatch or parse errors yield PARTIAL/UNKNOWN. Do not equate graph coverage with behavioral correctness.

## 3. Blast radius and deterministic risk

Map changed spans to files/symbols. Traverse reverse callers/importers, then constraint and protected-check mappings. Include all mandatory global integrity checks even when traversal selects no node. Cap traversal and context size while recording truncated nodes; required checks are not removed merely to fit a prompt.

Repeat state/impact construction on the approved candidate snapshot after a diff, retaining its relationship to the original source. A new unresolved import/call cannot inherit COMPLETE_FOR_DECLARED_SCOPE from the base. Mutation branches have their own source hashes and never overwrite the candidate graph/verdict.

Risk rules return an ordinal and reasons, not a calibrated probability:

| Trigger | Initial severity | Required action |
| --- | --- | --- |
| Protected policy/evaluator/launcher edit or base-hash mismatch | CRITICAL | Reject patch or block stale attempt |
| Public schema change, money rule change, idempotency store/key change | HIGH | Mandatory relevant protected checks and regression callers |
| Unknown edge to required behavior or required check mapping absent | HIGH | Resolve manually or block that accepted scope |
| Shared helper affects multiple declared entry paths | MEDIUM, raised by contract criticality | Include each impacted entry-path check |
| Internal-only change with complete declared mapping | LOW | Still execute required global checks |

Combine by maximum triggered severity, retaining every reason. LOW is not a promise of safety. A user cannot click away a required check and retain the same accepted contract; narrowing scope needs a new approved manifest and a visible changed claim.

## 4. Decision ledger and context freshness

A decision contains ID, statement, accepted/proposed status, source/contract dependencies, evidence IDs, owner/role, created timestamp, superseded ID and revisit condition. An agent may propose a decision; it cannot authorize policy changes.

P0 verifies all source and contract hashes before each proposal and patch application. P1 compares each ledger dependency hash after a change. Deleted/changed dependencies mark the decision STALE. Unrelated file edits need not invalidate a correctly declared decision; unbounded dependencies should be avoided.

A context packet includes source/contract/graph hashes, current decisions only, affected code excerpts, required check IDs, unresolved coverage, recent concrete observations and remaining budget. Exclude hidden truth, secrets, stale decisions and private reasoning. If its dependencies change while a call is pending, discard that proposal for application and request a current packet within budget.

## 5. Trajectory and stagnation

Record each action: actor/role, validated tool, canonical arguments hash, source hash, context hash, observation/check IDs, failure category/fingerprint, elapsed time, usage and remaining limits. An action succeeds when it adds relevant evidence or resolves a required failure, not merely when the tool exits zero.

Initial stall rule: two consecutive attempts with the same relevant source hash, canonical action intent and normalized failure fingerprint, with no new relevant observation between them. Normalize unstable timestamps/request IDs out of fingerprints; preserve exception/check category, affected contract and salient diff. Test the rule on development traces and freeze before evaluation.

P0 enters STALLED and stops with an explanation and partial evidence. P1 allows one recovery: rebuild fresh context, expose the repeated observation, choose one different named probe or narrower diagnosis, record the changed strategy. It still consumes the original audit budgets. A second stall, unknown required context, or exhausted budget ends BLOCKED/INCONCLUSIVE. Never reset counters to simulate progress.

A changed patch that resolves one constraint while another remains failed is progress; the legitimate-progress control must not be flagged solely because the same test still fails. Synthetic traces evaluate classification only; actual executed runs are reported separately.

## 6. Independent adversarial acceptance

The analyst/repair role and adversarial proposal role use separate prompts/context views. This logical separation does not alone make a check independent. The final authority is a deterministic protected evaluator with trusted expectations that the candidate cannot rewrite.

Run candidate code in a fresh image under a protected launcher/transport. Keep oracle code and hidden expected values in the trusted evaluator. Send bounded test inputs to the candidate; inspect outputs and exits from outside. Validate response IDs/shape and associate results with the exact patch, contract and image. Candidate stdout claiming PASS is just text.

Run required integrity and behavior checks, then selected impact regressions. Fail required schema/value comparison → REJECTED. Missing result/timeout/unresolved oracle → INCONCLUSIVE. Missing accepted prerequisite → BLOCKED. All required checks PASS and manifests match → VERIFIED. NOT_RUN means no gate executed. Store results before rendering any explanation.

An adversarial model may suggest inputs or tests. Validate and approve them against a known oracle before promoting them to protected checks. Avoid calling two agreeing model opinions “independent verification.”

## 7. Trusted mutation testing

P1 uses twelve pre-authored semantic mutants: three each for API, amount, caller, and idempotency checks. Examples: drop a required response key; round line items instead of the total; bypass the worker's helper; remove tenant from a duplicate key. Author on development fixtures, prove mutation changes the intended behavior, and freeze before evaluation.

Execute up to three relevant templates per verification in fresh branches. Keep the accepted patch immutable. A mutant is KILLED only if a valid protected check fails for its intended behavioral deviation. A syntax/import crash caused by an invalid mutation is INVALID, not a killed success. A timeout with no adjudicated behavior is INCONCLUSIVE.

Report `killed / valid executed mutants`, plus survived, invalid, skipped and inconclusive counts. A high score means sensitivity to these selected regressions, not complete test coverage or proof of correctness. State which templates were used; never compare different subsets as identical scores. Missing required mutation coverage blocks an adequacy claim.

## 8. Machine-verifiable evidence

Bundle canonical manifest, approved constraints, graph/coverage subset, context hashes, decision ledger, structured trajectory, source/diff, check results, environment/model metadata, limitations, artifact SHA-256 hashes and REPLAY.md. Separate public evidence from withheld evaluation truth; release reproducible fixtures/checks after final measurement where rights permit.

Validate hashes and schemas without executing code. Executable replay requires the documented isolated runner and pinned dependencies. Hashes establish artifact consistency; without an authenticated signing scheme they do not prove who created a bundle. Do not describe SHA-256 as an anti-forgery signature.

Export no secrets, private reasoning, unapproved private source or hidden live benchmark truth. A replay reruns stated checks and may encounter provider/environment differences; report them honestly rather than editing the original result.

## Implementation order and acceptance

First implement schemas/contracts, source hashing and evaluator-negative checks. Next graph/impact and bounded NVIDIA repair. Then export/UI. Add P1 decision invalidation, recovery and mutants only after the complete protected loop works. Use [test plan](14_TEST_PLAN.md) and separated [evaluation suites](13_EVALUATION_PLAN.md); no runtime feature is considered built because its specification is detailed.
