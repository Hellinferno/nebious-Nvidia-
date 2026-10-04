# Evaluation and benchmark plan

No results exist yet. Thresholds are internal development targets, not promised performance, official judging requirements, or competitor scores. The research requires several separate evaluations rather than one inflated “agent accuracy” number.

## Questions and separated suites

| Suite | Size | Question |
| --- | --- | --- |
| R12 `repair-r12-v1` | 12 cases: 8 faulty, 4 clean; 3 trials each | Does the bounded system diagnose and repair without harming clean cases? |
| V12 `gate-v12-v1` | 12 fixed patches: 8 invalid, 4 valid | Does the protected gate catch invalid changes missed by smoke tests? |
| G8 `graph-g8-v1` | 8 changed-source tasks | Are expected impacted nodes/checks found in declared graph scope? |
| F6 `freshness-f6-v1` | 3 stale and 3 fresh transitions | Is relevant stale context blocked without invalidating unrelated context? |
| W8 `trajectory-w8-v1` | 4 stalls and 4 legitimate-progress traces | Does the rule stop repeated failure without stopping useful progress? |
| M12 `mutants-m12-v1` | 12 trusted mutants, 3 per repair family | Are the selected regression classes detected by the check set? |

R12 has **36 B2 agent trials: 24 faulty and 12 clean**. B1 also has 36. B0 has twelve deterministic visible-test runs. Verifier check executions and mutant runs are nested actions, not extra independent repair trials. Report unique cases as well as repeat trials.

P0 fallback R6 is six cases, four faulty/two clean, three trials each: 18 B1 and 18 B2 trials, twelve faulty/six clean per system, plus six B0 runs. Reduced V6 has four invalid/two valid candidates. Keep omitted assurance suites NOT_RUN. Choose scope and targets before measuring; never rename R6 as R12.

## Systems to compare

| ID | System | Information and actions |
| --- | --- | --- |
| B0 | Visible smoke-test gate | Same source/accepted task, fixed public checks; no model or repair |
| B1 | Same NVIDIA repair agent without assurance orchestration | Same task/constraints/source access and hard budgets; visible tests/probes, up to two patches; no state graph/decision ledger/stall recovery/protected acceptance feedback |
| B2 | BenchProof runtime | Same model and hard budgets; graph/current context, constraints, trajectory control, protected feedback and gate |
| A-G, optional | B2 without graph-selected context | Keep gate/feedback/model/budgets constant to isolate graph contribution |

B1 and B2 final candidate outcomes are judged by the same frozen independent evaluator outside their repair loop. B1 cannot decide its own success. B2 never sees hidden truth/check implementation; feedback is sanitized contract-level observations. State that the main comparison tests the whole assurance layer, not causality of an individual component. For component claims use a controlled ablation.

Give both model systems the same available source and declared constraints, token/call/execution/time/diff caps and primary model configuration. Graph formatting is a treatment, not extra secret information. Separate runtime feedback differences in the protocol. Do not weaken B1 by hiding task intent. No product version is included as an external competitor until [its protocol](26_COMPETITOR_BENCHMARK.md) is actually run.

## Metric definitions

| Metric | Numerator / denominator | Rule |
| --- | --- | --- |
| Correct diagnosis | Faulty trials identifying intended family with relevant evidence / all faulty trials | Invalid output, timeout and unsupported outcome remain in denominator |
| Finding precision | True confirmed category findings / all confirmed category findings | Deduplicate category within trial; unjustified extra categories count false |
| Verified repair | Faulty trials whose final candidate resolves intended failure and passes all accepted checks / all faulty trials | Primary repair metric; not only produced patches |
| Conditional repair success | Accepted correct repairs / trials with patch attempts | Secondary; always pair with unconditional result |
| Clean false confirmation | Clean trials with any falsely confirmed defect / all clean trials | Suspicion reported separately |
| Harmful clean modification | Clean trials with unjustified accepted change / all clean trials | Manual truth/source review in addition to gate |
| Invalid gate acceptance | Invalid fixed candidates accepted / all invalid candidates | Compare smoke and protected gate on same V12 records |
| Valid gate rejection/unknown | Valid fixed candidates rejected or unresolved / all valid candidates | Report false rejection separately from operational unknown |
| Graph recall/precision | Correctly selected expected nodes/checks / expected; correct selections / selected | Expected manifest frozen; unknown coverage and truncation separate |
| Freshness detection | Correct stale flags / 3 stale transitions; incorrect stale flags / 3 fresh | Do not merge into repair success |
| Stall detection | Correct stopped stalls / 4 stalls; false stops / 4 progressing traces | Synthetic classification and executed recovery outcomes separate |
| Mutation sensitivity | Killed mutants / valid executed mutants | Invalid/skipped/inconclusive do not count killed; show all counts |
| Replay | Successful fresh replays / preselected exports | Selected failures remain in denominator |
| Latency/usage | Queue/active wall time, tokens, executions and priced cost per trial | Include failures; unknown cost is unknown |

