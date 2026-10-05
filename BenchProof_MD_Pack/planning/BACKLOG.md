# Implementation backlog

Research-aligned v2. All tickets start TODO until actual evidence is recorded. Dependencies, outputs and cut lines below replace the active ML-audit work. Detailed behavior is in [runtime](../docs/25_ASSURANCE_RUNTIME.md); work dates are in [daily tasks](DAILY_TASKS.md).

## Board rules

Status is TODO / IN_PROGRESS / BLOCKED / DONE. DONE requires acceptance artifacts and a tested commit, not a written specification. Complete the earliest unmet P0 dependency; P1 and P2 cannot consume release buffer. Mixed-priority tickets retain their stated P0 minimum even if their richer feature is cut.

## B-01 — Event and account readiness · P0

**Owner:** Ravi. **Dependencies:** None. **Target:** 4 Oct. **Status:** IN_PROGRESS (registration confirmed 4 Oct; Nebius account and key present 5 Oct; credits/expiry/billing not yet recorded; sandbox access not requested).

**Work:** Review this event eligibility/registration; record actual inference/runner access, credits, expiry and billing controls. Keep account facts separate from offered resources.

**Acceptance/evidence:** Access and eligibility checklist has actual owner confirmations; no assumed grants or beta access. Save sanitized account/access record and unresolved blockers.

**Scope/cut line:** Never replace required eligibility/access facts with assumptions.

## B-02 — Source scaffold and configuration · P0

**Owner:** Ravi. **Dependencies:** B-01 account facts; docs can scaffold independently. **Target:** 4 Oct. **Status:** DONE 4 Oct (locked install, health/ready/worker heartbeat, explicit live-mode refusal; see progress log).

**Work:** Create installable Python package, React/TypeScript UI, locked dependencies, .env.example and safe ignore rules. Add domain/API/state/evaluator module boundaries from repository structure.

**Acceptance/evidence:** Locked install and health/worker startup work; missing live credentials fail explicitly instead of silently switching to mock. Save tested versions/commit.

**Scope/cut line:** Use one worker/store; defer infrastructure abstractions.

## B-03 — Executable constraints and development fixtures · P0

**Owner:** Ravi. **Dependencies:** B-02. **Target:** 4–6 Oct. **Status:** DONE 5 Oct for the P0 minimum (AC/MC/CI/ID/clean validated in-process and through the Docker runner; relaxed/unknown/incomplete manifests → CONTRACT_UNAPPROVED; missing oracle → REQUIRED_CHECK_MISSING; trusted assets verified absent from candidate snapshots). Shallow-candidate case deferred to the gate suite in B-18.

**Work:** Implement five visible development cases and original synthetic inputs; pin approved C-API/C-AMOUNT/C-CALLER/C-IDEMPOTENCY/C-INTEGRITY mappings. Write external trusted oracle and reference repairs.

**Acceptance/evidence:** Faulty cases fail intended checks, reference repairs pass, clean passes untouched. Unapproved/missing required check is blocked; hidden truth absent from candidate.

**Scope/cut line:** AC/MC/clean first; CI/ID can stay P1.

## B-04 — Real NVIDIA inference adapter · P0

