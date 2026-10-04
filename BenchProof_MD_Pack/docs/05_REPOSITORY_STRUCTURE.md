# Planned repository structure

Research revision: source layout now centers on an assurance runtime. The paths and commands below are targets, not files shipped in this Markdown pack.

## Target paths

| Path | Responsibility |
| --- | --- |
| `README.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/`, `planning/` | Working documentation and source-work instructions |
| `LICENSE`, `THIRD_PARTY_NOTICES.md` | Actual license text and component attribution |
| `backend/pyproject.toml`, dependency lock | Installable Python package and tested dependency graph |
| `backend/benchproof/api/` | FastAPI endpoints, session/owner checks, validation and event streaming |
| `backend/benchproof/domain/` | Contract, graph, decision, trajectory, patch, check and bundle schemas |
| `backend/benchproof/constraints/` | Approval/pinning, required-check registry, scope and hash validation |
| `backend/benchproof/state/` | Python AST index, reviewed manifest links, adjacency store, freshness |
| `backend/benchproof/impact/` | Changed-symbol mapping, reverse traversal, risk rules, context packets |
| `backend/benchproof/agent/` | Logical role prompts, structured proposal validation and repair policy |
| `backend/benchproof/runtime/` | Orchestrator, leases, budgets, failure fingerprints and recovery |
| `backend/benchproof/providers/` | Nebius inference adapter; provider-neutral patch/trajectory interfaces |
| `backend/benchproof/execution/` | Contree or tested alternate adapter, operation lifecycle and limits |
| `backend/benchproof/evaluator/` | Trusted oracles, immutable checks, deterministic gate and mutation templates |
| `backend/benchproof/evidence/` | Canonical manifest, hash validation, report and safe export |
| `backend/benchproof/storage/` | SQLite migrations, artifact references, ownership and retention |
| `frontend/src/` | Example, constraints, impact, run, diff, verdict and export views |
| `fixtures/development/` | Visible synthetic service cases and reference repairs |
| `fixtures/public/` | Curated live examples and safe candidate presets |
| `evaluation/private/` | Frozen hidden truth/oracles outside agent context; exclude from public build until evaluation completes |
| `evaluation/manifests/` | Suite IDs, source hashes, split suite definitions and run plans |
| `tests/` | Trusted boundary, lifecycle, graph, freshness, loop and UI checks |
| `scripts/` | Preflight, worker, fixture validation, benchmark, summary and replay entry points |
| `.env.example`, `.gitignore` | Safe configuration keys and exclusions; no real credentials |

The invoice fixture contains `app/routes.py`, `schemas.py`, `money.py`, `services.py`, `repository.py`, and `worker.py`. A protected launcher sits outside candidate-editable `app/`. Dependency and contract manifests are registered by the trusted owner; they are not patch targets.

## Build order

1. Domain schemas, pinned contracts, development cases and trusted oracle checks.
2. Real provider and isolated-runner preflight; record actual versions.
3. Durable jobs/budgets plus immutable source hashing and AST/manifest graph.
4. Impact/context selection and one model-generated restricted repair.
5. Independent fresh gate, clean/rejection paths, export/replay.
6. UI and error recovery; then P1 decision freshness, loop recovery and mutations.
7. Frozen suites, hosted access, measured results and release material.

## Boundaries and naming

Policy/evaluator code never enters candidate-editable snapshots. The same runtime path powers UI examples and benchmarks. No separate shortcut “demo verifier.” Keep model interpretations separate from captured observations.

Use stable source, graph, contract, context, decision, action, patch, run, check and artifact IDs. Store immutable artifacts under run/attempt directories. `latest.json` may be a pointer, not benchmark provenance. SQLite constraints prevent cross-owner artifact reuse or conflicting terminal records.

## Planned commands after implementation

```powershell
python scripts/provider_preflight.py
python scripts/runner_preflight.py
python scripts/validate_fixtures.py --suite development-v2
python scripts/build_state.py --fixture invoice-dev-api
python scripts/run_benchmark.py --plan evaluation/manifests/final-plan.json
python scripts/summarize_results.py --runs artifacts/evaluation
python scripts/replay_bundle.py --bundle artifacts/example.zip
```

Add these scripts and exact argument schemas in the referenced tickets before advertising them as runnable. The release README must document the implemented locked install and isolated execution prerequisites.

## Version-control discipline

Commit each daily acceptance gate with evidence references. Freeze suite assets and runtime configuration in recorded commits. Preserve failed records when fixes are made. Functional runtime/evaluator changes invalidate affected quantitative claims until appropriately rerun; documentation-only updates do not require a gratuitous full benchmark.
