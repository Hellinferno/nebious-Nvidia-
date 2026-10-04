# Execution isolation and integrity specification

The assurance runtime accepts untrusted code and diffs. Each control below requires actual backend verification before its capability is exposed. Protected checks must remain protected even if the model behaves badly.

## Trust zones

Browser and repository content are untrusted. The API validates requests and ownership. The worker holds provider credentials but never executes candidate code. Candidate runtimes contain only approved source, protected transport and bounded inputs. The trusted evaluator keeps expected behavior/check logic outside those runtimes. Artifact export is an owner-scoped trusted operation.

## Intake and public mode

Public v1 accepts only immutable curated fixture IDs and approved candidate presets. It exposes no arbitrary Git URL, uploads, shell text, callback URL, dependency list or notebook runner. Developer-mode snapshot/diff intake is for explicitly authorized source and remains within the same limits.

Validate source <=10 MB/100 text files and diff <=20 KB/200 changed lines. Reject traversal, absolute paths, encoded path tricks, symlinks/hardlinks, submodules, binaries, archive bombs and unexpected file modes. A repository-provided constraints file is a proposal until approved and pinned; never auto-trust its rules.

## Candidate runtime controls

- Disable network during candidate execution and verify denial; trusted dependency preparation happens before it.
- No provider secrets, instance metadata access, privileged containers, host mounts, Docker socket or package-manager credentials.
- Enforce CPU, 2 GB memory, 60-second execution, process/disk/output ceilings using backend mechanisms actually tested.
- Input/source manifests are fixed; writable output is scoped to one audit/attempt. Evaluate approved changes only in a fresh candidate filesystem.
- Use fixed launch templates with structured arguments. Do not splice model text into host shell commands.
- Cap stdout/stderr and scrub secrets before retention. Candidate claims of PASS remain untrusted output.
- Track remote operation IDs, poll with finite timeouts, reconcile unknown submissions and confirm cleanup.

The API and worker cannot rely on a Docker logo or a documented sandbox feature as proof of isolation. Record actual network, metadata, timeout, memory and termination observations. If the backend cannot enforce required isolation, public execution is blocked until a tested route exists.

## Patch and policy protection

Allow only the fixture's approved `app/` source paths. Reject edits to constraints, evaluator/tests/truth, transport/launcher, environment, dependency manifests, budget settings, security code or evidence manifests. Reject new executable entry points and unexpected file-mode changes.

Validate base source hash atomically before apply. Normalize a diff without invoking candidate code. Keep original and patched immutable manifests. Diff explanations cannot waive checks. Source or contract changes invalidate graph/context and any acceptance result that depended on them.

## Independent evaluator boundary

Hidden expected values and oracle/check implementation are not mounted into candidate files. The trusted evaluator supplies bounded test inputs through a protected transport and evaluates returned behavior outside candidate execution. Validate output schema/IDs, exit status and artifact association. A missing/truncated response is UNKNOWN, not PASS.

Each final check runs against the exact candidate hash and fresh environment. Candidate code can see inputs it receives; do not claim inputs themselves remain secret. Protection means it cannot rewrite expected answers, check policy or verdict storage. Pre-authored mutation templates and evaluation truth remain outside candidate control.

## Prompt injection and stale state

README instructions, source comments, generated diff and tool text cannot change tool allowlists, limits or accepted constraints. Test an embedded instruction to reveal secrets, disable C-IDEMPOTENCY or edit evaluator code; all must be rejected by deterministic controls.

Only CURRENT reviewed decisions enter a P1 context packet. Compare source/contract hashes before each action. A late provider response using old context cannot apply a patch. Trace-fingerprint normalization must not remove significant failure differences or treat fabricated observations as progress.

## Session, cost and artifact controls

Require owner authorization for run, patch, event, cancel and export routes. Use unguessable IDs plus actual ownership checks, secure cookie settings if applicable, exact CORS origins and CSRF protection for cookie-authenticated mutations. Rate-limit public runs; start with one active run per session and two globally until measured.

Reserve worst-case usage before paid actions. Retry and mutant runs count within original limits. Cancel at every boundary, show CANCEL_PENDING until remote termination is reconciled, and preserve partial evidence. Public exports omit hidden benchmark truth and secrets; archives contain normalized relative names only.

## Mandatory negative checks

| Attack/failure | Required result |
| --- | --- |
| Evaluator/contract/test edit | Diff rejected before execution |
| Wrong base/context hash | Stale action rejected; current state rebuilt |
| Fake PASS text/forged result object | Trusted check still computes failure; no VERIFIED |
| Unknown required check/dynamic dependency | Visible BLOCKED/INCONCLUSIVE under accepted scope |
| Cross-session access | Denied for events, patches, artifacts and replay |
| Network/metadata attempt | Denied and recorded by tested runner policy |
| Infinite loop/output flood/memory excess | Bounded termination and retained limit reason |
| Hidden-truth or secret export | Excluded; release scan fails if found |

Treat a failing protection check as a release blocker for that capability. Narrow public scope while resolving it; never hide the failure behind a successful fixture screenshot.
