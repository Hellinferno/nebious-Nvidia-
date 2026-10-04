# BenchProof — Agentic Engineering Assurance Runtime

Research-aligned execution pack for Ravi. Revised 3 October 2026. All planning dates use Asia/Kolkata (IST).

**Track:** Coding and Agentic Engineering, Nebius x NVIDIA Global AI Hackathon.

**Product:** BenchProof checks proposed code changes against executable engineering constraints, traces affected dependencies, detects stale context and repeated failure, and exports evidence from an independent verifier.

**Status:** Documentation and implementation specifications only. No application, competitor trial, benchmark result, deployment, video, or entry submission has been completed by revising this pack. Acceptance targets below become achievements only when actual run evidence is attached.

## Start here

1. Read the [research and positioning](docs/24_RESEARCH_AND_POSITIONING.md) and [project brief](docs/00_PROJECT_BRIEF.md).
2. Read the [event requirements](docs/01_HACKATHON_REQUIREMENTS.md) and today's [daily tasks](planning/DAILY_TASKS.md).
3. Build from the [product requirements](docs/03_PRODUCT_REQUIREMENTS.md), [architecture](docs/04_ARCHITECTURE.md), [runtime specification](docs/25_ASSURANCE_RUNTIME.md), and [backlog](planning/BACKLOG.md).
4. Record evidence in the [progress log](planning/PROGRESS_LOG.md). Use the [evaluation protocol](docs/13_EVALUATION_PLAN.md) before collecting results.
5. Finish with the [release checklist](planning/RELEASE_CHECKLIST.md), [judge guide](docs/20_JUDGE_QUICKSTART.md), and [submission draft](docs/19_DEVPOST_SUBMISSION.md).

Internal submission: **28 October 2026, 8:00 p.m. IST**. Feature freeze: **25 October**. Official dates remain centralized in the event requirements.

## Research-driven direction

The research compared Cursor, Codex, Claude Code, Windsurf/Cascade, Cline, Aider, Devin, and GitHub Copilot. Official documentation already describes substantial code execution, memory/rules, repository context, cloud work, and agent coordination across this landscape. Those features alone are weak differentiation.

Our contribution to test is a connected assurance workflow: **human-owned constraint → versioned engineering state → affected checks → bounded repair → independent acceptance → replayable evidence**. This is a product hypothesis, not a claim that competitors lack every component.

The hero example is a synthetic Python invoice-ingestion service. A change can pass its visible smoke tests while breaking an API, exact amount calculation, caller behavior, or duplicate-request contract. BenchProof should expose the missed constraint, show the affected code, reject an inadequate patch, then verify a useful repair. “Proof bundle” means evidence for stated checks on a stated version; it does not mean a formal proof of universal correctness.

The earlier ML experiment-audit concept is superseded as the active build scope. Its lessons about independent verification and replay remain. Migration decisions and all document changes are in the [research change map](docs/27_RESEARCH_CHANGE_MAP.md).

## Scope and order

| Priority | Build commitment |
| --- | --- |
| P0 | Python fixture, pinned executable constraints, typed dependency graph with coverage limits, source freshness, bounded NVIDIA repair on Nebius, protected independent gate, clean/rejected paths, usable UI and export |
| P1 | Versioned decision invalidation, explicit loop recovery, trusted mutation probes, four repair families, full separated benchmark suites |
| P2 | Additional agent/provider adapters, two model tiers, broad language support, deeper graph views |

Ravi is the assumed sole builder. The schedule assumes 3–4 focused hours on weekdays and 5–6 on weekends; availability has not been confirmed. Complete the whole P0 path before expanding it. A working, understandable submission supports a strong competitive case; a prize remains a judging outcome.

## Documentation map

