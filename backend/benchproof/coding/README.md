# Coding runtime

Current runtime: durable owner-scoped tasks, a separately configured leased worker,
reviewed plans, bounded model edits, isolated checks, checkpoints and export are
implemented. The public deployment and its evidence are described in the root
`VERIFICATION.md`; local changes are not deployed just by editing or pushing files.

`generation.py` defines `coding-brief-v1`, `coding-plan-v1` and the line-based
`coding-edit-v2` response contract, with strictly parsed `coding-edit-v1` compatibility.
Plans bind the task's exact identity, source and editable
paths; edits bind the approved plan revision. The current check profile is the
curated `invoice-observation-v1`, or `project-unittest-v1` for imported projects.
Only unittest is supported; unsupported runner labels must fail before paid work
or candidate execution. Imported project checks are user-supplied evidence, not
the stronger independent protected invoice gate.

`generate_edits` makes one bounded provider request, validates the completion and
complete-file edits, builds a deterministic modify-only diff, checks its round trip
and enforces the existing patch policy. It does not apply or execute source. The
caller must durably reserve the paid action first. These contracts are primitives
used by the durable task API/store/worker. Do not expose this function directly as
an unmetered public request handler. `store.py` owns action reservations and
idempotency; `worker.py` owns leases/reconciliation; `engine.py` performs bounded
planning/edit/check stages. `runtime.py` requires explicit enabled/provider/runner,
daily allowance and deadline settings before admission.

The root README documents API + worker + frontend startup and no-spend defaults.
`AGENT_CUSTOMIZATION.md` documents frozen skills, reviewed harnesses and the bounded
MCP reference bridge. `DATA_RETENTION.md` defines current admission/deletion scope.

The shared structured-output boundary rejects length-limited, interrupted, empty,
oversized, schema-invalid and duplicate-key responses without guessing missing
claims, source locations or JSON endings. No automatic format retry or mock
fallback occurs. Recorded usage remains available on rejected responses; a
transport failure's usage is UNKNOWN, not zero.

## Generation policy v3 — 22 October

After the owner resumed bounded live verification, v2 was tested separately in
staging with three calls, a 4,096-output-token allowance, two edits and four-check
ceiling. It failed safely: the first candidate repeated the unquoted annotation
NameError; its revision encoded physical line breaks as literal backslash-n text.
The final state is BLOCKED, with three calls and three isolated
executions; no final check passed. The larger allowance is not the production
default or a matched comparison. Prior failures remain unchanged.

The new local `coding-generation-v3` requests complete files as `files[].lines`:
one physical line per array item. The trusted runtime joins them with LF. Embedded
line breaks/NULs, excessive lines/text, mixed schema encodings and protected paths
are rejected. Legacy v1 content is accepted only as literal parsed source, without
unescaping or guessing a repair. Changed Python files must parse as Python 3.12
before any patch can be returned or candidate execution reserved. AST parsing does
not execute imports, annotations or top-level statements and does not prove runtime
correctness. Syntax failures retain usage and stop with INVALID_PYTHON; they do not
trigger a paid retry. A later isolated baseline/candidate/final check is still required.

Bounded-loop exhaustion now reports PATCH_ATTEMPT_LIMIT instead of a misleading
single-pass stop. The frontend's historical HARNESS_STOPPED wording is neutral
because old tasks can record that code after more than one attempt.

The initial v3 snapshot was local and unmeasured. A separately authorized staging
run now reaches REVIEW_READY after one failed annotation candidate and one model
revision: three calls, two edits, four isolated executions, all six candidate and
fresh final methods pass. Both edits use the line-based contract; no source is
unescaped or manually repaired. This known-sample result is not first-pass success
or a held-out benchmark. See `verification/policy-v3-live-2026-10-22-results.json`.

Both edit completions exceed 2,048 tokens. The owner approves 4,096 output tokens
for the private production backend while retaining daily limits. Library defaults
remain 2,048; provider reasoning settings, SDK retries, protected tests and
candidate limits do not change. Exact deployed identity and public checks are in
root `VERIFICATION.md`. Both separately resumed authorizations are consumed; no
additional inference is authorized. Inspect/export old tasks rather than silently
migrating their pinned model, output allowance or prompts.

