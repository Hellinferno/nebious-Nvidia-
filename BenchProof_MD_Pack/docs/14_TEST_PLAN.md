# Correctness, isolation, and release tests

Tests protect the assurance boundary and meaningful behavior. They are implementation tasks, not completed checks. Benchmark scoring remains separate from regression tests.

## Critical test layers

| Layer | Meaningful checks |
| --- | --- |
| Schemas/store | Required hashes/check mappings, no candidate writes to verdict, owner relations and conditional transitions |
| Contracts | Unapproved manifest blocked; required check missing blocked; accepted version cannot be rewritten by diff |
| Graph/impact | Imports/direct calls/declared mappings, caller selection, deleted nodes, unresolved dynamic edge, coverage/truncation visibility |
| Freshness | Changed dependency invalidates decision/context; unrelated change does not; delayed stale proposal cannot apply |
| Trajectory | Same no-progress fingerprint stalls; meaningful new evidence progresses; one recovery max and budgets unchanged |
| Runner | Timeout/memory/output/network/metadata denial, fresh candidate state, operation reconciliation |
| Gate | Expected behavior outside candidate; wrong/missing/forged output cannot yield VERIFIED |
| Mutations | Valid semantic deviation, killed versus invalid/survived/unknown distinction, candidate restored |
| Evidence | Schema/hash consistency, tamper detection, safe archive paths, omissions and owner access |
| UI/API | Reload/reconnect/cancel, clean/rejected/limited result and real-mode display |

## Fixture-family checks

AC: required response fields, accepted status/error behavior and declared backward compatibility. MC: Decimal input, total-level rounding and two-decimal string formatting including `0.005 + 0.005 = 0.01`. CI: both route and worker obey shared semantics even after a helper change. ID: identical repeat, payload conflict, cross-tenant key reuse and controlled concurrent duplicate behavior.

Clean controls pass without an unnecessary patch. A reference repair passes all required checks, not merely the check it targets. Separate source freshness from scoped replay determinism; no removed ML split/label policy remains an active test.

## Independent-verifier negative cases

- Candidate prints “PASS,” fabricates a result JSON or alters output IDs; the trusted gate evaluates actual behavior and rejects/marks unknown.
- Patch edits test/oracle/constraints/launcher or removes mandatory regression mapping; policy rejects before execution.
- Final run has wrong base/diff/contract/image/evaluator hash; acceptance is blocked.
- One required check times out, is missing or cannot compute expected behavior; result cannot be VERIFIED.
- Generated adversarial case has no trusted oracle; it remains a proposal.
- Mutant fails import due to invalid generation; it is INVALID, not a claimed detection success.
- Required graph mapping is unresolved; graph “no affected nodes” cannot waive a contract.

## Lifecycle and budget checks

Lost worker lease does not cause duplicate paid execution. Unknown remote submission reconciles before retry. Cancellation is honored before next action and retains partial evidence. Crash between check storage and event emission restores consistent snapshot. Counters include retries, verification and mutants; recovery cannot reset time/cost/action limits.

An audit hitting the 300-second target with unfinished mandatory work yields TIMED_OUT/INCONCLUSIVE. A twelve-execution allowance does not authorize exceeding wall/cost caps. Validate source/diff/context boundaries and conservative cost reservation.

## Public access and manual checks

Try cross-session run/event/patch/export access, malformed IDs, traversal and arbitrary callback/source URLs. Confirm denial. Scan build, prompts, logs and bundle for credentials. Test public curated-only intake, incognito journey, keyboard navigation, readable mobile diff, SSE reconnect and download.

Run three live hero repetitions plus clean and rejected/limited outcomes on the release candidate. Test restore from backup and one fresh bundle replay. Optional graph animation is not a release gate.

## Planned commands and release record

After implementation, expose appropriate backend test groups and frontend checks, for example:

```powershell
python -m pytest tests/contracts tests/evaluator tests/runtime tests/state
python scripts/provider_preflight.py
python scripts/runner_preflight.py
python scripts/replay_bundle.py --bundle artifacts/release-hero.zip
```

Use the real installed package layout and actual frontend script names in the final README. Do not claim these commands ran from a documentation-only pack.

Record date, tested commit/model/runner, selected checks, passed/failed/skipped/blocked counts, sanitized artifact paths, defects and scope decision. Repeat checks when changes affect their boundary; broaden testing only for unresolved concerns or new failures.
