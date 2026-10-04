# Nebius and NVIDIA integration plan

Official API references are linked in [source register](23_SOURCE_REGISTER.md). Model availability, capability support, pricing, and account access remain live preflight checks.

## Verified API facts

[Token Factory quickstart](https://docs.tokenfactory.nebius.com/quickstart) documents the OpenAI-compatible base URL `https://api.tokenfactory.nebius.com/v1/`. The [model-list guide](https://docs.tokenfactory.nebius.com/api-reference/examples/list-of-models) documents authenticated catalog discovery. Its example IDs are not proof that a particular NVIDIA model is available to Ravi.

[Structured-output documentation](https://docs.tokenfactory.nebius.com/ai-models-inference/json) says JSON capabilities vary by model. [Function-calling documentation](https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling) makes backend tool execution the application's responsibility. Validate both capabilities on the selected model.

[Sandboxes](https://docs.tokenfactory.nebius.com/sandboxes/overview) are beta and require an access request. Their checkpoint branching, OCI-image support, and asynchronous operations are documented capabilities, not confirmed access for this project.

## Day 1 integration gate

| Check | Required saved evidence |
| --- | --- |
| Account ready | Ravi confirms access and applicable credit/billing conditions |
| NVIDIA model selected | Exact returned ID, provider, model card, license, tested timestamp |
| Minimal inference | Sanitized request configuration, response metadata, usage, wall time |
| Structured proposal | One valid constraint-linked action proposal JSON and rejection of malformed output |
| Tool loop | Model proposes one allowed read/probe; backend validates and executes |
| Sandbox access | Real image listing and bounded command, not request confirmation alone |
| Branching | Two child executions from the same recorded parent, with separate artifacts |
| Cleanup/cancel | Timeout/cancel behavior and operation reconciliation observed |

Keep the gate small. One working model is sufficient to start; multi-model routing is optional.

## Model selection

Prefer an available NVIDIA Nemotron model that handles code reasoning and the tested structured-output/tool flow at acceptable latency. Nano/Super/Ultra names are families or candidates, not configured endpoint identifiers.

Select one primary model using the same five development cases: valid tool proposal, useful constraint-linked diagnosis, bounded patch, clean-case restraint, and malformed-output handling. Record successes, latency, and token counts. If strict JSON schema is unsupported, use constrained JSON output plus server validation and at most one formatting repair. Unsupported tool calling can be represented as validated action JSON, without granting a shell tool.

If a smaller NVIDIA model fails repair quality, try another available NVIDIA candidate before adding a different provider. Do not remove the required model from the meaningful runtime path.

## Minimal inference check

Illustrative client configuration, to be implemented and tested after credential setup:

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["NEBIUS_API_KEY"],
    base_url="https://api.tokenfactory.nebius.com/v1/",
    timeout=30.0,
    max_retries=0,
)
available = client.models.list()
selected = os.environ["NEBIUS_MODEL_ID"]
assert selected in {item.id for item in available.data}
reply = client.chat.completions.create(
    model=selected,
    messages=[{"role": "user", "content": "Suggest one bounded check for a Python invoice-total constraint."}],
    max_tokens=256,
)
```

This smoke check tests connectivity only. The application's actual contract must validate provider parameters and response schemas. Never print API keys or full authorization headers. The sample does not select a model or establish its NVIDIA origin; the model card check does that.

## Execution adapter contract

Expose application methods `prepare`, `run_probe`, `apply_patch`, `verify`, `cancel`, and `collect_artifacts`. These are BenchProof interface names, not claims about exact SDK methods. Map them to the current Contree SDK and transport after a working preflight.

Record base image digest, checkpoint identifiers, operation identifiers, exits, timings, and artifact references. Test transport authentication, project scope, context-manager/lifecycle behavior, polling, result retrieval, and cleanup against the actual installed SDK. Use immutable digests rather than `latest` for final runs.

## Fallback decision by 6 October

If sandbox access is unavailable, continue UI and orchestration with labeled mocks while investigating an isolated runner on Nebius AI Cloud. Confirm actual provisionable compute, applicable credits, enforceable isolation, and the track interpretation. A standalone local container plus a provider logo does not demonstrate the intended hosted execution story.

Document the selected final route in [decisions](../planning/DECISIONS.md). If no appropriate execution route exists, mark the release blocked and narrow the implementation; never invent successful sandbox runs.

## Provider resilience

Bound each request, reserve estimated worst-case usage, and permit at most two retries for known safe transient inference failures within the total budget. Do not retry unknown execution submissions until operation reconciliation establishes whether the first started. Preserve model ID, prompt version, structured action, timestamps, and usage while excluding private chain-of-thought and secrets.

## Meaningful sponsor evidence

The visible audit must contain a real model-assisted experiment or patch. Show the inference and execution backend accurately in the UI. A development-time use of a model is different from the required runtime integration; document both truthfully.

## Research-driven integration decisions

The NVIDIA model's runtime role is investigation and repair under current engineering constraints. Send a bounded context packet with source/contract/graph hashes, affected code, current reviewed decisions, public check IDs and sanitized observations. Keep hidden truth/oracle implementation out of model input. Validate the proposal again against current hashes before application.

One tested NVIDIA model remains sufficient. The research's cost-aware multi-provider vision is P2; do not add subscriptions or route the meaningful runtime work away from the qualifying model. A second NVIDIA tier may be tested after actual quality/latency/usage measurements, with one recorded bounded escalation inside original limits.

Provider-neutral patch/trace schemas are application interfaces, not a claim that Cursor, Codex, Claude Code or other products have been integrated. Adapters are optional. Independent acceptance remains deterministic and protected; another model role cannot supply the final truth. The runner preflight must show fresh candidate state and evaluator assets absent from its editable tree.