## Historical generation policy v2 — 22 October

`prompts.py` identifies `coding-generation-v2` by the exact trusted plan/edit
prompt text. Prompts now specify Python 3.12, import-time forward-reference
semantics, use of previous candidate feedback, and concise complete-file JSON.
These are generic instructions, not a hard-coded repair for a sample.

API task creation pins this version/hash in `runtime_config.generation_policy`.
The API enqueue guard and live worker compare it before reserving paid work.
Policy-less older tasks or a changed prompt fail `STALE_RUNTIME`; inspect/export
their evidence and create/review a new task rather than silently upgrading them.
JSON/ZIP exports retain the task's original allowlisted runtime identity, not the
current process's policy. Provider metadata includes the policy on completed and
rejected requests.

The output allowance remains 2,048 tokens by default; provider settings, retries,
candidate limits and protected tests are unchanged. Truncation still rejects the
whole proposal, with no format repair, paid retry or canned replacement. Prompt
guidance is not an enforced guarantee of valid Python or provider reasoning mode.
NVIDIA documents reasoning controls for its model, but equivalent support on this
exact Nebius endpoint is not verified, so no speculative flag is sent.

The initial no-spend v2 candidate was not deployed or live-model measured; that
snapshot is `verification/generation-policy-v2.json`. The owner later resumed one
bounded staging run, which failed as recorded above. The 21 October failures and
denominators remain unchanged; no mock/static/saved-error check establishes new
model success.

## Historical first-increment generation checks

From the repository root, with the existing backend environment:

```powershell
backend/venv/Scripts/python.exe backend/scripts/check_coding_generation.py --run-id unique-offline-id
```

This default only replays locally retained AC-01 truncation records. It makes no
inference call. Missing historical local artifacts are reported, not fabricated.
The old public diagnosis HTTP 422 record did not capture its response cause; this
tool does not retroactively establish that cause.

`--live-once` explicitly enables one paid request, at most 2,048 output tokens and
no retry, against the public MC-01 sample. The acceptance plan is operator-scoped,
**not model-generated**. The run directory must be new. A durable exclusive call
reservation precedes the request; crash-unknown reservations are not erased or
automatically replayed. Actual recorded tokens are separate from monetary cost,
which remains UNKNOWN. Review credits before authorizing another run.

`--verify` additionally requires local Docker and runs at most the original and
candidate in isolated containers. There is no host-execution fallback. Without
this option, success means `GENERATED_POLICY_VALIDATED`, not passing tests.

For the already saved model edit, the separate cloud check makes **no inference**:

```powershell
backend/venv/Scripts/python.exe backend/scripts/verify_generated_patch_cloud.py --run-id existing-live-id
```

It first verifies that the diff reproduces the saved model's exact file content,
then pins the source and imports that diff through the existing public audit API.
Four non-retried mutations create the audit, check the original, propose the patch
and check the candidate. Its own exclusive reservation prevents accidental reruns.
This uses existing cloud execution, not a deployment of the new generation module
or an app-connected agent loop. A saved partial failure needs reconciliation,
not deletion of the reservation and a blind rerun.

## Observed acceptance

`artifacts/coding/c01-live-20261017-1/` retains the scoped task, actual provider
response, generated diff, call reservation, local report and cloud report. One
NVIDIA request recorded 971 prompt + 1,183 completion = 2,154 tokens, 5,068 ms.
The original MC-01 failed `amount-boundary`; that exact generated patch passed all
seven protected checks in the existing Vercel Docker runner. Audit
`audit-1ba1aab76133`, patch `patch-a2b556ff90cf`. No candidate code ran locally;
the original fixture was unchanged. This is one development acceptance sample,
not a benchmark, general-project support or proof of all requirements.

This historical sample does not substitute for current-release full browser
rehearsals or held-out model evaluation. Follow the R-series release plan in the
root `BUILD_PLAN.md`; C-09 measurement and actual competition submission remain
separate acceptance gates.
