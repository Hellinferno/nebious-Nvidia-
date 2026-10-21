# Customized live rehearsal — 21 October 2026

Later the same day, a separate public feature/no-change batch and an explicitly
approved bounded feature follow-up were run. The clean control stopped unchanged,
but both feature runs failed safely. Their [separate complete records](verification/README.md)
do not overwrite this successful bugfix or justify an all-workflows-pass claim.

## Scope

One genuine end-to-end public sample completed at
[benchproof.vercel.app](https://benchproof.vercel.app). This is an integration
rehearsal with agent-assisted plan review under the owner's authorization, not a
human user study, held-out benchmark, comparative result or proof of every
requirement. Earlier failures and scripted evaluations remain separate evidence.

| Identity | Recorded value |
| --- | --- |
| Task | `coding-d6450f348202421a` |
| Project | `proj-207b4fdb89d8`, public StringCalculator sample |
| Runtime | `49337c3683310a7c137e898459dd38ab3927a2c3cd7cc3588e6523596127bcd3` |
| Deployment | `dpl_7SPDgfYC3M5HLPCThyCMWEPBRgi7` |
| Provider / model | Nebius Token Factory / `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| Base source | `7cc95afe1407d2b866d4a8cf8464c484107b25c929b905ef0a06f15f3fa55c0b` |
| Candidate source | `e6d6f0326e97d21023f239b225114959b804ade9a943dae525be8531758c9b50` |
| Approved plan | `97a04fd3adc6259d601fae8599f6388ab5447f9fc45680d02ab9dadffa974e05` |
| Skill / harness | `stable-python-interfaces` / `single-pass-v1` |
| Read-only MCP reference | `benchproof-docs`, `read_guide`, topic `workflow`, explicitly consented |
| Reference content hash | `ff6ad57605cbc555bcdedc9321ea1e07d09744767cd78eaf0d6d115aada56430` |
| Download SHA-256 | `99542f3e890fc15ad34b87ba72b656a4f4cd76b8ff4fc7fd87d8f5d68b8ef38d` |

The task required `add()` to raise `ValueError` for negatives, including
`negatives not allowed` and the negative values in its message, while preserving
empty/positive input behavior. Only `app/calculator.py` was editable; imported
`tests/test_calculator.py` remained unchanged.

## Outcome and browser evidence

- Real model-generated plan reviewed before approval; one genuine model edit,
  no canned replacement or inference retry.
- Baseline: two checks passed, the negative-number check failed. Candidate and
  fresh final execution: all three checks passed, none failed/skipped.
- Final state `REVIEW_READY`, not automatic user acceptance. Assurance is limited
  to the supplied project checks. Manual diff inspection confirms the negative
  collection/message and one-file scope, without executing candidate code locally.
- Three real isolated Docker executions; network denied, non-root user, read-only
  root/source, 256 MiB memory, one CPU, 64 pids and 30-second execution timeout.
- Original project fetched before/after and verified immutable. Desktop and
  390-pixel mobile layouts inspected; no overflow, browser errors or unexpected
  requests. ZIP downloaded, read without execution and matched to task/plan/diff.
- Reload preserved task state and counters: two model calls, one patch, three
  executions, 11.70 active seconds. Limits were two/one/three/300 seconds.

The first browser script incorrectly waited for `AWAITING_APPROVAL` while the UI
renders `AWAITING APPROVAL`. Planning had succeeded. Its timeout and screenshot
are retained; read-only reconciliation confirmed the completed call. A new browser
continued the same task, approved the reviewed plan and used only its one remaining
model call. Planning was not repeated; the test harness failure is not hidden.

## Usage and estimate, not billing

| Model action | Provider response | Prompt tokens | Completion tokens | Duration |
| --- | --- | --- | --- | --- |
| Plan | `chatcmpl-a1fb53e8-ad6c-4751-a737-d378fc1ecb80` | 1,154 | 688 | 4,129 ms |
| Edit | `chatcmpl-e5af5f54-f65e-44bf-835b-3a97a5e6a124` | 1,619 | 653 | 6,038 ms |
| Total | Exactly two calls, zero retries | 2,773 | 1,341 | Not end-to-end wall time |

Both returned `finish_reason=stop` with a 2,048-output-token allowance per call.
Total recorded usage: **4,114 tokens**. At the checked
[listed model rates](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
of $0.06 per million input and $0.24 per million output tokens, estimated inference
cost is **$0.00048822**. Actual billed charge and updated account balance remain
UNKNOWN; account-specific prices, taxes or other account activity are not measured.
The owner reported $59 and the intended judging reserve is $50, but the application
does not enforce a dollar balance/reserve. No further inference is part of this run.

## Retained local records

Private/generated artifacts stay Git-ignored; do not publish owner capabilities,
API credentials or raw private deployment configuration.

- `artifacts/release-live-20261020/rehearsal.json`: original browser timeout.
- `artifacts/release-live-20261020/review-approval.json`: explicit plan review.
- `artifacts/release-live-20261020/rehearsal-continuation.json`: passing continuation.
- `artifacts/release-live-20261020/recorded-model-usage.json`: read-only reconciliation.
- `artifacts/release-live-20261020/task-evidence-completed.json` and `task-bundle.zip`.
- `artifacts/coding/customization-20261017/same-task-live-continuation-1792588615820/`:
  desktop/mobile screenshots and network record.

Remaining gates: broader live evaluation with saved failures/denominators, user
sessions, owner review of the corrected final video, confirmed judging access/credits, final rights
review and owner submission. See [BUILD_PLAN.md](BUILD_PLAN.md).