| File | Use |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Coding-work instructions and trust boundaries |
| [CHANGELOG.md](CHANGELOG.md) | Revision and eventual release history |
| [00_PROJECT_BRIEF.md](docs/00_PROJECT_BRIEF.md) | Audience, problem, hero path, scope |
| [01_HACKATHON_REQUIREMENTS.md](docs/01_HACKATHON_REQUIREMENTS.md) | Official requirements and dates |
| [02_WIN_STRATEGY.md](docs/02_WIN_STRATEGY.md) | Evidence for judging criteria |
| [03_PRODUCT_REQUIREMENTS.md](docs/03_PRODUCT_REQUIREMENTS.md) | Stories, priorities, acceptance |
| [04_ARCHITECTURE.md](docs/04_ARCHITECTURE.md) | Components, data flow, state machine |
| [05_REPOSITORY_STRUCTURE.md](docs/05_REPOSITORY_STRUCTURE.md) | Planned code layout and commands |
| [06_SETUP_WINDOWS.md](docs/06_SETUP_WINDOWS.md) | Environment, installation, preflight |
| [07_NEBIUS_NVIDIA_INTEGRATION.md](docs/07_NEBIUS_NVIDIA_INTEGRATION.md) | Real provider and execution integration |
| [08_AGENT_WORKFLOW_AND_PROMPTS.md](docs/08_AGENT_WORKFLOW_AND_PROMPTS.md) | Roles, tools, prompt contracts |
| [09_SANDBOX_AND_SECURITY.md](docs/09_SANDBOX_AND_SECURITY.md) | Intake, isolation, evaluator protection |
| [10_DATA_AND_FIXTURES.md](docs/10_DATA_AND_FIXTURES.md) | Synthetic repositories and separate suites |
| [11_API_AND_DATA_CONTRACTS.md](docs/11_API_AND_DATA_CONTRACTS.md) | Endpoints, typed records, evidence format |
| [12_UI_UX_SPEC.md](docs/12_UI_UX_SPEC.md) | Judge journey, decisions, statuses |
| [13_EVALUATION_PLAN.md](docs/13_EVALUATION_PLAN.md) | Fair baselines and metric definitions |
| [14_TEST_PLAN.md](docs/14_TEST_PLAN.md) | Integrity, behavior, isolation, recovery checks |
| [15_DEPLOYMENT_RUNBOOK.md](docs/15_DEPLOYMENT_RUNBOOK.md) | Deployment, backup, recovery, access |
| [16_COST_AND_CREDITS.md](docs/16_COST_AND_CREDITS.md) | Budget, usage, reserves, benchmark cost |
| [17_RISKS_AND_FALLBACKS.md](docs/17_RISKS_AND_FALLBACKS.md) | Cut lines, blockers, recovery scope |
| [18_DEMO_SCRIPT.md](docs/18_DEMO_SCRIPT.md) | A 2:50 genuine product demonstration |
| [19_DEVPOST_SUBMISSION.md](docs/19_DEVPOST_SUBMISSION.md) | Draft entry with evidence slots |
| [20_JUDGE_QUICKSTART.md](docs/20_JUDGE_QUICKSTART.md) | Testing and replay instructions |
| [21_PRODUCT_FEEDBACK.md](docs/21_PRODUCT_FEEDBACK.md) | Observed platform feedback |
| [22_LICENSE_AND_ATTRIBUTION.md](docs/22_LICENSE_AND_ATTRIBUTION.md) | Licenses, rights, provenance |
| [23_SOURCE_REGISTER.md](docs/23_SOURCE_REGISTER.md) | Sources and unresolved facts |
| [24_RESEARCH_AND_POSITIONING.md](docs/24_RESEARCH_AND_POSITIONING.md) | Eight-tool comparison and hypotheses |
| [25_ASSURANCE_RUNTIME.md](docs/25_ASSURANCE_RUNTIME.md) | Constraints, graph, freshness, risk, loops, mutations |
| [26_COMPETITOR_BENCHMARK.md](docs/26_COMPETITOR_BENCHMARK.md) | Optional fair external-agent evaluation |
| [27_RESEARCH_CHANGE_MAP.md](docs/27_RESEARCH_CHANGE_MAP.md) | Changes across the previous 32 documents |
| [DAILY_TASKS.md](planning/DAILY_TASKS.md) | 28 dated work sessions with evidence gates |
| [BACKLOG.md](planning/BACKLOG.md) | Dependency-ordered implementation tickets |
| [PROGRESS_LOG.md](planning/PROGRESS_LOG.md) | Actual status and daily evidence |
| [DECISIONS.md](planning/DECISIONS.md) | Accepted, superseded, and open choices |
| [RELEASE_CHECKLIST.md](planning/RELEASE_CHECKLIST.md) | Product, integrity, access, submission gates |

## Working rules

Commands, modules, and schemas are implementation targets until the corresponding code exists. Mocks remain labeled and never count as live integration evidence. A model recommendation cannot change a protected constraint or grant execution privileges. Every claimed result identifies source, contract, evaluator, model, and environment versions.

Finish each day with the acceptance check, its artifact, remaining blocker, and next dependency. Keep failures in the record. No account creation, payment, external message, publication, or contest submission has been performed by this documentation update.
