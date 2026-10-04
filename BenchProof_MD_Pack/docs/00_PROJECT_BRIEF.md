# BenchProof project brief

Owner: Ravi. Revised 3 October 2026 after the coding-agent research. Status: proposed product; no implementation results yet.

## Product in one sentence

BenchProof is an Agentic Engineering Assurance Runtime that checks a code change against explicit constraints, follows its impact through a versioned engineering graph, and produces independent, replayable acceptance evidence.

## User and problem

The initial user is a developer reviewing an agent-generated change to a small Python service. A patch can satisfy visible tests while breaking a caller, public response, precise amount calculation, or duplicate-request behavior. A long agent session can also rely on an outdated design decision or repeat the same failing attempt.

Research documents mature coding and automation features across eight tools. We should build a useful layer that accepts patches or trajectories from different agents, with a first-party NVIDIA repair loop for the hackathon. Our hypothesis is that explicit constraint-linked acceptance and evidence improve review decisions. This must be measured; the research alone does not establish a market gap or competitor failure.

## Hero demonstration

1. Select the synthetic invoice service and a declared task: preserve public response and exact amount semantics while fixing a boundary bug.
2. Show a proposed change that passes visible smoke tests. Explain which contract those tests did not exercise.
3. Build the graph from Python AST plus explicit links; show the affected route, money helper, service, worker, and protected checks. Label unresolved edges.
4. Run a trusted counterexample in isolation. The independent gate rejects the inadequate candidate and records the violated constraint.
5. Use a real NVIDIA model call on Nebius to propose a bounded repair using current source and impact context.
6. Verify in a fresh candidate environment against protected checks and regressions. If implemented, run trusted mutants to report test sensitivity separately.
7. Download a bundle with hashes, diff, check results, decision provenance, runtime limits, and a replay guide.

A rejected candidate is a useful outcome. A repeated failure should stop or take one documented recovery path; it should not turn into an endless hidden retry.

## What we build

| Layer | Outcome |
| --- | --- |
| Constraint registry | Human-owned versioned contracts mapped to protected checks |
| Engineering state | Files, symbols, contracts, tests, decisions, patches, and runs with typed edges |
| Impact/context | Affected callers/checks, stale dependencies, risk reasons, unresolved coverage |
| Agent loop | Useful diagnosis/repair from actual NVIDIA inference; bounded actions and failure fingerprints |
| Independent gate | Trusted expected behavior; fresh execution; candidate cannot decide acceptance |
| Evidence | Machine-readable result manifest plus readable report and independent replay |

## Feasible boundaries

One Python/FastAPI fixture family, six main modules, CPU-sized synthetic inputs, SQLite adjacency storage, AST parsing, and one tested model. P0 supports API compatibility and exact amount calculations. P1 adds caller-impact and idempotency repair coverage, decision invalidation, recovery, and trusted mutation reporting.

Public use is curated examples and candidate presets. Authorized developer mode can ingest a bounded source snapshot and unified diff. A generic provider-neutral record format is feasible; a full IDE, distributed control plane, arbitrary repository agent, whole-program proof, and integrations to all eight products are outside the deadline scope.

No real payment account, personal invoice data, financial recommendation, or production money movement is needed. The invoice domain supplies precise engineering constraints and readable boundary cases.

## Competitive hypothesis and completion

The research-derived contribution is the linkage between constraints, graph state, trajectory, verification, and evidence. A graph or memory alone is already a familiar capability. Judge-facing value is a clear review decision with inspectable support.

Completion means a working, accessible, measured release with genuine model use, executable examples, bounded claims, open source, a short video, and complete entry materials. The [strategy](02_WIN_STRATEGY.md) explains evidence priorities. A contest win cannot be guaranteed.
