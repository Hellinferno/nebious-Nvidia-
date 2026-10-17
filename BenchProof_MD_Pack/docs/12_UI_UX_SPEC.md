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

Every action is also a named skill (`/start` … `/cancel`) in a palette opened with Ctrl+K or `/`. The palette lists the server-computed availability, cost class and plain-sentence blocked reason for each skill, the recommended next action names the skill it maps to, and the panel buttons call the same endpoints, so a developer can drive the whole journey by slash command without learning the layout. A proposed diff is shown as `PENDING` until the protected gate approves or rejects it; the gate result names its verification attempt.

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

### Implemented visual refresh — 16–17 October 2026

The hosted workspace uses a fixed light visual system: slate text, white panels on a neutral canvas, and restrained teal actions. Typography uses an explicit local sans-serif stack (Segoe UI on Windows), independent heading line heights, and monospace only for identifiers, hashes and diffs. No remote font service or new package is required. Browser color-scheme preference must not mix incompatible foreground/background palettes.

The brand/command bar, compact runtime status, section links and numbered stages separate navigation from decisions. Five case cards share a responsive grid; the active selection is distinguished by a border and fill, not only its button. Status dots accompany actual API text and remain pending until readiness is known. Lifecycle, gate verdict and optional test strength remain separate; this is a presentation change, not a new assurance claim.

`deployment/vercel/ui-check.mjs` checks rendered font faces, heading/subtitle separation, horizontal overflow at 1440/1280/1024/768/390/320 px, Ctrl+K/Escape, and stable colors under dark preference. The connected browser journey also checks active-audit layouts at 1440/768/390/320 px, in addition to gate/export/replay/download/reload. Screenshots and machine-readable records are stored under `artifacts/ui-refresh-20261016/`. Automated layout checks do not replace volunteer usability sessions.

If volunteers are available, ask them to choose a faulty example, explain why it was rejected, verify a repair and find what remains unchecked. Ravi arranges contact; this pack sends no messages. Record consent, completion, confusion, time and changes without coaching answers. Aim for three sessions, disclose actual count and limited sample.

Release acceptance: users can identify the failed constraint and next action, distinguish graph limits from behavior checks, inspect the real diff, recover from reload, and download the evidence. All displayed statuses/numbers come from actual API records; no hardcoded passing demo state.
