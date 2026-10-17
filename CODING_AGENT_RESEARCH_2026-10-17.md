# Coding-agent landscape and five recurring product problems

Research date: 17 October 2026, Asia/Kolkata. This is a source-backed desk review, not a hands-on benchmark or proof of an unserved market.

## Executive conclusion

Do not try to win by implementing every feature from every coding app. Strong incumbents already offer code generation, terminal execution, tests, repository context, memory, checkpoints, integrations and parallel agents. A defensible prototype needs one useful end-to-end coding workflow and measured improvements on a specific developer frustration.

Recommended product hypothesis: a resumable, bounded coding agent for small existing Python projects, powered by an NVIDIA model on Nebius Token Factory. It takes a task, writes real changes, runs tests in isolation, revises failures within explicit limits, and hands back a reviewable patch with the actual execution results. Existing BenchProof assurance components can support this workflow rather than dominate its interface.

This hypothesis is not validated demand, an implemented feature list, a claim of uniqueness, or a guarantee of winning.

## Method and limitations

- Reviewed 17 current product families/surfaces and one historical comparator. This is a broad selection, not every coding product or every feature.
- Product capabilities below are documented by their vendors. Documentation does not establish their reliability, unrestricted availability, quality or superiority. Plan, platform and rollout restrictions apply.
- Problem evidence combines the 2026 Stack Overflow Developer Survey with first-person reports and feature requests in product issue trackers/forums. These reports establish that particular people encountered a problem; they do not measure its global frequency or prove it remains unfixed in current releases.
- Problems are prioritized by likely user harm, recurrence across the sources and relevance to our build. They are not a statistically established global top five. Search selection, self-reporting and closed/duplicate reports introduce bias.
- Some reported behaviors involve third-party models, proxies or beta builds. Model behavior, product orchestration and environment failures must not be conflated.
- No competitor accounts were purchased, no candidate code or model inference was run, no competitor benchmark was performed, and the production app was not changed for this research.

## 1. Notable documented capabilities

