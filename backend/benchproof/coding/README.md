# Coding runtime

Current runtime: durable owner-scoped tasks, a separately configured leased worker,
reviewed plans, bounded model edits, isolated checks, checkpoints and export are
implemented. The public deployment and its evidence are described in the root
`VERIFICATION.md`; local changes are not deployed just by editing or pushing files.

`generation.py` defines development `coding-brief-v1`, `coding-plan-v1` and
`coding-edit-v1` contracts. Plans bind the task's exact identity, source and editable
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
