# BenchProof Runtime Integrity Report v1

Date: 2026-10-14
Ticket: B-17
Schema: `benchproof/integrity-report-v1`

## Outcome

BenchProof now fails closed at every public candidate-execution entry point. Public verification, mutation assessment, and evidence replay require a configured, ready Docker runner; none can fall back to the development in-process evaluator. If Docker is unavailable, these capabilities return `RUNNER_UNAVAILABLE` and the UI disables them.

## Enforced controls

| Surface | Backend enforcement | Negative evidence |
| --- | --- | --- |
| Prompt injection | Repository excerpts are data under the system prompt; model output must match a strict, extra-forbidden schema; probe names are allowlisted and probe arguments must be empty. | Command-like probes and model-selected arguments fail schema validation. |
| Evaluator/contract edits | Strict modify-only unified diffs may touch at most three `.py` files rooted under `app/`; evaluator, contract, test, runner, reference, and expected-truth paths are denied case-insensitively. | Traversal, protected paths, creation/deletion, renames, mode changes, binary patches, git metadata, and target/header mismatches are rejected. |
| Forged PASS or missing output | Candidate verdict/check fields are ignored. The protected evaluator recomputes every result; required failures reject and missing/unknown checks are inconclusive. | A forged `VERIFIED` observation remains `REJECTED`; absent observations remain `INCONCLUSIVE`. |
| Stale source/context | Patch base hashes are checked again immediately before copying/applying; hunk context and line counts must match. Decision/source/contract context is recomputed after model calls. | Wrong base hashes, forged hunk context, and delayed stale context are rejected. |
| Intake and paths | Candidate intake accepts regular, non-linked files only and enforces per-file, total-byte, and file-count ceilings. | Traversal, absolute/out-of-scope paths, protected names, symlink files/directories, and oversized trees fail intake. |
| Ownership | Every audit-derived API route resolves the audit and compares its owner capability before reading or mutating records. Patch verification also checks audit parentage. | Cross-owner audit, event, patch, mutation, bundle, and replay requests return `OWNER_DENIED`; cross-audit patches return `PATCH_NOT_FOUND`. |
| Runtime isolation | Docker uses no network, a read-only root, non-root user, dropped capabilities, no-new-privileges, read-only candidate/launcher mounts, cleared environment, memory/PID/CPU/tmpfs caps, and a wall-clock kill. | Actual internet and metadata probes run only when Docker is available. Unavailable isolation blocks public verification/replay instead of falling back. |
| Output/resource limits | Stdout and stderr are drained with 64 KiB retained caps each; observations are capped at 256 KiB; artifacts are capped at 16 files and 512 KiB total. | Truncated output is marked; malformed, linked, oversized, or wrong-schema observation files cannot become evaluator input. |
| Cancellation | A remote reservation transitions to `CANCEL_PENDING`; only confirmed remote termination can transition it to `CANCELLED`. | Repeated cancellation is idempotent while pending; an unconfirmed remote stop cannot claim cancellation. |
| Archives and exports | Output names must be safe `.zip` names. Validation rejects duplicate, encrypted, linked, directory, traversal, oversized, high-ratio, unmanifested, missing, or hash-mismatched entries before replay. | Duplicate-name and entry-count archives fail non-executing validation. |
| Secrets and hidden truth | Export content is scanned for provider tokens, bearer values, common credential assignments, AWS access keys, private keys, `expected.json`, reference repairs, and intended-failure metadata. | Matching content raises `SecurityExclusionError` and bundle export is refused. |

## Blocked capabilities and remaining limitations

- Public verification, mutation assessment, and bundle replay are unavailable unless `BENCHPROOF_RUNNER=docker` and the Docker daemon plus pinned image are ready.
- Nebius hosted sandbox spawning is still unavailable, so no hosted isolation claim is made.
- `X-BenchProof-Owner` remains an opaque browser-generated local/demo capability, not production identity authentication.
- The in-process evaluator remains available only as an explicit development/library harness for curated fixtures and tests; it is not a public API execution mode.
- Output retention is bounded, but the host bind-mounted artifact directory has no filesystem quota. The container timeout and post-run artifact limits reduce exposure; production deployment should use a quota-backed scratch volume.

