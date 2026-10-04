# Interface and user experience

The research changes the main decision from “trust this ML score” to “accept, reject, or review this code change under declared constraints.” Keep the developer's decision clear; implementation detail belongs in expandable evidence.

## Main screens

| Screen | Primary action | Essential content |
| --- | --- | --- |
| Examples | Choose task/candidate and start | Supported Python scope, synthetic label, live/mock mode, accepted constraint summary |
| Run | Follow assurance or cancel | Progress/status, time/usage, affected components, concise observations |
| Impact | Inspect affected behavior | Changed files/symbols, callers, mapped contracts/checks, coverage gaps |
| Diff | Review proposed repair and verify | Minimal readable diff, base hash, targeted failures, protected-policy status |
| Result | Decide whether stated evidence suffices | Gate verdict, failed/passed/unknown checks, limitations, test-strength status |
| Evidence | Download or inspect replay | Version hashes, decision/action ledger, artifact list, replay instructions |

Use one connected journey with tabs/panels, not six unrelated dashboards. Public mode selects curated examples; no tempting arbitrary-repository upload appears in v1.

## Hero layout

The header shows task, source version, accepted contract and actual runtime mode. The first result explains: “The candidate passed visible smoke tests but failed C-AMOUNT on invoice-total rounding.” Show the small input and expected/actual behavior only when safe and available from the trusted result.

Below it, show the affected route and worker, source links, a readable diff and required-check table. Advanced details reveal edge provenance, graph gaps, context/decision hashes and runner/model configuration. The main action is “Verify proposed repair,” followed by “Download evidence.” No generic “make it safe” button.

## Status language

| State | Suggested message |
| --- | --- |
| VERIFIED | “All required checks passed for this version and declared scope.” |
| REJECTED | “This change violates a required constraint.” |
| INCONCLUSIVE | “Some required checks could not establish a result.” |
| BLOCKED | “A required prerequisite or coverage mapping is missing.” |
| STALLED | “The same failing attempt repeated without new evidence.” |
| WEAK mutation strength | “Selected checks missed one or more declared regression mutants.” |
| Clean/no patch | “No failed required constraint was found in the checks run.” |

Display lifecycle separately from gate verdict: a COMPLETED run may be rejected or inconclusive. Display test strength separately from required-contract acceptance, following the manifest's required/optional mutation policy. Never use “100% safe,” “all bugs fixed,” or “formally proven.”

## Graph, risk and freshness

Use a compact affected-path list first. A small graph is optional when it helps inspection. Distinguish observed, declared and inferred links in text/legend, not color alone. PARTIAL coverage and unresolved required relationships stay visible above the final action.

Risk is Low/Medium/High/Critical plus concrete triggered reasons. Avoid probability gauges or invented confidence percentages. CURRENT/STALE decisions show affected dependency and latest validation; do not expose hidden model reasoning.

## Evidence and metric presentation

Show counts with denominators and suite names. Live run checks are not benchmark repair rates. Mutation killed/valid counts need survived/invalid/skipped/unknown details. Cost is “unknown” when prices or usage are absent. Historical recorded evidence must be visibly labeled and cannot masquerade as a new live run.

## Errors and recovery

Reload restores the existing audit and SSE cursor. Provider/rate-limit failures explain retryability without repeated automatic starts. Cancel displays pending reconciliation until remote termination is known. Budget exhaustion keeps logs, diff and partial checks downloadable where safe. Stale patch prompts a current rerun; it cannot be applied by dismissing a warning.

## Accessibility and visual system

Use readable neutral surfaces, restrained status color, one main action per stage, sufficient contrast, visible focus, keyboard navigation and labels for every icon. Do not rely on red/green. Diff supports side-by-side on wide screens and unified view on narrow screens. Long artifact IDs are copyable but not the main prose. Basic journey works around 360 px width without horizontal page overflow.

## Usability protocol and acceptance

If volunteers are available, ask them to choose a faulty example, explain why it was rejected, verify a repair and find what remains unchecked. Ravi arranges contact; this pack sends no messages. Record consent, completion, confusion, time and changes without coaching answers. Aim for three sessions, disclose actual count and limited sample.

Release acceptance: users can identify the failed constraint and next action, distinguish graph limits from behavior checks, inspect the real diff, recover from reload, and download the evidence. All displayed statuses/numbers come from actual API records; no hardcoded passing demo state.