| Product / surface | Standout capabilities worth studying | Primary source |
| --- | --- | --- |
| Cursor | Multi-file agent, repository/web search, terminal and browser tools, local checkpoints; cloud agents add isolated VMs, parallel work and demonstration artifacts. Tab predicts coordinated edits and next editing locations. | [Agent](https://cursor.com/docs/agent/overview), [cloud capabilities](https://cursor.com/docs/cloud-agent/capabilities), [Tab](https://cursor.com/help/ai-features/tab) |
| Claude Code | Cross-file implementation and command execution; persistent instructions/auto memory, skills, hooks, MCP, coordinated agents and local/cloud workflows. Checkpoint rewind can restore code and/or conversation, with documented coverage limits. | [Overview](https://code.claude.com/docs/en/overview), [checkpointing](https://code.claude.com/docs/en/checkpointing) |
| OpenAI Codex | Terminal/IDE coding and execution, dedicated review, resumable sessions, subagents and script/CI workflows. The desktop/browser experience adds browser-based inspection and verification; this should not be attributed to the CLI's built-in interface. | [CLI](https://learn.chatgpt.com/docs/codex/cli), [Browser](https://learn.chatgpt.com/docs/browser), [updates](https://learn.chatgpt.com/docs/whats-new) |
| GitHub Copilot | Repository-aware conversation, background cloud implementation with tests/linters, issue/PR entry points, code review, shared session context, memory, custom agents and repository-event/scheduled automation. | [Copilot on GitHub](https://docs.github.com/en/copilot/concepts/copilot-surfaces/copilot-on-github) |
| Cascade / former Windsurf surface | Code/chat modes, planning and task lists, real-time editor context, rules/memories, reusable workflows, named checkpoints, queued instructions, lint fixes and deployment tools. Current Windsurf documentation redirects to Devin Desktop; do not count this as an unrelated vendor. | [Cascade](https://docs.devin.ai/desktop/cascade/cascade) |
| Devin | Delegated engineering tasks in a workspace with shell, IDE and browser; human takeover, parallel tasks, repository integrations and CLI-to-cloud handoff. | [Introduction](https://docs.devin.ai/get-started/devin-intro) |
| Cline | Open-source agent across desktop, CLI and editor surfaces, browser/terminal work, provider choice/BYOK and human approval workflows; task-board execution uses per-card worktrees. Checkpoints support task recovery. | [Overview](https://docs.cline.bot/cline-overview), [checkpoints](https://docs.cline.bot/core-workflows/checkpoints) |
| Aider | Terminal pair programming, repository maps, cloud/local model choice, automatic Git commits and undo through Git, image/web context, voice input and automatic lint/test feedback. | [Features](https://aider.chat/) |
| OpenCode | Provider-configurable terminal agent, read-only planning versus build mode, project instructions, image context and conversational undo/redo workflows. | [Documentation](https://opencode.ai/docs/) |
| Continue | Customizable open-source IDE assistant with agent/chat/edit/autocomplete modes, terminal CLI, configurable models, rules and MCP tools, including local-model setup options. | [Documentation](https://docs.continue.dev/) |
| Augment | Codebase context tooling, coding agents, terminal workflows, automated PR review and trigger/schedule-based software development automation. | [Introduction](https://docs.augmentcode.com/introduction) |
| Kiro | Structured feature/bugfix specifications, requirements/design/task artifacts and dependency-aware task execution; shared project configuration across IDE, CLI and web surfaces. This already overlaps the idea of coding from explicit requirements. | [Specs](https://kiro.dev/docs/specs/), [overview](https://kiro.dev/docs/) |
| Google Antigravity | Agent-management workspace, parallel local agents, terminal interface, background subagents, artifacts and browser-in-the-loop workflows. | [Official product page](https://antigravity.google/) |
| Gemini CLI | Terminal development workflows, persistent context, shell execution, plans, session history, checkpoints/rewind, extensions, MCP, headless operation and sandboxing. Some features are marked experimental. | [Documentation](https://geminicli.com/docs/) |
| Replit Agent | Prompt-to-application workflow with project setup, infrastructure, code, testing and publishing; plan review, checkpoints and integrated application services. | [Agent overview](https://docs.replit.com/features/agent/overview) |
| Bolt | Browser-based development environment, prompt-driven builds, code/visual editing, repository import, preview/publish workflows, database/auth management and collaboration. | [Introduction](https://support.bolt.new/get-started/intro-bolt) |
| Lovable | Natural-language full-stack application generation with editable frontend/backend code, database/auth/integrations, project previews/version history and source-control handoff. | [Introduction](https://docs.lovable.dev/introduction/welcome) |

Historical comparator: [Roo Code's documentation](https://roocodeinc.github.io/Roo-Code/) describes model-agnostic development, specialized modes and filesystem/terminal workflows, but now explicitly marks the extension shut down. Do not recommend it as a currently maintained competitor without checking its status. The shutdown notice gives May 15 without a year in the reviewed text.

### Feature families, not a copy-everything backlog

1. Fast inline completion and predicted next edits.
2. Repository search, symbol understanding and focused context retrieval.
3. Plan/spec review before mutation; explicit tasks and acceptance criteria.
4. Genuine multi-file code changes and small, readable diffs.
5. Terminal execution, build/lint/test feedback and repair iteration.
6. Browser interaction, visual inspection, screenshots and demonstration artifacts.
7. Issue-to-branch/PR workflows, reviews and CI integration.
8. Persistent instructions, decisions, memory and resumable sessions.
9. Checkpoints, rollback, forks and conflict-aware change handling.
10. Parallel agents with worktree/environment isolation.
11. Extensibility through skills, hooks, MCP, APIs and automation.
12. Model/provider choice, local models and bring-your-own-key workflows.
13. Prompt-to-full-stack applications, visual editing and deployment.
14. Permissions, sandboxing, network/secret boundaries and observability.

These are existing categories. Merely renaming one is not innovation. The advantage must come from a specific audience, workflow quality, integration or demonstrated improvement.

## 2. Five recurring problems

### 1. Plausible completion without dependable correctness evidence

User problem: an agent says a task is complete, but an important requirement is missing, a test was not executed, a failure is misreported, or the evidence belongs to an older code version. Users must investigate whether the summary is trustworthy.

Evidence:

- The [2026 Stack Overflow trust question](https://survey.stackoverflow.co/2026/ai/data/ai-trust) has 14,304 responses. 48.0% selected conditional trust when they can readily verify the output; 6.6% selected trust extending to important work decisions. These are self-selected survey responses, not a coding-agent failure rate.
- [Codex issue 41626](https://github.com/openai/codex/issues/41626) reports a conversation recap converting a pending, approval-gated hardware test into verified completion. It concerns recap accuracy, not evidence that the review command itself fabricated results.
- [Claude Code issue 22507](https://github.com/anthropics/claude-code/issues/22507) reports incorrect classification/attribution of a test failure and contradictory later statements. Despite its title, the issue body says tests did run. Do not repeat the misleading shorthand that no tests ran.

Proposed response: requirement-to-evidence status, machine-captured test commands/exit codes and source identity, explicit NOT_RUN/FAILED/BLOCKED, and stale-result invalidation after code changes. Tests themselves still need trusted expectations; passing self-written tests is not universal correctness.

Demonstration: attempt to mark a task done before its required test runs; the application refuses completion. Change the candidate after a passing run; the old result becomes stale.

### 2. Loss of task intent and relevant context across long work

User problem: developers repeat instructions, agents forget constraints after summarization/resume, or stale architectural assumptions are reused after files change.

Evidence:

- [Claude Code issue 23776](https://github.com/anthropics/claude-code/issues/23776) describes compaction preserving technical detail but losing the user's review-before-implementation instruction.
- A [Cursor support response](https://forum.cursor.com/t/cursor-is-ignoring-even-the-most-simple-rules-in-iteration-development-approach/152025/6) discusses unreliable rule adherence in long sessions and suggests smaller rules and explicit reminders.
- [Codex issue 8310](https://github.com/openai/codex/issues/8310) reports task-intent loss when resuming after a limit, requesting a clear continuation checkpoint.

Proposed response: persist a compact user-approved task brief, constraints, current plan, decisions, attempted approaches and next step outside the model transcript. Tie reused code facts to source/dependency hashes; retrieve only relevant context. Summaries may assist navigation but must not override recorded user intent.

Demonstration: stop after an intermediate change, resume, and continue the same task without restarting or forgetting an approved restriction. A changed dependency invalidates a stored code fact.

### 3. Repeated actions without progress

User problem: agents reread the same files, regenerate rejected changes or repeat failing commands while the user pays attention and tokens without getting closer to a working patch.

Evidence:

- [Cline issue 11209](https://github.com/cline/cline/issues/11209) reports repeated file reads without implementation and includes a later recurrence report.
- [Claude Code issue 86291](https://github.com/anthropics/claude-code/issues/86291) describes repeated reads after compaction with no edits or new evidence. Its environment includes a third-party model/proxy, so it does not establish the behavior of every Claude configuration.
- [Cursor continuation-loop report](https://forum.cursor.com/t/cursor-automatically-injects-your-previous-response-was-interrupted-after-every-response/159243) includes a support acknowledgment of an erroneous continuation injector. This is a particular orchestration failure, not a universal explanation for loops.

Proposed response: fingerprint normalized actions, relevant source state and failure observations. Repetition without new evidence triggers a bounded strategy change or an explicit stall. A legitimate repeated test after a real code change is not automatically a loop. Preserve useful partial work and report the blocker.

Demonstration: deliberately produce the same rejected candidate twice; stop before another identical paid attempt. Separately show that a changing candidate can legitimately rerun the same test.

### 4. Unwanted edits and unreliable recovery

User problem: a focused request expands into unrelated refactors, manual work is overwritten, or rollback does not restore the exact intended change set.

Evidence:

- [Cline issue 13136](https://github.com/cline/cline/issues/13136) reports off-task actions continuing after stop instructions.
- [Codex issue 16784](https://github.com/openai/codex/issues/16784) requests task-level undo/redo that preserves pre-existing user changes; it is closed as a duplicate, not evidence of the current behavior of every Codex client.
- [Claude's checkpoint documentation](https://code.claude.com/docs/en/checkpointing) explicitly documents exclusions, including shell-command changes and some subagent edits. Checkpoints already exist; coverage and recovery semantics matter.

Proposed response: isolated per-task workspace, approved path scope, explicit approval for deletions/renames/expanded scope, immutable before/after snapshots, and conflict detection before applying or reverting a patch. Never implement undo as a blind repository reset.

Demonstration: create a user edit before the task, run an agent patch, then undo only the agent change while preserving the user's bytes. If the same file changes concurrently, show a conflict rather than overwriting it.

### 5. Unpredictable task cost, duration and stop behavior

User problem: a small task unexpectedly uses many calls, large repeated contexts or background work; usage displays do not explain which task consumed the allowance, or cancellation does not reliably halt new work.

Evidence:

- [Cline issue 14256](https://github.com/cline/cline/issues/14256) reports failed sessions continuing to consume calls. Its billing allegations and totals are the author's observations, not independently audited facts.
- A [Cursor user request](https://forum.cursor.com/t/cursor-always-turns-3-sentences-into-60k-tokens/149061/6) asks for intelligible per-task/workspace usage and cost reporting. This historical report does not prove that today's dashboard lacks those capabilities.
- [Cursor cloud-agent documentation](https://cursor.com/docs/cloud-agent) explains that model/context choices affect usage and describes spend limits. Controls already exist in competing products; a budget feature alone is not novel.

Proposed response: separate token/call/time/execution limits, visible per-task usage, admission reservations and a final usage record. Distinguish measured token usage from estimated monetary cost; show cost as unknown when prices or usage are unavailable. Stop scheduling new paid calls after cancel/failure/budget exhaustion and reconcile any in-flight operation.

Demonstration: exhaust a tiny call budget and confirm no new inference begins. Cancel during work and prove both stopped scheduling and actual execution termination/reconciliation, rather than only changing a UI label.

### How strongly should we prioritize these?

The [2026 survey's switching question](https://survey.stackoverflow.co/2026/ai) reports 25.1% choosing better output quality as their reason for switching AI tools, versus 6.4% choosing lower cost and 1.4% choosing a particular feature. These are shares of respondents to that question, not percentages of switchers, and they do not isolate coding apps. The inference for our product is to prioritize useful, correct delivery over a giant feature list or a cheap-token-only pitch. Do not combine differently worded 2025/2026 trust questions as a trend.

## 3. Recommended build focus

### Specific initial audience

Developers maintaining small Python repositories who have a concrete failing test or bounded implementation task and want an agent-produced patch they can understand, test and safely reject. This is a proposed audience requiring interviews/usability sessions, not a validated customer segment.

### Minimum useful coding workflow

1. Import a size-limited supported project or open a sample. Clearly distinguish user projects from synthetic examples.
2. State the task, required behavior, files allowed to change and hard limits.
3. Agent inspects relevant source and proposes a short editable plan.
4. NVIDIA inference through Token Factory generates genuine code changes, never an undisclosed reference repair.
5. Execute approved test/build commands in a resource-limited sandbox, not on the trusted API host.
6. Feed real failures back into a bounded repair loop; stop on unsafe scope, repeated failure, missing dependencies or limits.
7. Review the patch and real execution output; download/apply it only after conflict checks. Support task-level recovery and preserved checkpoints.

Do not expose arbitrary public-repository execution until input/path/archive handling, dependencies, egress, secrets, ownership and resource boundaries are designed and tested. Token Factory provides inference; code execution still needs the separate execution environment in our architecture.

### Build first, next, later

| Priority | Work | Reason |
| --- | --- | --- |
| First | One real task-to-model-patch-to-test-to-revision-to-review journey | It establishes that this is a coding agent rather than a review dashboard or canned demo. |
| Next | Persistent task brief/resume, loop circuit breaker, scoped edits/checkpoints, usage limits and evidence-linked completion | These target the five problems within the same coherent workflow. |
| Later | Browser UI automation, optional model routing, GitHub issue-to-PR convenience and reusable skills | Useful after the core loop is reliable; each adds scope and integration risk. |
| Defer | General IDE clone, many languages/frameworks, multi-agent swarms, arbitrary deployments and full-stack builder parity | These are expensive existing categories, not automatic differentiation. |

### What existing BenchProof work can support

Reuse candidate isolation, protected check infrastructure, patch validation, source identities, SQLite state, bounded actions, SSE events and evidence export where their contracts fit. The offline trial harness includes model-generated repair logic, but that does not mean the public app already offers a generalized coding-agent workflow. The current public reference-diff path must not be labeled live agent generation. Existing intermittent diagnosis HTTP 422 and model-output truncation also remain reliability work.

### Evidence for a credible competition demonstration

- Show real generation and execution on supported projects, not just changed UI statuses or stored answers.
- Include repair, a small feature task, a clean/no-change case, a hard failure and stop/resume. Keep failed attempts in the denominator.
- Compare a simple agent loop and our improved loop using the same model, inputs, attempt/token/time budgets and initial source. Use unseen tasks for measurement and separate demonstration examples from held-out tasks.
- Measure correct task completion, regression checks, unnecessary changed files, human interventions, paid calls/tokens, elapsed time and recovery correctness. Do not invent savings or compare different-quality models as if orchestration alone caused an improvement.
- Observe real developers attempting the workflow. Issue reports are problem signals; user sessions establish whether our solution is usable and useful.
- Keep acceptance and release claims scoped to the tested version and checks. No test suite proves universal correctness.

The [official competition page](https://nebiusglobalaihackathon.devpost.com/) evaluates technological implementation, design, potential impact and quality of the idea. A focused, demonstrated coding workflow with substantive NVIDIA/Nebius use addresses those criteria more directly than a feature-count contest. This is a strategic assessment, not a prediction of judges' decisions.

## Bottom line

Build an actual coding agent first. Make reliability controls visible as user benefits inside that workflow: it remembers the task, does not repeat futile work, respects edit boundaries, shows what really ran, can recover safely and stops within limits. Treat superiority as a hypothesis to test, not a slogan.