## Addendum — 14 October, second hardening pass (Day 15 pulled forward)

| Surface | Backend enforcement | Negative evidence |
| --- | --- | --- |
| Observation authorship | The launcher parent never imports candidate code: the candidate runs in a child process (`python -I`, cleared environment) that prints one record and exits with `os._exit`; the parent writes `/out/observations.json`, prints the same record last and exits without atexit hooks. The host accepts observations only when the parent's stdout record equals the file. | A file-only record, an altered file and a missing stdout record are each rejected (`test_hardening_day15.py`). |
| Output file identity | `observations.json` must be a regular, non-linked file under the size cap (`lstat`); a timeout discards any partial observations. | Linked or oversized files and timeouts produce no evaluator input. |
| Worker delegation | `worker-caller-path` v2 requires a live call to `services.process_invoice` inside a function (dead-code and module-level calls do not count) and observed idempotency across a repeated and a conflicting worker job. | Dead-code delegation, a replaced receipt on repeat and a replaced receipt on conflict all FAIL; missing dynamic observation is UNKNOWN. |
| Fixture resolution | Fixture ids must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` and resolve directly under the fixtures root. | `C:x`, separators, `..` and hidden names are rejected. |
| Patch application | Zero-length old ranges insert after the named line as GNU patch does; CRLF sources and diffs are normalized and patched files are written with LF. | CRLF inputs produce LF output; applied trees hash identically on any platform. |
| Record atomicity | A state transition and its `state_changed` event commit together; a gate run stores its complete check set as the next attempt in one transaction; audit creation under an `Idempotency-Key` writes the audit, the key and the event in one serialized transaction. | A duplicate inside a batch stores nothing; a rejected CAS leaves no event; a replayed key never creates a second audit. |
| State guarding | Writes that follow verification or investigation touch only active audits. | A cancelled audit keeps `CANCELLED` and `PENDING` after a gate run while its checks are still recorded. |
| Patch policy authority | Proposals are stored `PENDING`; only the acceptance gate writes `APPROVED`/`REJECTED`. | The API returns `PENDING` on proposal; the gate flips it after an isolated verification. |
| Budget accounting | Mutation reservations are taken only after candidate validation and returned when the baseline is not VERIFIED. | An unverified baseline leaves exactly the spent baseline charged. |

The Docker daemon (29.7.2) and the pinned candidate image became available during the pass, so the three isolated-runner tests executed the new parent/child launcher inside the container: the clean control was judged VERIFIED, MC-01 REJECTED, and a stalled launcher was killed at the timeout with no observations accepted. `scripts/run_integrity_evidence.py` then recorded `runtime_isolation` as PASS for the first time (it was BLOCKED in the B-17 record): internet and metadata probes denied, no secret environment names, no trusted assets in the candidate tree, candidate mount not writable, image `benchproof-candidate:dev@sha256:fbe0b348a6ad…`.

Known flake: on this Windows host `docker info` took about 32 seconds, just over the runner's 30-second readiness probe. The first evidence run therefore failed closed with `RUNNER_UNAVAILABLE` and the retry passed. Nothing is accepted when the probe times out, but a slow daemon can make readiness and verification intermittently unavailable.

## Reproduction

Run from `backend/`:

```powershell
$env:TEMP = (Resolve-Path .).Path + "\pytest-day13-temp"
$env:TMP = $env:TEMP
python -m pytest tests/test_security_day13.py tests/test_execution.py tests/test_lifecycle.py -q --basetemp pytest-day13
python scripts/run_integrity_evidence.py
```

The JSON evidence is written to `artifacts/integrity/day13_integrity.json`. Docker-dependent evidence is `PASS` only after live network/metadata probes and isolation assertions succeed; otherwise it is recorded as `BLOCKED`, never silently passed.
