# API, state, and evidence contracts

Research-aligned schema target: `benchproof/v2`. Implement strict typed records and migrations before UI integration. Examples below are illustrative shapes, not output from a built service.

## Endpoints

| Method/path | Purpose | Preconditions |
| --- | --- | --- |
| GET `/api/v1/health` | Liveness with safe mode/version | No secrets or internal topology |
| GET `/api/v1/ready` | Worker/store/provider configuration ready | Do not bill a model call on every poll |
| GET `/api/v1/examples` | Approved curated fixtures and scope | Only public manifest fields |
| GET `/api/v1/contracts/{id}` | Accepted public constraint summary | Approved version; hidden oracle excluded |
| POST `/api/v1/audits` | Start bounded audit for fixture/task/preset | Session quota, idempotency key, accepted contract |
| GET `/api/v1/audits/{id}` | Snapshot, versions, budget, lifecycle/verdict | Owner check |
| GET `/api/v1/audits/{id}/events` | SSE with sequence/resume cursor | Owner check; bounded retention |
| GET `/api/v1/audits/{id}/impact` | Graph subset, risk reasons, coverage | Current source/graph version |
| GET `/api/v1/audits/{id}/decisions` | Reviewed/proposed/stale ledger | Owner; no private reasoning |
| POST `/api/v1/audits/{id}/patches` | Authorized developer diff import | Disabled for arbitrary public intake; base hash validated |
| GET `/api/v1/patches/{id}` | Normalized diff and policy result | Owner via parent audit |
| POST `/api/v1/patches/{id}/verify` | Request fresh protected gate | Owner, approved patch/contract, budget reservation |
| POST `/api/v1/audits/{id}/cancel` | Durable cancellation request | Owner; remote reconciliation follows |
| GET `/api/v1/audits/{id}/bundle` | Safe immutable evidence download | Owner; hash/secret checks passed |

Use structured body arguments, not source paths in URLs. POST idempotency keys bind owner, endpoint and body hash; same key/different body returns conflict. Reload/reconnect must not duplicate paid actions.

## Required records

| Record | Mandatory fields |
| --- | --- |
| Audit | schema_version, audit_id, owner_ref, fixture/task IDs, source_hash, contract_hash, run_state, gate_verdict, mode, created_at, attempt, limits/reservations |
| Constraint | ID/version, statement, scope, required, protected_check_ids, dependencies, approval_ref, hash |
| Graph | graph_id/hash, source/contract hashes, builder_version, nodes/edges, coverage, unresolved_items |
| Edge | from/to, type, OBSERVED/DECLARED/INFERRED provenance, source span/manifest ref, uncertainty |
| Context | context_hash, source/contract/graph hashes, current_decision_ids, excerpts, selected_checks, unresolved_coverage, remaining_budget |
| Decision | ID, statement, status/freshness, dependency hashes, evidence IDs, owner/role, timestamp, supersedes, revisit_condition |
| Action | action_id, role, tool, canonical_args_hash, source/context hash, observation IDs, failure_fingerprint, usage, elapsed, status |
| Patch | patch_id, base_hash, diff_hash, approved_paths, changed_lines, targeted_constraints, policy_result, author/provider metadata |
| CheckResult | check_id/version, patch/source/contract/image/evaluator hashes, PASS/FAIL/UNKNOWN, oracle_kind, observation refs, duration, reason |
| MutationResult | template/version, mutant_hash, validity, KILLED/SURVIVED/INVALID/INCONCLUSIVE/SKIPPED, supporting_check_ids |
| Artifact | artifact_id, owner/audit/attempt, relative name, MIME, byte size, sha256, visibility |

Any inferred/unknown field is explicit. Prefer null plus reason over a false zero or empty-success value. Validate enum values, size limits, referential integrity and content hashes at write boundaries.

## Illustrative constraint shape

```json
{
  "schema_version": "benchproof/v2",
  "constraint_id": "C-AMOUNT",
  "version": 1,
  "statement": "Sum Decimal strings; round once on invoice total using ROUND_HALF_UP; return two decimals",
  "scope": ["app/money.py", "app/services.py", "app/worker.py"],
  "required": true,
  "protected_check_ids": ["amount-boundary", "caller-consistency"],
  "approval_ref": "OWNER_APPROVAL_TO_RECORD",
  "hash": "COMPUTE_FROM_CANONICAL_RECORD"
}
```

Placeholders above must become actual validated values in implementation. Do not treat illustrative strings as accepted hashes or approval.

## Events and errors

Event types include audit_created, state_changed, graph_built, coverage_limited, context_stale, decision_invalidated, action_started/completed, check_failed, patch_proposed/rejected, stalled, recovery_started, verification_completed, mutation_completed, budget_exhausted, cancel_pending, cancelled and bundle_ready.

Events have audit/attempt/sequence/timestamp and an artifact/result ID. SSE replays from `Last-Event-ID`; the snapshot remains authoritative if retention has expired. Terminal event emission follows committed results.

Error codes: INVALID_INPUT, OWNER_DENIED, SOURCE_LIMIT, STALE_SOURCE, CONTRACT_UNAPPROVED, REQUIRED_CHECK_MISSING, GRAPH_UNRESOLVED, PATCH_PROTECTED_PATH, PROVIDER_UNAVAILABLE, RUNNER_UNAVAILABLE, BUDGET_EXHAUSTED, CHECK_UNKNOWN, MUTATION_INVALID and CANCEL_PENDING. Safe user messages explain the next action; internal details remain sanitized server records.

## Evidence bundle

| Entry | Contents |
| --- | --- |
| `manifest.json` | Schema, versions, accepted scope, verdict, artifact hashes, omissions |
| `constraints.json` | Accepted public behavior and check mappings |
| `state.json`, `coverage.json` | Graph subset, provenance and unresolved scope |
| `decisions.json`, `trajectory.jsonl` | Source-linked ledger and concise actions |
| `candidate.diff`, `source-manifest.json` | Base/patch linkage and source hashes |
| `checks.json`, `mutations.json` | Actual results; NOT_RUN where absent |
| `environment.json`, `usage.json` | Image/runner/model config and known usage/prices |
| `report.md`, `REPLAY.md` | Readable review decision and isolated replay procedure |

Hash canonical UTF-8 JSON with fixed key ordering; store SHA-256 separately from display summaries. Archive entries use safe normalized relative paths and bounded total sizes. Verification of manifest consistency runs without code execution; executable replay remains isolated.

## Storage invariants

Candidate output cannot write CheckResult or gate_verdict. VERIFIED requires matching manifests and PASS for every required check; skipped/UNKNOWN required checks forbid it. One active lease owns a run; compare-and-swap transitions prevent duplicate verifier results. Every patch belongs to its audit/owner. Results are immutable; corrections create new versioned attempts linked to the old record.