**Owner:** Ravi. **Dependencies:** B-01/B-02. **Target:** 4–8 Oct. **Status:** IN_PROGRESS (5 Oct: real catalog + bounded inference + valid structured JSON proposal on `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, no credential leakage; model card/license, tool loop and repair-proposal behaviors remain).

**Work:** Discover actual model catalog; record model card/license. Validate structured constraint-linked actions, repair proposal, usage, timeouts and format rejection behind a narrow adapter.

**Acceptance/evidence:** Real call returns known NVIDIA model metadata; five preflight behaviors recorded; no credential leakage. A useful live action is traceable to the call.

**Scope/cut line:** One tested model; extra tiers/providers P2.

## B-05 — Isolated runner and protected transport · P0

**Owner:** Ravi. **Dependencies:** B-01/B-02. **Target:** 5–6 Oct. **Status:** IN_PROGRESS (5 Oct: Sandboxes token accepted but no spawn/list permission → BLOCKED pending the beta access request; local Docker runner tested as the development alternate, D-024: fresh snapshot, network none, read-only, env cleared, timeout kill, judged outside).

**Work:** Map tested SDK calls to prepare/run/cancel/artifacts; pin image, keep launcher outside editable app source. Verify fresh state, network/resource controls and remote-operation lifecycle.

**Acceptance/evidence:** Bounded real command/input-output run with IDs/artifacts; oracle absent from candidate; timeout/network/cleanup observed. Decide tested alternate if beta access fails.

**Scope/cut line:** Mocks enable development only; isolation cannot be dropped.

## B-06 — Typed records, jobs and events · P0

**Owner:** Ravi. **Dependencies:** B-02/B-03. **Target:** 6 Oct. **Status:** IN_PROGRESS (5 Oct: leases, CAS transitions, ordered resumable events + SSE, idempotent POST, immutable check results/artifacts, evaluator-only verdicts; owner-mismatch denial pending B-13; worker lease processing pending Day 4).

**Work:** Implement strict v2 domain schemas, SQLite ownership/leases/transitions, action budgets and resumable SSE. Persist remote IDs and reservations before follow-up work.

**Acceptance/evidence:** One lease per run, no duplicate POST action, restored snapshot agrees with events. Candidate records cannot write verdicts; owner mismatch denied.

**Scope/cut line:** Single-instance durable store; defer distributed scheduling.

## B-07 — Immutable intake, state graph and baseline · P0

**Owner:** Ravi. **Dependencies:** B-03/B-05/B-06. **Target:** 7 Oct. **Status:** TODO.

**Work:** Hash approved source, parse supported AST forms, add reviewed typed manifest edges and coverage issues. Run visible baseline in isolation and map source changes to nodes.

**Acceptance/evidence:** Declared route/helper/worker links resolve; unknown dynamic edge is visible; stale source blocked. Graph hash and baseline artifact saved.

**Scope/cut line:** AST/SQLite and compact list; graph database/visual polish optional.

## B-08 — Impact, current context and bounded planner · P0

**Owner:** Ravi. **Dependencies:** B-04/B-07. **Target:** 8 Oct. **Status:** TODO.

**Work:** Reverse-traverse changed callers/contracts/checks; apply deterministic risk reasons; build bounded hash-linked context. NVIDIA proposes at most two falsifiable hypotheses and named probes.

**Acceptance/evidence:** Probe returns relevant evidence; selected checks include mandatory integrity; missing critical mapping blocks. Delayed stale action cannot apply.

**Scope/cut line:** No universal graph or calibrated risk probability.

## B-09 — Restricted patch authoring/import · P0

**Owner:** Ravi. **Dependencies:** B-08. **Target:** 9 Oct. **Status:** TODO.

**Work:** Implement provider-neutral diff record and validated patch proposal. Enforce base hash, app-path allowlist, line/byte ceilings and protected-file/mode restrictions.

**Acceptance/evidence:** Useful AC/MC diff applies to intended source; protected/wrong-base/oversized patch rejected before code execution. Save original/candidate hashes.

**Scope/cut line:** External product adapters P2; neutral schema stays.

## B-10 — Fresh independent acceptance gate · P0

**Owner:** Ravi. **Dependencies:** B-03/B-05/B-09. **Target:** 9 Oct. **Status:** TODO.

**Work:** Execute approved candidate fresh; trusted evaluator computes expected behavior externally and stores check/verdict. Required failure/unknown/missing result cannot pass.

**Acceptance/evidence:** Two distinct repair families pass; shallow invalid candidate rejected; clean untouched passes; forged PASS/protected edit rejected. Save check artifacts.

**Scope/cut line:** Acceptance authority and required-check integrity never cut.

## B-11 — Bundle export and independent replay · P0

**Owner:** Ravi. **Dependencies:** B-10. **Target:** 10 Oct. **Status:** TODO.

**Work:** Export canonical version/hash manifest, constraints, graph/gaps, decisions/actions, diff, results and REPLAY guide with safe paths/ownership and omissions.

**Acceptance/evidence:** Fresh isolated replay matches stated checks; tampered artifact fails nonexecuting validation; secrets/truth excluded. Preserve bundle/replay record.

**Scope/cut line:** Readable static report first; decorative export formatting optional.

## B-12 — Integrated developer-facing UI · P0

**Owner:** Ravi. **Dependencies:** B-06/B-10/B-11. **Target:** 11 Oct. **Status:** TODO.

**Work:** Connect curated examples, constraint review, impact, events, diff/verify, separate verdict/test strength and export to actual API records.

**Acceptance/evidence:** Faulty/clean/rejected paths work from browser with readable failure and next action; no hardcoded success or arbitrary public intake.

**Scope/cut line:** Affected-path list before interactive graph.

## B-13 — Errors, reconnect, ownership and accessibility · P0

**Owner:** Ravi. **Dependencies:** B-12. **Target:** 12 Oct. **Status:** TODO.

**Work:** Restore audits after reload, resume SSE, handle provider/timeout/budget/cancel states and safe artifact access. Check keyboard/mobile core path.

**Acceptance/evidence:** Reconnect causes no duplicate spend; pending cancel reconciles; cross-owner routes denied; unknown check stays explicit.

**Scope/cut line:** Keep core navigation/readability; optional animation cuts first.

## B-14 — Decision ledger and dependency freshness · P1; source-hash guard P0

**Owner:** Ravi. **Dependencies:** B-07/B-08. **Target:** 13 Oct. **Status:** TODO.

**Work:** Record reviewed/proposed decisions with dependencies/evidence/revisit triggers. Invalidate changed/deleted hashes, exclude stale decisions and rebuild context.

**Acceptance/evidence:** Relevant change marks stale; unrelated control remains current; late proposal rejected. Save F6-ready development transitions.

**Scope/cut line:** If cut, retain P0 source/contract hash freshness and state that rich ledger is absent.

## B-15 — Trajectory stopping and one recovery · P1; hard stop/caps P0

**Owner:** Ravi. **Dependencies:** B-06/B-08. **Target:** 14 Oct. **Status:** TODO.

**Work:** Canonicalize action/failure fingerprints; detect two no-progress repeats. Preserve improving controls; add one fresh-context changed-strategy recovery within original limits.

**Acceptance/evidence:** Stall stops, progress does not; second stall ends blocked; counters never reset. Save synthetic trace labels separately from actual recovery runs.

**Scope/cut line:** Simple stopping P0; rich replan optional P1.

## B-16 — Trusted mutation test-strength probes · P1

**Owner:** Ravi. **Dependencies:** B-10; stable P0. **Target:** 15 Oct. **Status:** TODO.

**Work:** Author semantic templates with external oracles, validate behavior changes, run max three relevant fresh branches and store killed/survived/invalid/unknown results.

**Acceptance/evidence:** Weak check set exposes survivor; invalid syntax is not killed; candidate remains unchanged. Strength/policy explicit and execution budgets respected.

**Scope/cut line:** If cut, NOT_RUN with no adequacy claim.

## B-17 — Integrity and execution hardening · P0

**Owner:** Ravi. **Dependencies:** B-09/B-10/B-13. **Target:** 16 Oct. **Status:** TODO.

**Work:** Run prompt-injection, protected-edit, fake-PASS, stale-graph, secret, traversal/ownership and actual network/resource/termination negatives.

**Acceptance/evidence:** Every exposed trust control has tested evidence; failing capability blocked/narrowed. Save sanitized test report and remediation.

**Scope/cut line:** Never substitute documentation for backend enforcement.

## B-18 — Freeze evaluation assets and scope · P0 reduced; P1 full

**Owner:** Ravi. **Dependencies:** B-03/B-10/B-17. **Target:** 17 Oct. **Status:** TODO.

**Work:** Validate and freeze R12/V12/G8/F6/W8/M12 assets or explicit R6/V6 subset, reference repairs, private truth and manifests. Choose based on implemented scope/budget.

**Acceptance/evidence:** Original/reference/clean semantics validated; unique hashes; no truth leakage. Save suite commit and chosen counts before final runs.

**Scope/cut line:** No hidden denominator changes or post-result fixture replacement.

## B-19 — Fair baseline harness and configuration freeze · P0 reduced; P1 full

**Owner:** Ravi. **Dependencies:** B-18/B-04/B-10. **Target:** 20 Oct. **Status:** TODO.

**Work:** Implement B0 smoke, B1 same agent minus assurance and B2, shared final evaluator and immutable trial/summary records. Freeze model/prompts/thresholds/image/budgets.

**Acceptance/evidence:** Small manual record counts match script; information/limits fair; setup/version/price snapshot saved. Failures remain assigned.

**Scope/cut line:** Optional component ablation/external products cut before core measurement.

## B-20 — Hosted product, persistence and recovery · P0

**Owner:** Ravi. **Dependencies:** B-11/B-13/B-17. **Target:** 19 Oct. **Status:** TODO.

**Work:** Deploy exact working build with HTTPS, supervised worker, durable data, public curated mode, quotas and server secrets. Restore backup in separate location.

**Acceptance/evidence:** Incognito faulty/clean/rejected/export journeys pass; restart/reconcile and restore tested; access lifetime/credits documented.

**Scope/cut line:** No ephemeral-store assumption; choose tested host.

## B-21 — Frozen trials, separated analysis and replay · P0 reduced; P1 full

**Owner:** Ravi. **Dependencies:** B-19/B-20. **Target:** 21–23 Oct. **Status:** TODO.

**Work:** Run all assigned B0/B1/B2 trials and selected assurance suites, preserve failures/usage, inspect accepted diffs and replay preselected exports.

**Acceptance/evidence:** Actual counts/denominators link to immutable records; limitations and null results retained; evaluated/deployed versions reconciled.

**Scope/cut line:** Report explicit reduced scope rather than invent missing measurements.

## B-22 — User observation and product fixes · P1; critical UX fixes P0

**Owner:** Ravi. **Dependencies:** B-12. **Target:** 18/23 Oct. **Status:** TODO.

**Work:** Observe voluntary task sessions if available; record consent/confusion/completion without coaching. Fix the highest-value core decision/readability issue.

**Acceptance/evidence:** Actual session count and change evidence; no fabricated user study or unsolicited messages. Core journey understandable.

**Scope/cut line:** Self-review disclosed if volunteers unavailable.

## B-23 — Clean-clone release, license and docs · P0

**Owner:** Ravi. **Dependencies:** B-17/B-20/B-21. **Target:** 24–25 Oct. **Status:** TODO.

**Work:** Add actual LICENSE/notices, tested setup, accurate judge guide and results/limits. Clean clone the release, run appropriate checks and tag feature freeze.

**Acceptance/evidence:** Setup/replay/access work from final docs; claims match implementation; terms/inventory complete; three live rehearsals recorded.

**Scope/cut line:** After freeze only necessary fixes; functional ones need affected reruns.

## B-24 — Genuine short demo video · P0

**Owner:** Ravi. **Dependencies:** B-23. **Target:** 26 Oct. **Status:** TODO.

**Work:** Record real constraint/impact/rejection/repair/gate/export footage; disclose cuts/replay, caption and remove secrets/unsupported numbers.

**Acceptance/evidence:** Public video below three minutes with incognito playback and genuine run IDs; file/link retained.

**Scope/cut line:** Omit extra P1 screens before hiding the complete loop.

## B-25 — Final feedback and entry materials · P0

**Owner:** Ravi. **Dependencies:** B-21/B-23/B-24. **Target:** 27 Oct. **Status:** TODO.

**Work:** Write actual Nebius/NVIDIA observations; finalize entry from measured scope, fill required links/testing instructions and recheck live rules/form.

**Acceptance/evidence:** No achievement placeholders or unmeasured product rankings; all required fields and public links reviewed.

**Scope/cut line:** Future features remain explicitly future work.

## B-26 — Submission and access preservation · P0

**Owner:** Ravi. **Dependencies:** B-25. **Target:** 28 Oct 20:00 IST; buffers 29–30 Oct. **Status:** TODO.

**Work:** Ravi completes actual entry action, verifies submitted status, retains confirmation and keeps the tested version accessible through judging.

**Acceptance/evidence:** Submitted status/time/URL and incognito links saved; credit/host reserve and post-submit monitoring plan established.

**Scope/cut line:** A draft is not submitted; no silent replacement of submitted behavior.

## B-27 — Optional adapters, ablations and broader cases · P2

**Owner:** Ravi. **Dependencies:** All P0 complete; time/credits remain. **Target:** Only before freeze. **Status:** TODO.

**Work:** Consider one accessible external-agent adapter/trial, graph ablation, second NVIDIA tier or permissioned case. Use research benchmark protocol and rights checks.

**Acceptance/evidence:** Configured versions/access, fair trials and actual evidence; unrun tools stay NOT_RUN. Optional work does not delay release.

**Scope/cut line:** Cut all of this before any P0 or submission buffer.

## Daily board entry

| Ticket | Status | Commit | Acceptance artifact | Blocker/next action |
| --- | --- | --- | --- | --- |
| [ID] | TODO | None | None | Earliest unmet dependency |

When a scope decision changes a ticket, update its acceptance and linked docs rather than checking off a removed requirement. Record NOT_RUN/unsupported for omitted benchmark/features. Keep superseded decisions and failed attempts inspectable.
