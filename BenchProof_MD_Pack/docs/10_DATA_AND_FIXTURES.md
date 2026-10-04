# Synthetic service and fixture design

Replaces the earlier ML dataset/split plan. All cases and counts below are proposed until implemented, validated and frozen. Use original synthetic inputs and no private invoice/customer data.

## Common service

Build a small Python/FastAPI invoice-ingestion service with `routes`, `schemas`, `money`, `services`, `repository` and `worker` modules. The normal task receives tenant ID, request ID and line-amount strings; returns a receipt with stable required fields and a fixed two-decimal total. A worker/report path uses the same semantics.

Use Decimal constructed from strings, sum unrounded line amounts, then ROUND_HALF_UP once on the invoice total. Example: `0.005 + 0.005` returns `0.01`, whereas prematurely rounding each line would return `0.02`. This is an explicit synthetic task rule, not a claim about all real accounting systems.

Idempotency is tenant/request scoped. Repeating an identical payload returns the original receipt without double count. Same key/different payload returns the declared conflict response. Different tenants can reuse a request ID independently. A controlled two-request concurrency fixture checks only the declared local behavior; it does not prove distributed exactly-once processing.

## Three visibility boundaries

| Assets | Visibility | Use |
| --- | --- | --- |
| Development source/cases/reference repairs | Visible to builder and development prompts | Implement and tune |
| Frozen task intent and faulty/clean source | Agent receives approved source/contract context | Fair evaluation input |
| Frozen expected categories, protected oracle/check code, candidate truth and mutant validity | Trusted evaluator/assessor only during final measurement | Outcome scoring and gate integrity |

Do not mount hidden check files in candidate runtimes. Expected outputs are computed outside them. The service sees test inputs sent to it; distinguish that from protected expected answers.

## Development suite

`development-v2`: five visible cases, one each for API (AC), amount (MC), caller impact (CI), idempotency (ID), plus one clean service. Include known-good repairs and one shallow candidate that passes visible smoke tests but fails a protected check. These are demonstration/tuning cases, not held-out evidence.

## Frozen repair suite R12

`repair-r12-v1`: twelve unique cases, eight faulty and four clean, three agent trials per case. Faulty variants have one intended repair family with optional benign distractors. Avoid names that reveal the answer in agent-visible paths.

| IDs | Family | Defect and required behavior |
| --- | --- | --- |
| AC-01, AC-02 | API compatibility | Missing/renamed required field or incorrect error/status behavior; repair preserves declared public schema and examples |
| MC-01, MC-02 | Exact amount boundary | Premature item rounding or float conversion; repair follows pinned Decimal/round-on-total rule |
| CI-01, CI-02 | Cross-module caller impact | Shared-helper change or caller bypass breaks route/worker consistency; repair covers both declared entry paths |
| ID-01, ID-02 | Tenant-scoped idempotency | Duplicate double count, conflicting payload acceptance, tenant-key omission or controlled race variant; repair preserves accepted key/conflict behavior |
| CL-01–CL-04 | Clean controls | Correct variants with benign unusual code/structure; no unjustified accepted repair |

P0 fallback `repair-r6-v1`: AC-01/AC-02, MC-01/MC-02 and CL-01/CL-02. Six unique cases, four faulty/two clean, three trials each. Never report it as R12.

## Separate assurance suites

| Suite | Target count | Purpose; do not combine with repair denominator |
| --- | --- | --- |
| V12 `gate-v12-v1` | 12 fixed candidate patches: 8 invalid, 4 valid | Compare visible smoke acceptance with protected gate on identical candidates |
| G8 `graph-g8-v1` | 8 source-change tasks | Expected impacted entry points/contracts/checks under declared supported graph scope |
| F6 `freshness-f6-v1` | 6 state transitions: 3 stale, 3 fresh | Correct invalidation and avoidance of unnecessary invalidation |
| W8 `trajectory-w8-v1` | 8 traces: 4 true stalls, 4 legitimate progress | Classification/stopping; synthetic traces labeled; executed recovery recorded separately |
| M12 `mutants-m12-v1` | 12 trusted semantic mutants: 3 per repair family | Sensitivity of protected checks, mutant validity and survival |

P0 reduced gate V6 contains four invalid and two valid candidates from AC/MC. G8/F6/W8/M12 are P1 final evaluation goals except source-hash freshness and simple stall stopping, which remain P0 implementation checks. If omitted, report NOT_RUN; do not quietly change suite counts.

## Fixture authoring and freeze

For each case store opaque agent-visible ID, trusted category, source hash, approved constraints, graph manifest, input generator seed, reference repair hash, expected check properties, runner image and resource needs. Change code/control flow and input variants between development and held-out cases.

Original faulty source must fail the intended trusted check; reference repair passes all required checks; clean controls pass untouched. Validate that hidden truth is absent from model context and candidate filesystem. Validate every mutant is behavior-changing and syntactically executable before freezing.

Freeze suite assets on 17 October; freeze evaluated prompts/model/runtime configuration on 20 October. No tuning on final outcomes followed by an untouched-holdout claim. A harness defect requires versioned correction and affected reruns. If the outcomes guide tuning, label later measurements regression evaluation or obtain fresh variants.

## Release and external cases

After measurement, release enough first-party source, checks and manifest to reproduce published results. Preserve a private live evaluation copy only while needed; do not publish hidden truth early. Public hero cases may be known development examples and must be labeled as such.

A permissioned external repository is optional P2 and a separate case study. Record authorization, rights, commit, oracle review and coverage limits. It contributes no synthetic-suite trial to R12 unless a new protocol explicitly defines that change before measurement.
