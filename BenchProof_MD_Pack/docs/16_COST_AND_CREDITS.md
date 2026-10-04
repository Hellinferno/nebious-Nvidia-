# Credits, usage, and cost controls

This is a planning budget, not authorization to spend money. No credits have been requested or granted as part of this documentation work.

## Verified credit route

The [official resources page](https://nebiusglobalaihackathon.devpost.com/resources) lists a form for $25 Token Factory credits with activation code `NEBIUS-DEVPOST-GLOBAL26`, plus another $25 through the Builder Program. Treat these as offered application routes, not confirmed balances. Record actual grants, expiry, service eligibility, and restrictions.

The [billing documentation](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new) describes card-based onboarding, promo expiry, and automatic charging conditions. Ravi should check the current account controls before running bulk experiments. Token Factory, Sandboxes, AI Cloud, Tavily, and application hosting balances may be separate; do not assume a credit for one pays another.

## Account ledger

| Resource | Confirmed balance | Expiry | Eligible services | Owner check |
| --- | --- | --- | --- | --- |
| Token Factory | Not confirmed | Not confirmed | Not confirmed | 4 Oct |
| Sandboxes | Access/cost not confirmed | Not confirmed | Not confirmed | 4–6 Oct |
| Nebius AI Cloud | Not confirmed | Not confirmed | Not confirmed | Only if required |
| Application hosting | Not selected | Not confirmed | Not confirmed | By 6 Oct |
| Optional services | Not selected | Not confirmed | Not confirmed | P2 only |

Do not use the previously reported AWS $100 credit balance as funding evidence for this event.

## Proposed allocation

Allocate only from credits actually granted and usable for the relevant service:

- 15%: onboarding, model selection, runner preflight.
- 35%: development contracts, graph/context and repair tuning.
- 20%: frozen benchmark and replay.
- 10%: rehearsal and release smoke tests.
- 20%: judging-access reserve and unexpected repairs.

If that reserve cannot support the judging period, revise the plan before submission. A short-lived promotional balance is not a hosting strategy.

## Per-audit cost calculation

For model m, record input tokens `I_m`, output tokens `O_m`, and dated prices `P_in_m`, `P_out_m` in dollars per million tokens:

`inference_cost = sum((I_m × P_in_m + O_m × P_out_m) / 1,000,000)`

Add measured sandbox/compute usage at its actual billing units, storage/egress if applicable, and hosting allocation if reporting fully loaded cost. Some endpoints include reasoning tokens or cache-specific pricing; follow actual reported usage semantics. Unknown costs remain unknown.

## Enforced limits

Before each remote action, reserve a conservative upper bound from the remaining audit and daily budget. Reject work if the upper bound would exceed the cap. Reconcile actual usage afterward. A total call cap alone does not bound spend if the context size is unlimited.

Bound input context and output tokens. Retry counts include their usage. Limit concurrent audits and remote operations. Count final verification reruns in the execution allowance. Record interrupted/failed attempts too.

Choose `BENCHPROOF_MAX_AUDIT_USD` after measuring the selected model and runner. The UI should show a usage estimate only when it can explain the underlying price snapshot.

## Benchmark budget check

Before the planned 12 B0 visible-test runs + 36 B1 agent trials + 36 B2 runtime trials, estimate their worst-case consumption from development trials. If the estimate exceeds usable credit after reserves, reduce optional comparisons, reduce context, or use the explicitly named P0 suite. Keep all failure counts in the chosen denominator.

Do not save cost by omitting the independent verifier while still calling a repair verified. Do not buy additional compute automatically.

## Practical savings

Cache trusted dependency images and source manifests. Use one tested NVIDIA model before adding routing. Send focused source excerpts, not entire repositories. Keep fixtures CPU-sized. Stop refuted hypotheses promptly. Reuse recorded genuine evidence for explanatory browsing while keeping a functional live route.

## End-of-day record

Record actual grant balance, token usage, runner billing units, failures/retries, amount reserved for judging, and next-day ceiling. If the ledger is uncertain, pause large batches and resolve the account facts before continuing.

## Assurance-specific budget controls

Include independent gate, baseline/probe and trusted-mutant executions in the same twelve-execution audit cap. Mutations have at most three relevant templates per live verification; one recovery and any model-tier escalation consume the original call/time/cost caps. Richer context does not authorize unlimited input tokens. Cache source/graph artifacts only when their source/contract/builder hashes match.

The benchmark forecast also includes V12 fixed-candidate gates, G8 impact tasks, F6 freshness transitions, W8 trajectory traces and M12 mutant validation/execution. Estimate their separate model/runner needs: deterministic graph/trace checks need no paid model call merely to generate a metric. Compare B1/B2 usage with the same primary model and caps; report overhead as well as gains.

If reserves are inadequate, omit optional external-agent trials first, then select the explicit R6/V6 fallback before measurement. Do not run all eight paid tools just because they were researched. No subscription purchase or extra spending is authorized by these budget suggestions. Actual credit expiry and long-term host access must still be established.
