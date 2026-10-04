# Coding-agent research and BenchProof positioning

Revised 3 October 2026. The latest recovered research direction was **Agentic Engineering Assurance Runtime**, following an earlier “Agentic Engineering Control Plane” proposal. This document records verified public capabilities and our resulting design hypotheses. No hands-on competitor benchmark was recovered or performed in this revision.

## Research method and evidence levels

Prior discussion compared eight products and suggested context drift, repeated failure, global impact and shallow verification as useful problem areas. Those are plausible engineering failure modes, not measured failure rates for particular products. Public primary documentation was checked before incorporating claims.

Use three evidence levels: DOCUMENTED (a cited official page describes a feature); HYPOTHESIS (a proposed weakness or opportunity needing a test); MEASURED (an actual versioned run with configuration and artifacts). This pack currently contains documented features and hypotheses, with no measured product ranking. Absence from a reviewed page does not prove a capability is absent from a product.

## Eight-tool landscape

| Tool | Documented capabilities relevant to our plan | Consequence for BenchProof |
| --- | --- | --- |
| Cursor | Agent can inspect/edit code, run commands, use browser testing and coordinate work; project rules provide scoped instructions. [Agent overview](https://cursor.com/docs/agent/overview), [rules](https://cursor.com/docs/rules) | Do not claim code execution, coordination or rules are new. Test whether an explicit protected contract/evidence layer helps a concrete task. |
| OpenAI Codex | Cloud work uses a task workspace and supports inspecting changes/checks and PR workflows; AGENTS.md supplies repository instructions. [Cloud docs](https://learn.chatgpt.com/docs/cloud), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | Remote execution and durable instructions are existing capabilities. Accept Codex-style diff/trace records through a neutral schema without requiring integration for P0. |
| Claude Code | Available in terminal, IDE, desktop and web contexts; supports memory/instructions and subagents. Its memory docs distinguish instructions from client-enforced settings. [Overview](https://code.claude.com/docs/en/overview), [memory](https://code.claude.com/docs/en/memory), [subagents](https://code.claude.com/docs/en/sub-agents) | Retire a terminal-only characterization. Compare executable engineering constraints with behavior-shaping instructions, while acknowledging existing enforcement controls. |
| Windsurf/Cascade | The requested Windsurf memories URL currently redirects to Devin Desktop/Cascade docs; memories, rules and AGENTS.md remain described. [Current page](https://docs.devin.ai/desktop/cascade/memories) | Memory/rules are established. Record the naming/redirect overlap and avoid treating overlapping product documentation as independent evidence of eight unique implementations. |
| Cline | Official overview describes open-source desktop, CLI and IDE options, model choice, approvals and parallel/headless work. [Overview](https://docs.cline.bot/cline-overview) | Do not reduce it to one extension or claim model neutrality/parallel sessions are unique. A generic patch import is sufficient initially. |
| Aider | Repository maps use code symbols and dependency graph ranking within a token budget. [Repo map](https://aider.chat/docs/repomap.html) | A graph alone is not our novelty. Add versioned constraint, check, decision and evidence relationships and evaluate their effect. |
| Devin | Documentation describes writing, running and testing code using a development environment with shell, editor and browser tools. [Introduction](https://docs.devin.ai/get-started/devin-intro) | Do not claim autonomous execution/testing is absent. Focus on independent acceptance evidence for an explicit scope. |
| GitHub Copilot | Cloud agent handles background repository work in an ephemeral GitHub Actions environment and produces PR changes; custom agents are documented. [Cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent) | Background coding, tests and PR automation are established. Do not make them the headline differentiator. |

OpenAI's [Agents API overview](https://developers.openai.com/api/docs/guides/agents-api/overview) also documents managed Codex harness/session capabilities. Generic persistence, recovery or orchestration should not be asserted as unique to BenchProof.

The old Codex developer URLs redirected to learn.chatgpt.com documentation during verification. Store the reviewed canonical destination and retrieval date; recheck before public comparison. Product documentation and names can change.

## Research conclusions translated into build decisions

| Research theme | Build decision | How we test it |
| --- | --- | --- |
| Instructions can be forgotten or interpreted differently | Pin accepted executable constraints with protected oracles | Wrong response/amount must fail even if the patch declares success |
| Context can become stale | Source-hash-bound packets and versioned decision dependencies | Separate freshness suite: changed relevant dependency invalidates reuse |
| Local changes can affect distant callers | Typed AST/manifest graph and conservative reverse impact traversal | Separate graph suite with declared expected affected nodes/checks |
| Agents can repeat ineffective attempts | Failure fingerprints, bounded stop and one P1 recovery | Stalled and legitimate-progress traces scored separately |
| Self-generated tests can be weak | Independent protected acceptance plus trusted mutations | Fixed candidate gate corpus and separate mutant sensitivity counts |
| Reviewers need traceable decisions | Decision ledger and hash-linked evidence bundle | Fresh replay, provenance validation and tamper checks |
| Cost grows during retries | Bounded calls/context/executions and cost reservations | Actual per-trial usage with dated prices; no assumed savings |
| Users may switch coding tools | Provider-neutral patch/trace schema | Import one synthetic external-style record; adapters optional |

## Differentiation hypothesis

Our proposed contribution is a connected runtime that keeps constraints, engineering state, decisions, trajectories and independent evidence aligned on one source version. The strongest demonstration is an inadequate candidate accepted by visible smoke tests but rejected by a protected contract, followed by a useful constrained repair and replay.

This is not proof that no tool offers comparable workflows. Do not publish a “first,” “only,” “best,” or guaranteed-win claim based on this desk review. Evaluate the behavior and the contribution of the layer under [internal evaluation](13_EVALUATION_PLAN.md). Use the [optional external-agent protocol](26_COMPETITOR_BENCHMARK.md) before naming a product winner or weakness.

## Accepted scope and rejected expansion

Keep one Python fixture family, an AST/SQLite graph, one NVIDIA model and curated public inputs. Implement constraint-linked checks, source freshness and bounded stopping in P0. Add decision invalidation, recovery and mutation evidence as P1 only after the complete loop works.

The research's broader vision—persistent organization-wide architecture memory, multi-provider cost optimization and a universal code knowledge graph—is a future direction. A full control plane, integrations to all eight agents, semantic completeness across languages and calibrated risk prediction do not fit the current deadline.

## Open research questions

- Does graph-backed context improve the same model's repair rate under matched budgets?
- How often does the independent gate reject invalid candidates that visible smoke tests accept?
- Can the trajectory rule distinguish a true stall from an improving attempt?
- Do source-linked decisions prevent outdated assumptions from being reused?
- Do the selected trusted mutants reveal a weak check set without excessive latency?
- Can a reviewer understand a constraint failure and scope limit quickly?

Answer with separate suite records and actual counts. No measured answer exists yet. Preserve that status in the submission copy until the build produces evidence.
