# Architecture decisions and open choices

Research revision 3 October 2026. Accepted means selected for implementation, not already built. Evidence and actual status belong in [progress](PROGRESS_LOG.md).

## Retained decisions

| ID | Decision | Reason / revisit condition |
| --- | --- | --- |
| D-001 | BenchProof; Coding and Agentic Engineering track | Preserve project identity and research-directed fit; revisit on explicit change |
| D-003 | React/TypeScript/Vite, FastAPI durable worker | Simple usable product; revise for observed host mismatch |
| D-004 | Meaningful runtime NVIDIA inference on Nebius | Required planned provider path; resolve actual model/access |
| D-005 | Prefer Nebius Sandboxes behind adapter | Isolated execution; test alternate if access absent by 6 Oct |
| D-006 | Protected independent deterministic acceptance | Candidate cannot control its success; never remove for schedule pressure |
| D-007 | Curated public examples only | Bounded useful reviewer access; broader intake needs separate review |
| D-009 | Original synthetic fixture inputs | Reproducible rights and no private invoice data |
| D-010 | Single-instance SQLite plus durable artifacts | Small graph/record workload; revisit actual storage/scale limits |
| D-011 | Freeze 25 Oct; internal submit 28 Oct 20:00 IST | Protect release and form/access buffer; official changes govern |
| D-012 | No guaranteed-win/universal-proof claim | Evidence supports declared version/scope only |

## Superseded decisions

| ID | Previous scope | Replacement | Migration effect |
| --- | --- | --- | --- |
| D-002 | Python/scikit-learn tabular ML audit | D-013 assurance runtime on Python service | Retire ML data/split/label machinery from active build |
| D-008 | Target/metric leakage P0, group/replay faults P1 | D-014 engineering repair families | Rewrite cases, prompts, check contracts and claims; no measured result carries over |

The initial design had no completed implementation or benchmark to migrate. Independent verification, provenance and replay principles are retained. ML audit can be a later vertical, outside current release commitments.

## Research-aligned decisions

| ID | Accepted planning choice | Evidence/revisit condition |
| --- | --- | --- |
| D-013 | Agentic Engineering Assurance Runtime as product | Recovered latest research; validate working user decision and baselines |
| D-014 | P0 API/amount; P1 caller/idempotency repair families | Synthetic precise contracts; expand only after complete P0 |
| D-015 | AST/manifest typed graph in SQLite; provenance and gaps explicit | Aider/source research shows graph alone is familiar; no claim of universal impact |
| D-016 | Human-owned pinned executable constraints with external trusted oracle | Negative gate tests must establish protection before public use |
| D-017 | Hash-bound context; P1 decision dependency invalidation | F6 and delayed-proposal tests; never silently reuse stale state |
| D-018 | Ordinal risk with deterministic reasons | No calibrated probability; revise rules from development evidence before freeze |
| D-019 | Two repeated no-progress fingerprints stop; one P1 recovery | Validate W8 controls; original limits never reset |
| D-020 | P1 trusted pre-authored mutants, max three per live verification | Separate strength metric; omit with NOT_RUN if budget lacks room |
| D-021 | Provider-neutral diff/trace records; eight product integrations optional | Desk research is not API integration or performance ranking |
| D-022 | R12/V12/G8/F6/W8/M12 separated; explicit R6/V6 fallback | Freeze chosen scope and denominator before final runs |
| D-023 | Primary comparison same NVIDIA agent with/without assurance | Shared final evaluator and hard budgets; component claims need ablation |

## Open implementation choices

| ID | Choice | Evidence needed | Target |
| --- | --- | --- | --- |
| O-001 | Exact NVIDIA model and parameters | Actual catalog/card/license, five development preflight behaviors, usage | 4–8 Oct |
| O-002 | Contree auth/SDK/lifecycle and limits | Real image/command/fresh state/artifact/cancel observations | 5–6 Oct |
| O-003 | Tested alternate runner if needed | Resolved for development 5 Oct by D-024 (local Docker runner); hosted execution route still Sandboxes pending access | 6 Oct |
| O-004 | App host/persistence/lifetime | Proposal 5 Oct, untested: one Linux VM with Docker, persistent disk for SQLite/artifacts, HTTPS reverse proxy; decide after runner access is known | Select 6 Oct; deploy 19 Oct |
| O-005 | Actual usage/cost ceilings | Dated prices/grants/expiry and measured upper bounds | 6 Oct; finalize 20 Oct |
| O-006 | Supported graph forms and mappings | Fixture AST coverage, unknown-edge tests and reviewed manifest | 7–8 Oct |
| O-007 | Final suite/scope and fingerprint normalization | P0/P1 evidence, controls and budget forecast | Suite 17 Oct; configuration 20 Oct |
| O-008 | License/model/image/asset inventory | Actual component terms and top-level LICENSE | 25 Oct |
| O-009 | Mutation adequacy required or optional per release contract | Valid templates, survivor behavior, overhead and explicit accepted policy | 15–20 Oct |
| O-010 | Optional external-agent tools/configuration | Real access/versions/terms and remaining time | P2 only |

## Decisions recorded during implementation

### D-024 — Local Docker runner as the tested development alternate to Nebius Sandboxes

- Date, owner, status: 5 October 2026, Ravi, accepted for development; hosted route remains open.
- Trigger and observed evidence: Sandboxes `GET /whoami` returned 200 with every permission `false` and `/images` returned 403 (`artifacts/runner/runner_20261005T181249.json`). Docker Desktop 29.7.2 (linux engine) available locally. Contract `6d5b95ce…`; no graph yet.
- Constraints and options investigated: (a) wait for Sandboxes beta access — blocks all execution work; (b) run candidates in-process — violates the protected boundary; (c) local Docker container with network none, read-only root, cleared env, resource caps, timeout kill — selected.
- Selected option, rationale and artifacts: (c). Candidate image `benchproof-candidate:dev@sha256:104ce828…` from `python@sha256:02108f5d…`; launcher `backend/runner/launcher/observe_invoice.py` mounted read-only outside `app/`; trusted oracle judges `observations.json` on the host. Evidence: clean VERIFIED, MC-01 REJECTED, timeout negative killed, isolation probes all denied.
- Cost, security, user, schedule and coverage effects: no provider cost; shared-kernel isolation only (not VM); unblocks Days 3–10 development; the final hosted story still needs Sandboxes or an isolated VM route per doc 07 — a local container is not accepted as the hosted route merely because it starts.
- Dependency hashes, affected documents/contracts and revisit condition: image digest above; docs 07/09, backlog B-05, O-003/O-004. Revisit when Sandboxes `spawn` permission is granted or by the 6 Oct fallback review.
- Superseded ID: none.

## Decision entry template

### D-[number] — title

- Date, owner, status: proposed / accepted / superseded.
- Trigger and observed evidence; source/contract/graph versions.
- Constraints and options actually investigated.
- Selected option, rationale and prototype/check artifacts.
- Cost, security, user, schedule and coverage effects.
- Dependency hashes, affected documents/contracts and revisit condition.
- Superseded ID and new version where applicable.

A proposed fallback/model/check remains proposed until tested. A model-authored decision cannot approve its own policy change. Keep historical decisions and invalidation reasons; do not rewrite them to imply the latest release was always the plan.
