# Public workflow verification

These are public synthetic integration samples, not held-out tasks, competitor
comparisons or a human user study. Results include failures; a safely rejected
patch does not count as an implemented feature.

## Frozen original batch

`public-workflows-v1.json` freezes the task text, original files, protected imported
checks, single-pass limits and expected outcomes before inference. Its SHA-256 is
`115227117b7ecfab6057012039ee4ee38ad9a8e74c1a29e0f2a5af8e069f4dfb`
over UTF-8, LF-normalized bytes. Do not change it to fit later outputs.

`public-workflows-2026-10-21-results.json` is a sanitized summary of the real cloud
run. The feature failed with a Python forward-reference NameError; the clean
control stopped without edits as expected. That is **one expected outcome out of
two**, not two successful feature implementations. Three of four authorized model
calls and three isolated executions were consumed, with no inference retries.
Provider token usage is recorded; listed-price estimates are not actual billing.

To inspect without inference or candidate execution, run from `backend`:

```powershell
python -m pytest tests/test_public_rehearsals.py
```

To reproduce through the application, manually upload one case's `files`, select
its workflow, enter its task, choose `single-pass-v1` and lower the task budgets
to its `limits`. Use the instruction-only skill recorded in the result summary.
Review the model plan and source-bound scope before approving. Planning and
starting consume real provider/runner allowance; they are not part of the static
test above. Preserve new task IDs and all failures instead of overwriting these
results. Do not paste private code or credentials into this public demo.

## Separate follow-up

The owner separately authorized at most three additional model calls, two edit
attempts and four isolated executions on the same BankAccount sample using
`bounded-v1`. This known-sample regression has a larger attempt budget and is
not a matched comparison. Its record must remain separate from the original
two-case denominator; the original failed feature remains a failure.

`bounded-followup-2026-10-21-results.json` records that follow-up: **BLOCKED /
MODEL_OUTPUT_TRUNCATED**, three model calls, two edit reservations and two isolated
executions. Its first candidate again failed class import; the revision response
hit the output limit and was not accepted or executed. This is not a completed
feature. Desktop/mobile inspection, ZIP export, unchanged original source and
reload without additional spend passed as read-only safety checks. No more
inference calls are authorized by these completed checks.

## Judging access

From the repository root, this read-only check makes no inference call or hosting
change:

```powershell
node deployment/vercel/judging-check.mjs
```

An operator may supply the actual configured Unix deadline with
`--deadline-epoch 1796063340`. The existing November 30 admission cutoff is before
the published December judging window, so this configuration currently fails the
check. This is a coding-admission deadline, not a claim that the website shuts
down. A future date alone does not guarantee credits, capacity or sufficient
shared quotas. See [submission gates](../SUBMISSION_CHECKLIST.md) and the
[official rules](https://nebiusglobalaihackathon.devpost.com/rules).

Raw browser screenshots, provider reconciliation, task bundles and private owner
capabilities stay in ignored local artifacts/private configuration. Public
summaries do not include credentials; hashes identify retained evidence, not
digitally signed attestations.
