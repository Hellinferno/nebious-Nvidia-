# Make the agent work your way

The [DeepSeek Harness README](https://github.com/deepseek-ai/deepseek-harness/blob/master/README.md) describes an everything-is-a-plugin architecture and links to the Web guide and architecture documentation. Following those links, the [base bundle documentation](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/bundle/base/README.md) describes named profiles, configurable defaults, permission policies and optional components. BenchProof adapts those ideas into bounded user controls. It does not install Harness, replace NVIDIA/Nebius, or introduce executable third-party plugins.

## Available locally

### Named agent profiles

Open **Customize agent** in the task composer. Save a name and your chosen workflow, custom instructions, instruction modules, mode and task budget together. Select a saved profile for another project without overwriting that project's task description.

- Save/update, duplicate, save as new, and delete profiles; up to ten are stored per browser owner capability.
- **Make default** explicitly selects a saved profile when reopening the new-task workspace. Unsaved edits do not silently become defaults. **Remove default** clears that choice.
- Export a portable profile JSON file or import a validated versioned profile. Imports reject unknown fields, module IDs, executable configuration, invalid limits and unsupported versions. Importing does not run an agent or install code.
- Profile JSON contains configuration only, not project source, task descriptions, owner capabilities or credential configuration. Free-text instructions may still contain sensitive material you entered: inspect exports before sharing and never include secrets.
- Profiles are browser-local templates, not an account-synced plugin marketplace. Changing or deleting one never rewrites an existing task.

### Switchable instruction modules

Combine any of these with your own instructions:

| Module | Guidance |
| --- | --- |
| Preserve compatibility | Keep public interfaces and existing behavior stable. |
| Prefer the standard library | Favor existing dependencies and small changes. |
| Match typing conventions | Preserve useful type information and nearby conventions. |
| Handle errors clearly | Make expected failures explicit; do not suppress useful errors. |
| Keep changes focused | Avoid unrelated cleanup, renaming and broad rewrites. |

These modules are fixed prompt sections, not executable tools or dynamically installed plugins. Their text is composed with your custom instructions and included in both planning and editing. The combined instruction limit is 2,000 characters; oversized combinations are rejected rather than silently truncated. Review the composed instructions in the created task.

### Plan-only and implementation modes

- **Plan and implement** retains explicit approval before code edits and checks.
- **Plan only** can generate, edit and save a reviewed plan, but the backend refuses edits and test executions, including direct API/store/engine paths. Paused planning can resume; it cannot resume into execution. Planning can still consume inference credits.

The upstream [plan-mode documentation](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/plan/plan-mode/README.md) informs the review interaction; BenchProof's plan-only restriction is enforced independently, not merely requested in a prompt.

### Lower-only task budgets

| Limit | User range | Default |
| --- | --- | --- |
| Model calls | 1–4 | 4 |
| Edit attempts | 1–2 | 2 |
| Test executions | 1–4 | 4 |
| Active seconds | 30–300 | 300 |

**Lean budget** selects two model calls, one edit attempt, three executions and 120 active seconds. **Default budget** restores the original upper bounds. Implementation normally needs at least two calls and three executions for its first edit and fresh final checks; smaller settings may intentionally stop before completion. Plan-only does not use edit/test allowances.

Limits are persisted in the immutable brief, bound to plan approval, and enforced by durable action reservations and active-time guards. They survive reload/restart and do not override global daily quotas. They are not hard currency/total-token guarantees or a promise that an already accepted provider call can be unbilled.

### Task workflow

1. Choose a sample or an uploaded Python project. Saved projects load their own source; creating a task uses the selected project's exact revision.
2. Pick **Fix a bug**, **Add a feature**, **Refactor**, or **Custom task**. Changing the recipe does not overwrite your task description.
3. Describe the desired outcome and select up to three editable `app/` files. Imported `tests/` remain read-only.
4. Optionally expand **Coding instructions** to specify conventions, compatibility constraints, or preferred implementation style. Instructions are limited to 2,000 characters; never include secrets.
5. Choose **Save for future tasks** only if you want those instructions remembered in this browser. **Forget saved instructions** removes that browser preference; it does not change existing tasks or their server-side records.
6. Create a draft, generate a plan, review/edit its steps, approve it, and explicitly choose **Start task**. Draft creation itself makes no inference call; plan generation does.

The selected recipe and instructions are structured task preferences. Both planning and edit requests receive them, including bounded revision attempts. They are stored in the immutable task brief and exported with task evidence. The approved plan binds that exact brief: changing preferences cannot reuse an older approval.

Recipes and instruction modules guide the prompt; plan-only and lower-only budgets are separate backend controls. No profile can change the configured provider/model, execution isolation, editable paths, output allowance or test profile, or raise server limits. Existing tasks and preferences without the new controls retain their original hashes and idempotency behavior. Explicit default-valued controls normalize to those same identities.

Feature and refactor recipes may proceed when baseline checks already pass; a nonempty edit and fresh final checks are still required. Bug-fix, custom, and legacy tasks retain the existing stop-on-passing-baseline repair behavior. Passing existing tests does not prove that a new feature satisfies untested requirements.

## More understandable results

- The workspace shows the task's pinned instructions rather than silently substituting current browser preferences.
- Plan review uses the actual backend plan schema and keeps approval separate from starting execution.
- Recorded check results, skipped/unknown checks, stdout and stderr are shown separately. An entirely skipped suite is not displayed as a passing result, even if the backend report incorrectly labels it verified.
- Event and checkpoint times use the API's Unix-second timestamps.
- Task stop reasons explain what happened and what can be reviewed next, instead of leaving only a blocked/failed badge.
- An older deployment without coding-task capabilities is described as unavailable rather than silently offering broken task creation.

## Inspiration translated into product decisions

| Harness idea | BenchProof adaptation |
| --- | --- |
| Named profiles and composition | Save, select, duplicate and import/export a named reusable setup. |
| Optional components and assembled context | Switch fixed instruction modules on/off and combine them with bounded user text. |
| Permission policy and settings | Select enforced plan-only operation or explicit implementation, and lower task budgets. |
| Durable session state | Preferences live in the existing durable task brief and approval identity. |
| Separate tool/execution capabilities | Recipes never change the trusted runner or permission boundary. |
| Event-driven UI | Actual persisted plans, check reports and task activity drive visible state. |

This is architectural inspiration, not copied upstream implementation or an integration claim. DeepSeek's [safety guidance](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md) also makes clear that its experimental runtime is not a substitute for an execution security boundary.

## Instruction-only skills

The **Skills manager** creates, edits, imports and exports a restricted instruction-only `SKILL.md` format: required scalar `name` and `description` frontmatter followed by Markdown instructions. Optional scalar `license` and `compatibility` metadata is accepted but not executed or retained. Nested YAML, executable permissions, scripts, linked references, assets and archives are not supported. This is not complete Agent Skills runtime compatibility.

Save up to ten uniquely named skills in this browser and select up to three for a new task. Each skill has at most 2,000 instruction characters. Skill text is kept as an immutable snapshot, not silently updated when its library entry changes. Deselect/reselect to use edited text. New portable profiles use version 2 when they contain skills or a nondefault harness; existing version-1 profiles remain compatible. The shared model-context byte limit still applies before inference; combining many large inputs can be rejected.

## Reviewed harness strategies

- `bounded-v1`: the existing bounded loop with up to two candidate attempts.
- `single-pass-v1`: one candidate; a failed candidate stops without an automatic revision. Both the task allowance and engine enforce this restriction.

These are real orchestration policies, bound to the task's brief and plan approval. Neither grants permissions, resets quotas or loads arbitrary Python/JavaScript plugins. Replacing the underlying runtime or adding another strategy requires reviewed server code and tests, not a profile import.

## Read-only MCP reference bridge

The **MCP reference context** panel explicitly loads the operator-approved catalog. Pick a connection and tool, enter JSON arguments and consent to sending those exact arguments. No project source is attached automatically. Review up to two returned text snapshots before task creation. Snapshots are hashed, included in planning/editing and task exports, and excluded from portable profiles. Treat all reference text as untrusted input, not acceptance evidence; never include secrets.

This is a limited stateless HTTPS context bridge, **not** a general MCP agent client. It supports protocol `2026-07-28` JSON responses, `tools/list` and allowlisted `tools/call`. It does not support older initialization/session flows, SSE, stdio servers, OAuth setup, arbitrary user URLs, sampling or automatic model-selected tool calls. Only operator-approved tools also advertising `readOnlyHint: true` are callable. Tool annotations are claims, not proof: operators must trust the endpoint's actual behavior.

Operator configuration (server-side only):

```text
BENCHPROOF_MCP_CONNECTIONS=[{"id":"docs","name":"Docs","url":"https://your-approved-server.example/mcp","tools":["search"],"token_env":"BENCHPROOF_MCP_TOKEN_DOCS"}]
BENCHPROOF_MCP_QUERIES_PER_DAY=5
BENCHPROOF_MCP_TOKEN_DOCS=<optional dedicated server credential>
```

Use a real trusted endpoint; the example hostname is a placeholder. The default catalog is empty and calls are disabled. Configure the trusted backend environment, not browser/Vite variables. A separate MCP credential cannot select the Nebius key. Endpoints must use HTTPS/443 with no embedded credentials or query string; every resolved address must be public, and connections pin the checked address while verifying TLS against the original hostname. No redirects or automatic retries are followed. Socket waits, response size (32 KiB), argument size (2 KiB) and returned context (2,000 characters) are bounded. System DNS resolution has no separate application deadline.

One query reserves a shared daily allowance before up to two RPC requests; failures still count. Supported argument schemas are a deliberately restricted subset (primitive types, objects, arrays, enum and basic bounds); unsupported validation keywords fail closed. No schema URLs are fetched. Arbitrary external server compatibility and production credential setup are not implied by passing mocked tests.

## Runner and release scope

Imported projects now dispatch by their approved check profile, not filenames. Their launcher uses the shared Docker controls and cancellation identifier. Skipped, missing, duplicated or malformed check results cannot produce a passing project verdict. Ordinary project tests remain user-supplied checks, not the independent protected invoice gate. The scripted evaluation CLI requires explicit acknowledgement and Docker; it never substitutes a host subprocess for isolation or labels synthetic usage as measured model performance.

See [VERIFICATION.md](VERIFICATION.md) for current test results, live-call evidence and remaining release limitations. An open plugin marketplace, arbitrary shell access, complete MCP interoperability, a held-out model benchmark and a competition win are not claimed. Public deployment is a separate operation from local verification and Git push.

Further competitive work should build on a reliable vertical slice: richer source/context selection, reviewed regression-test proposals, a concise resumable activity stream, and a genuinely measured end-to-end demo. Do not add those by weakening the runner or presenting scripted evaluation as model performance.
