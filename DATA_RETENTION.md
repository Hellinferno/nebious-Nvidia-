# Demo data retention and storage admission

BenchProof is a bounded public demo, not a private repository-hosting service.
Owner access uses a browser-generated bearer capability, not a verified account.
Do not upload credentials, personal data or sensitive source. Source selected for
a model plan/edit and pinned skills/reference text can be sent to Nebius; public
documentation MCP queries send only the explicitly consented arguments.

## Admission limits

New project creation checks these limits in the same SQLite write transaction:

- Ten projects per owner and 100 projects across all owners.
- 16 MiB combined serialized project-source and manifest payload across all owners.
  Encoded UTF-8 JSON bytes, including escaping, are counted, not just raw file sizes.
- Existing intake limits remain: 20 files, 24 KiB/file, 128 KiB raw/project and
  256 KiB encoded request body.

New project and task creation also checks the database plus current WAL size
against a 128 MiB admission ceiling, with an estimate for the incoming record,
and retains at least 128 MiB of free space on the database filesystem after that
estimate. A failed storage probe refuses admission. New tasks retain the existing
global 100-task limit. The deployed shared daily mutation/provider/execution
allowances remain separate and are not reset by using another owner capability.

These are admission safeguards, not a hard filesystem quota: existing tasks,
SQLite overhead, exports, backups and other processes can consume additional
space after admission. Operators must monitor capacity and stop new paid work
before exhausting it. Do not loosen candidate isolation or erase evidence to
recover capacity. The server's defaults are conservative limits, not user controls.

## Retention and deletion

- No automatic TTL or silent eviction is implemented. Data remains until explicit
  owner/operator deletion or the end of demo hosting; no indefinite hosting promise
  is made. If existing data exceeds a new limit, new admission stops; old records
  are not automatically removed.
- `DELETE /api/v1/projects/{project_id}` removes only the matching owner's project
  record and releases its project count/payload allowance. Other owners' records
  are unaffected. This is not full erasure of related task data.
- Task briefs, source snapshots, checkpoints, observations and exports are separate
  evidence. Deleting a project intentionally does not invalidate or erase an
  existing task's pinned source. There is no public task-purge endpoint in this
  release. Never represent project deletion as secure deletion of all copies.
- Private database/config backups and downloaded exports can retain prior data.
  SQLite deletion is not a secure physical overwrite. Lost browser capabilities
  are not recoverable through verified-account login in this demo.

Before any operator cleanup, export required evidence, make a WAL-consistent backup,
identify exact owner/project/task scope and retention requirements, obtain explicit
approval for deletion, and verify restoration separately. Historical evaluation
records must not be erased as routine cleanup. A production release needs a complete
account, retention schedule and end-to-end erasure workflow beyond these demo limits.