For diagnosis, an independent assessor uses frozen truth and observation support. A fluent correct guess without relevant evidence is not the same as an executed confirmed contract failure; report claim-only findings separately.

## Internal target gates

Before final measurement set these ambitious but unvalidated R12 targets: correct diagnosis >=21/24 faulty B2 trials; verified repair >=20/24; clean false confirmation 0/12; harmful accepted clean change 0/12; unsupported VERIFIED verdict zero. Reduced R6 targets: diagnosis >=10/12, repair >=9/12, clean false confirmation 0/6 and harmful accepted clean change 0/6.

V12 target: protected invalid acceptance 0/8 and correct valid acceptance 4/4; V6 target 0/4 and 2/2. Demonstrate at least one fixed candidate where smoke accepts and protected gate rejects, without generalizing from that one example. G8/F6/W8 aim for correct declared mappings/classification on all their frozen small cases; report actual counts if missed. Mutation adequacy is the predeclared relevant templates killed, with any survivor exposed.

Replay selection: one accepted export from each implemented repair family, one clean case, every video export, and one rejection/limited result where available. Require all selected replays to match the stated check outcomes or document a discrepancy. Three consecutive live hero rehearsals pass. Median active time target <=120 seconds and p95 <=300 seconds, with sample size and cold/warm split; correctness takes precedence.

If targets fail, report actual outcomes and narrow claims. Do not discard a seed, raise a tolerance or quietly replace a case to obtain a passing report. A null/negative improvement versus B1 is a valid finding.

## Protocol and budget

1. Validate development fixtures/reference repairs and negative evaluator checks.
2. Freeze suite source, trusted categories/oracles, graph truth, traces and mutants on 17 October.
3. Freeze evaluated commit, prompts, model/parameters, runner image, accepted constraints, thresholds and budgets on 20 October.
4. Estimate twelve B0 + 36 B1 + 36 B2 runs and separate suite execution costs; preserve judging reserves. Use explicit R6/V6 fallback if needed.
5. Run predetermined trial indices in balanced order to reduce warm/cache/provider effects. Do not select outcomes after observing them.
6. Save one immutable attempt record with every timeout, provider failure, diff, verdict and usage. Classify pre-action infrastructure failures and product failures, reporting both.
7. Compute summaries from records, check small-sample arithmetic manually, inspect every accepted patch for harness gaming, and replay the preselected exports.
8. Publish suite/configuration IDs, actual counts, limitations and failed examples. Release sufficient synthetic source/checks for reproducibility after evaluation.

An ambiguous submission or failed action cannot disappear into an undocumented retry. Recovery is within the original trial and budget; a new independent trial is explicitly numbered and counted.

## Release changes and uncertainty

Functional changes to prompts, graph/context selection, policy, check/oracle, model or runner require affected versioned reruns. UI/docs-only changes need appropriate checks, not an automatic full benchmark. If final outcomes were used to tune, call later runs regression evaluation or obtain fresh held-out variants.

Twelve synthetic cases do not establish broad product reliability. Three repeats of one case are not three independent problems. Report unique-case and worst-family behavior; use intervals only with clear sampling assumptions. Risk levels are deterministic rules, not validated failure probabilities. Optional agent comparisons need versions/access and cannot be inferred from desk research.

## Result tables to fill

| System | Unique repair cases | Trials | Correct diagnosis | Verified repair | Clean false confirmation | Latency/usage |
| --- | --- | --- | --- | --- | --- | --- |
| B0 visible tests | Not run | Not run | Not measured | N/A | Not measured | Not measured |
| B1 same agent | Not run | Not run | Not measured | Not measured | Not measured | Not measured |
| B2 runtime | Not run | Not run | Not measured | Not measured | Not measured | Not measured |

| Assurance suite | Outcome | Artifact |
| --- | --- | --- |
| V12 / G8 / F6 / W8 / M12 | Not run; fill separately | None yet |
| Fresh replay / executed recovery | Not run; identify actual sample | None yet |
