# Changelog

## 2026-10-05 — Days 2–3: isolated runner boundary, approved constraints, durable state

- Provider: first real NVIDIA inference on Nebius (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`), structured-JSON proposal validated server-side; credential identified as a short-lived session token (owner must create a long-lived key).
- Execution: `benchproof.execution` adapter contract; `DockerRunner` (network none, read-only, cleared env, caps, timeout kill) and labeled `MockRunner`; protected launcher `runner/launcher/observe_invoice.py`; pinned candidate image `backend/runner/image/Dockerfile`; `scripts/runner_preflight.py`. Nebius Sandboxes recorded BLOCKED (no spawn permission); Contree SDK 0.3.6 installed for the record (D-024).
- Evaluator: single observation-based oracle shared by the in-process harness and the Docker runner; expected values never read from candidate output; forged PASS text ignored.
- Constraints: executable check registry; `approve_manifest` rejects relaxed/unknown/incomplete proposals (CONTRACT_UNAPPROVED) and missing oracles (REQUIRED_CHECK_MISSING); registry validated at API startup.
- Storage: leases, CAS transitions, ordered events, idempotency keys, SQLite triggers making check_results/artifacts immutable, evaluator-only check/verdict writes that must agree with stored checks.
- API: `Idempotency-Key` on `POST /audits` (replay vs 409 conflict), `contract_hash` pin, `GET /audits/{id}/events` as JSON or SSE with `after`/`Last-Event-ID`, CAS cancel with events, cached runner readiness.
- Tests: 76 pytest cases (3 Docker-backed, skipped without a daemon); ruff clean. No graph, patch, export, deployment or hosted sandbox run is claimed.

## 2026-10-04 — Day 1 scaffold (B-02 done; B-03 in progress; B-04 blocked)

- Backend: installable `benchproof-backend` package with `requirements.lock.txt`; FastAPI `health`, `ready`, `examples`, `constraints`/`contracts`, `audits` (create/get/list/cancel); SQLite migrations incl. worker heartbeats; lifespan-based startup.
- Constraints: pinned C-API, C-AMOUNT, C-INTEGRITY v1 with canonical hashes and a combined contract hash.
- Fixtures: five `development-v2` cases (AC-01, MC-01, CI-01, ID-01, clean-service) with public `fixture.json`, trusted `expected.json` and `reference/` repairs kept outside `app/`; source hashing per fixture.
- Evaluator: seven deterministic checks; gate returns VERIFIED / REJECTED / INCONCLUSIVE; development harness and `scripts/validate_fixtures.py` validate faulty, reference and clean behavior.
- Provider: Nebius Token Factory adapter (timeout, no retries); `scripts/provider_preflight.py` fails explicitly without a key and writes a sanitized record.
- Worker: `scripts/start_worker.py` heartbeat only; no candidate execution exists.
- UI: reads real `/api/v1` records and shows mode, provider/runner/worker state, constraints and examples.
- Tests: 40 pytest cases; ruff and oxlint clean. No model call, runner, graph, patch, export or deployment is claimed.

## 2026-10-03 — research-aligned planning pack v2

- Applied the recovered coding-agent research and checked comparison claims against primary product documentation.
- Kept the BenchProof name and Coding and Agentic Engineering track; changed the active product to an Agentic Engineering Assurance Runtime.
- Replaced ML leakage/metric fixtures with a multi-module Python service and API, exact-amount, caller-impact, and idempotency repair families.
- Added executable constraints, a typed state graph, source-linked decision freshness, deterministic risk reasons, trajectory stopping/recovery, independent adversarial verification, and bounded trusted mutations.
- Revised every previous Markdown document, the backlog, and all 28 daily sessions. Preserved freeze, submission buffer, provider integration, isolation, rights, and judging-access obligations.
- Separated repair, gate, graph, freshness, trajectory, and mutation evaluations; specified fair optional external-agent comparisons without fabricated results.
- Added research/positioning, detailed runtime, competitor benchmark, and migration-map documents. Rebuilt the pack archive.

This is a documentation revision. No feature, benchmark, competitor outcome, deployment, or submission is marked completed by it.

## 2026-10-03 — planning pack v1, superseded scope

Created the initial ML experiment-audit plan, event/source checks, execution schedule, independent verification concept, and early submission target. Its active ML/scikit-learn scope is superseded by v2; those original implementation tasks were not completed.

## Future release entry

- Date, tag, and full commit:
- User-visible behavior and supported contract families:
- Implemented assurance components and explicit exclusions:
- Model/provider and runner/image versions:
- Accepted contract/evaluator/suite hashes:
- Tests and measured result artifacts, including failures:
- Deployment and replay evidence:
- Known coverage limits and rollback reference:
