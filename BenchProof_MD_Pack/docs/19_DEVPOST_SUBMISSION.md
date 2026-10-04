# Devpost entry draft

Draft updated for the research-driven assurance runtime. It is not ready-to-publish achievement copy: features, links, results and lessons must be finalized from the built release. Official required fields remain in [event requirements](01_HACKATHON_REQUIREMENTS.md).

## Title and short description

**BenchProof — Agentic Engineering Assurance Runtime**

Draft description: “Checks agent-generated code changes against executable constraints, follows their impact, and produces independent, replayable acceptance evidence.”

Use this description only if the release actually supports those behaviors. Otherwise narrow it to the implemented scope.

## Inspiration — adaptable draft

Coding agents can make useful changes, but reviewers still need to establish whether a patch respects the intent of a system. Our research found that memory, rules, repository context and background execution already exist across mature tools. We focused on a concrete review decision: connect an accepted constraint to affected code, independent checks and evidence on one version.

Our demonstration uses an original synthetic Python invoice service, where exact amount, public response and duplicate-request behavior make failures small and inspectable. It handles no real payments or private invoice data.

## What it does — select implemented capabilities

- Pins human-owned constraints and immutable source versions.
- Maps changed Python code to declared callers, contracts and protected checks, exposing unresolved coverage.
- Uses an NVIDIA model on Nebius for bounded investigation and a restricted repair.
- Accepts or rejects the candidate through a fresh isolated run and protected deterministic evaluator.
- Exports source/diff/check/version evidence and a replay guide.
- If completed: invalidates stale decisions, stops/replans a repeated failure, and reports trusted mutation sensitivity separately.

Delete every unimplemented bullet. Do not imply full language support, formal proof, production reliability or integrations to all eight researched agents.

## How we built it — fill actual implementation

Draft stack: Python/FastAPI worker, React/TypeScript/Vite, SQLite state/records, AST plus reviewed dependency manifest, Nebius Token Factory inference and tested isolated execution adapter. Replace with actual services, dependency versions, NVIDIA model ID and runner/image digest.

Explain that the model proposes actions/diffs while accepted contracts and expected behavior stay outside candidate control. Distinguish generated adversarial proposals from trusted final checks. If mutations are used, name their bounded pre-authored scope.

## Challenges — evidence slots

- Constraint or cross-module case that failed: [run/check/artifact].
- Graph uncertainty/stale decision handling: [actual observation and limitation].
- Provider capability or cancellation issue: [dated sanitized reproduction].
- Self-verification/gaming attempt rejected: [negative test].
- Schedule/budget cut and resulting scope: [decision record].

Write observed challenges, not generic stories. A provider feature documented online does not establish our integration experience.

## Accomplishments — fill from final records

| Claim | Required evidence | Current state |
| --- | --- | --- |
| Working protected repair loop | Live audit, diff and fresh check results | Not built |
| Correct repair/clean behavior | Selected R12/R6 actual numerators, denominators, failures and commit | Not measured |
| Gate detects inadequate candidates | V12/V6 results and paired smoke/gate artifacts | Not measured |
| Graph/freshness/trajectory/mutation contribution | Separate named suites; no combined denominator | Not measured |
| Replayable export | Preselected fresh replay logs and limitations | Not built |
| Developer usability | Actual session count and observations | Not observed |

Optional external-agent comparison is included only if the [fair protocol](26_COMPETITOR_BENCHMARK.md) is actually completed. Desk research supports positioning, not “we beat” claims.

## Lessons and next steps

After building, state one evidence-backed lesson about constraints, context, verification or cost. Future directions can include additional Python repositories, external-agent adapters and broader language indexing. Keep them labeled future work. The old ML-audit domain is a possible later vertical, not shipped coverage.

## Tool feedback and fields

Complete factual Nebius/NVIDIA feedback from [feedback log](21_PRODUCT_FEEDBACK.md). Fill project/track, runtime model/services, public repository/license, actual demo/test-build URL, public video, setup/testing instructions, results/limits and all live form requirements.

- Demo URL: [required, not available yet]
- Repository/release commit: [required, not available yet]
- Public video/duration: [required, not available yet]
- Evaluated suite/config/results: [not measured]
- Testing access and availability: [to verify]
- Team/eligibility declarations: [Ravi to verify]

## Before copying into the form

Replace placeholders or explicitly state unavailable nonrequired evidence. Verify every feature sentence against a built path and every numeric claim against records. Use short plain explanations and link inspectable artifacts. Check the live form and rules on 27 October; submit by the internal 28 October, 8:00 p.m. IST target and retain actual submitted-status confirmation.
