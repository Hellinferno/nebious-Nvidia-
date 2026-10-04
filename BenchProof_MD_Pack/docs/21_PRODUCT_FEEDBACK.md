# Platform and model feedback log

Status: template. No hands-on Nebius/NVIDIA application usage has been completed by creating this pack. Official documentation observations belong in the source register; they are not invented product experiences.

## Observation template

### Observation ID: FB-[number]

- Date/time and source commit:
- Service/tool/SDK:
- Exact model, endpoint, SDK version, and environment:
- Goal and why the product needed this capability:
- Steps performed:
- Expected behavior:
- Actual behavior:
- Sanitized evidence or minimal reproduction:
- Latency/token/operation measurements if relevant:
- What worked well, with a concrete example:
- Friction or limitation observed:
- Effect on the user/product:
- Workaround, if any:
- Suggested improvement and expected benefit:
- Severity: blocking / significant / minor:
- Reproducibility: consistent / intermittent / one occurrence:
- Would we use it again? Reason:
- Resolution or follow-up status:

## Topics to observe during the build

| Date window | Observation focus |
| --- | --- |
| 4–6 Oct | Account onboarding, exact model discovery, beta access, first command |
| 7–9 Oct | Structured JSON, tool-loop reliability, code patch quality, invalid output |
| 10–15 Oct | Artifact retrieval, checkpoint branching, cancellation, error diagnostics |
| 19–22 Oct | Hosted latency, quotas, bulk evaluation, usage accounting |
| 24–27 Oct | Reviewer experience, docs consistency, recovery and deploy friction |

These topics are prompts for observation, not claims that a problem occurred.

## Feedback quality

A useful entry is specific enough to reproduce, connects the limitation to a real product workflow, and suggests a feasible improvement. Keep requests constructive and distinguish provider behavior from our own implementation bugs.

For model quality, name the exact task and input/contract shape. Do not report general “bad reasoning” from one failure. For performance, specify cold/warm behavior, sample size, and whether time includes queueing or sandbox preparation.

## Submission summary to fill on 27 October

- Integration used and why:
- Most useful observed capability:
- Most significant observed friction:
- Evidence-backed improvement request:
- Model behavior that affected investigation/repair quality:
- Account/cost/access feedback if relevant:
- What we would keep or change in a future version:

No feedback message is sent automatically. Ravi can include the completed feedback in the entry or contact the organizer if he chooses.

## Research-aligned observations

Collect actual observations about constraint-linked action JSON, repair quality across impacted callers, current/stale context rejection, bounded recovery, fresh execution, oracle separation, mutation overhead and artifact retrieval. Record request/model/SDK versions and sanitized reproductions; distinguish unsupported capability from a product defect.

Measure whether tool schemas and bounded current context improve this runtime, and where budgets/latency fail. No competitor failure anecdote belongs in sponsor feedback without an actual configured run. The eight-tool desk review is not hands-on product testing. Complete feedback from observed Nebius/NVIDIA integration and publish only claims the records support.
