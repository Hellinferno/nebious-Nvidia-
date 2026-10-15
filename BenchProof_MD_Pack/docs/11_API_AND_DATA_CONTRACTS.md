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
| POST `/api/v1/audits/{id}/decisions` | Record proposed or human-reviewed decision with server-computed dependencies | Owner; at least one file/source/contract/graph dependency |
| GET `/api/v1/audits/{id}/context` | Rebuilt current source/contract/graph/decision packet | Owner; stale and unreviewed decisions excluded |
| GET `/api/v1/audits/{id}/trajectory` | Fingerprint rule, recovery count and original remaining limits | Owner; persisted audit/action state |
| POST `/api/v1/audits/{id}/recover` | Consume the single changed-strategy recovery | Owner; audit must be STALLED with action/time budget remaining |
| POST `/api/v1/audits/{id}/mutations` | Run at most three relevant trusted semantic mutants | Owner; VERIFIED baseline, accepted patch and execution budget |
| GET `/api/v1/audits/{id}/mutations` | Read immutable strength runs and explicit outcome counts | Owner; policy stays separate from gate verdict |
| POST `/api/v1/audits/{id}/patch` | Authorized developer diff import; stored as `PENDING` | Disabled for arbitrary public intake; base hash and current context validated |
| GET `/api/v1/patches/{id}` | Normalized diff and policy result | Owner via parent audit |
| POST `/api/v1/audits/{id}/verify` | Fresh protected gate; records the next verification attempt and writes `APPROVED`/`REJECTED` on the patch | Owner, isolated runner ready, patch belongs to the audit, budget |
| GET `/api/v1/audits/{id}/gate` | Latest attempt's check results and attempt number | Owner |
| POST `/api/v1/audits/{id}/cancel` | Durable cancellation request | Owner; remote reconciliation follows |
| GET `/api/v1/audits/{id}/bundle` | Safe immutable evidence download | Owner; hash/secret checks passed |
| GET `/api/v1/skills` | Versioned catalog of bounded skills with session-level availability | No model call; availability from cached readiness |
| GET `/api/v1/audits/{id}/skills` | Same catalog with availability, cost and blocked reason computed from this audit's record, budgets and runtime | Owner; invoking a skill means calling its listed endpoint, which repeats every check |

Use structured body arguments, not source paths in URLs. Audit, event, patch, gate, bundle, replay and skill routes require the opaque `X-BenchProof-Owner` capability and validate it against the parent audit; list results are owner-filtered. This is the bounded demo access mechanism, not production identity authentication. POST idempotency keys bind owner, endpoint and body hash; same key/different body returns conflict. Audit creation under a key writes the audit row, the key record and the `audit_created` event in one serialized transaction, so a duplicate submit replays instead of creating a second audit. Reload/reconnect must not duplicate paid actions.

Skills (`skills-v1`) are named, versioned capabilities (`/start`, `/ready`, `/diagnose`, `/recover`, `/decision`, `/repair`, `/verify`, `/strength`, `/export`, `/validate`, `/replay`, `/cancel`). Each maps to exactly one existing endpoint and declares its cost class (`model-call`, `isolated-execution`, `none`). The catalog never grants anything: availability and `blocked_reason` are advisory and the mapped endpoint repeats every check.

## Required records

| Record | Mandatory fields |
| --- | --- |
| Audit | schema_version, audit_id, owner_ref, fixture/task IDs, source_hash, contract_hash, run_state, gate_verdict, mode, created_at, attempt, limits/reservations |
| Constraint | ID/version, statement, scope, required, protected_check_ids, dependencies, approval_ref, hash |
| Graph | graph_id/hash, source/contract hashes, builder_version, nodes/edges, coverage, unresolved_items |
| Edge | from/to, type, OBSERVED/DECLARED/INFERRED provenance, source span/manifest ref, uncertainty |
| Context | context_hash, source/contract/graph hashes, current_decision_ids, excerpts, selected_checks, unresolved_coverage, remaining_budget |
| Decision | ID, statement, PROPOSED/REVIEWED state, CURRENT/STALE/SUPERSEDED freshness, typed dependency expected/current hashes and CHANGED/DELETED reason, evidence IDs, owner/role, timestamp, supersedes, revisit_condition, validation overhead |
| Action | action_id, role, tool, strategy, canonical_args_hash, source/context hash, observation IDs/fingerprints, failure category/fingerprint, usage, elapsed, remaining original limits, status |
| Patch | patch_id, base_hash, diff_hash, approved_paths, changed_lines, targeted_constraints, policy_result (`PENDING` until the protected gate writes `APPROVED` or `REJECTED`), author/provider metadata |
| CheckResult | check_id/version, attempt, patch_id, patch/source/contract/image/evaluator hashes, PASS/FAIL/UNKNOWN, oracle_kind, observation refs, duration, reason |
| MutationResult | template/version/family, base and mutant hashes, validity, KILLED/SURVIVED/INVALID/SKIPPED/UNKNOWN, supporting and selected check IDs, duration/reason |
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

Event types include audit_created, state_changed, graph_built, coverage_limited, context_stale, decision_invalidated, action_started/completed, check_failed, patch_proposed/rejected, stalled, recovery_started, verification_completed, mutation_completed, budget_exhausted, cancel_pending, cancelled and bundle_ready. `CANCEL_PENDING` is non-terminal: a worker-side reconciliation may move it to `CANCELLED` only after remote termination is confirmed.

Events have audit/attempt/sequence/timestamp and an artifact/result ID. SSE replays from `Last-Event-ID`; the snapshot remains authoritative if retention has expired. Terminal event emission follows committed results.

Error codes: INVALID_INPUT, INVALID_STATE, OWNER_DENIED, SOURCE_LIMIT, STALE_SOURCE, STALE_CONTEXT, STALLED, RECOVERY_EXHAUSTED, CONTRACT_UNAPPROVED, REQUIRED_CHECK_MISSING, GRAPH_UNRESOLVED, PATCH_PROTECTED_PATH, PROVIDER_UNAVAILABLE, RUNNER_UNAVAILABLE, BUDGET_EXHAUSTED, CHECK_UNKNOWN, MUTATION_INVALID and CANCEL_PENDING. Safe user messages explain the next action; internal details remain sanitized server records.

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

Candidate output cannot write CheckResult or gate_verdict. VERIFIED requires matching manifests and PASS for every required check; skipped/UNKNOWN required checks forbid it. One active lease owns a run; compare-and-swap transitions commit the state change and its `state_changed` event together. Every patch belongs to its audit/owner. Results are immutable; every gate run stores its complete check set atomically as the next attempt, `checks.json` carries the latest attempt plus the attempt count, and earlier attempts stay readable. State writes that follow verification or investigation are guarded: a cancelled, timed-out, failed or blocked audit keeps its state while the evidence is still recorded. Source, intake, decision-dependency and suite-lock hashes are computed over LF-normalized bytes so a CRLF checkout and an LF checkout agree.

Isolated observations are accepted only when the launcher parent's final stdout record equals `/out/observations.json`; the candidate runs in a child process with a cleared environment and exits without atexit hooks, and the `worker-caller-path` check (version 2) requires a live static delegation plus observed worker idempotency across a repeated and a conflicting job.
