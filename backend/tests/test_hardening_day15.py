"""Day 15 hardening pass: launcher child isolation and record reconciliation, worker-caller-path v2,
line-ending independent hashes, strict fixture ids, patch application edge cases, atomic lifecycle
writes, verification attempts, guarded state writes and budget give-back."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from benchproof.constraints import contract_hash
from benchproof.decisions import create_decision, refresh_decisions
from benchproof.domain import (
    AuditRecord,
    CheckOutcome,
    CheckResult,
    DecisionReviewStatus,
    GateVerdict,
    RunState,
)
from benchproof.evaluator.harness import collect_observations_in_process, judge
from benchproof.evaluator.observations import (
    WORKER_CALLER_PATH_VERSION,
    _worker_path,
    evaluate_observations,
    worker_delegates_to_process_invoice,
)
from benchproof.execution import prepare_snapshot
from benchproof.execution.docker_runner import _last_record, reconcile_records
from benchproof.fixtures import canonical_source_bytes, fixture_dir, source_hash_for_dir
from benchproof.gate import execute_acceptance_gate
from benchproof.intake import inspect_source_tree
from benchproof.mutations import MutationError, run_mutation_assessment
from benchproof.patch import (
    PatchProposal,
    apply_patch_to_dir,
    apply_patch_to_file,
    get_canonical_mc01_repair_diff,
)
from benchproof.storage import (
    get_audit,
    get_decision,
    get_patch,
    migrate,
    save_audit,
    save_patch,
    update_audit_state,
)
from benchproof.storage.lifecycle import (
    TRUSTED_EVALUATOR,
    IdempotencyConflict,
    ImmutableRecordError,
    VerdictAuthorityError,
    create_audit_idempotent,
    latest_check_attempt,
    list_check_results,
    list_events,
    migrate_lifecycle,
    next_check_attempt,
    record_check_results,
    request_cancellation,
    transition,
)
from benchproof.suites import sha256_file, tree_hash
from benchproof.trajectory import budget_snapshot

BACKEND = Path(__file__).resolve().parents[1]
LAUNCHER = BACKEND / "runner" / "launcher" / "observe_invoice.py"
CLEAN = fixture_dir("clean-service") / "app"

LIVE_WORKER = (
    "from services import process_invoice\n\n"
    "def handle_invoice_job(tenant_id, request_id, lines):\n"
    "    return process_invoice(tenant_id, request_id, lines)\n"
)
DEAD_CODE_WORKER = (
    "from services import process_invoice\n\n"
    "def handle_invoice_job(tenant_id, request_id, lines):\n"
    "    if False:\n"
    "        process_invoice(tenant_id, request_id, lines)\n"
    "    while 0:\n"
    "        process_invoice(tenant_id, request_id, lines)\n"
    "    return None\n"
)
MODULE_LEVEL_WORKER = (
    "from services import process_invoice\n"
    "process_invoice('t', 'r', [])\n\n"
    "def handle_invoice_job(tenant_id, request_id, lines):\n"
    "    return None\n"
)
NO_IMPORT_WORKER = (
    "def handle_invoice_job(tenant_id, request_id, lines):\n"
    "    return process_invoice(tenant_id, request_id, lines)\n"
)


def _db(tmp_path: Path, name: str = "day15.db") -> Path:
    path = tmp_path / name
    migrate(path)
    migrate_lifecycle(path)
    return path


def _mc01_audit(db: Path, audit_id: str = "audit-gate") -> AuditRecord:
    record = AuditRecord(
        audit_id=audit_id,
        owner_ref="owner-1",
        fixture_id="MC-01",
        source_hash=source_hash_for_dir(fixture_dir("MC-01") / "app"),
        contract_hash=contract_hash(),
    )
    save_audit(record, db)
    return record


def _res(check_id: str, outcome: CheckOutcome) -> CheckResult:
    return CheckResult(check_id=check_id, outcome=outcome, oracle_kind="deterministic", reason="t")


def _receipt(total: str = "0.01", receipt_id: str = "rcpt-1") -> dict:
    return {"stored_receipt": {"response": {"receipt_id": receipt_id, "total_amount": total}}, "error": None}


# ── Launcher: parent/child split and stdout-versus-file reconciliation ──────────

def test_launcher_parent_record_equals_file_and_child_is_isolated() -> None:
    """Development-only run of the launcher on this machine (the container path is identical)."""
    snapshot = prepare_snapshot(CLEAN)
    try:
        proc = subprocess.run(
            [sys.executable, str(LAUNCHER), "--candidate", str(snapshot.candidate_dir), "--out", str(snapshot.out_dir)],
            capture_output=True, text=True, timeout=180, check=False,
        )
        assert proc.returncode == 0, proc.stderr[-800:]
        file_record = json.loads((snapshot.out_dir / "observations.json").read_text(encoding="utf-8"))
        stdout_record = _last_record(proc.stdout)
        assert stdout_record == file_record
        assert file_record["environment"]["launcher_isolation"] == "child-process"
        assert file_record["child"]["exit_code"] == 0 and file_record["child"]["timed_out"] is False
        assert {"stored_receipt", "repeat", "conflict"} <= set(file_record["worker"])
        accepted, error = reconcile_records(file_record, stdout_record)
        assert accepted == file_record and error is None
        assert judge(accepted, snapshot.app_dir)["verdict"] == "VERIFIED"
    finally:
        snapshot.cleanup()


def test_reconciliation_rejects_file_only_and_altered_records() -> None:
    record = {"schema": "benchproof/observations-v1", "route": {}, "worker": {}, "error": None}
    assert reconcile_records(None, None) == (None, None)
    accepted, error = reconcile_records(record, None)
    assert accepted is None and "not trusted" in error
    altered = {**record, "route": {"first": {"status": 201}}}
    accepted, error = reconcile_records(altered, record)
    assert accepted is None and "tampering" in error
    assert reconcile_records(record, dict(record)) == (record, None)
    stdout = 'noise\n{"schema": "other"}\n' + json.dumps(record) + "\ntrailing text\n"
    assert _last_record(stdout) == record
    assert _last_record("no json here\n{not json") is None


# ── worker-caller-path v2: live static delegation AND observed worker idempotency ──

def test_static_delegation_ignores_dead_and_module_level_calls() -> None:
    assert worker_delegates_to_process_invoice(LIVE_WORKER) is True
    assert worker_delegates_to_process_invoice(DEAD_CODE_WORKER) is False
    assert worker_delegates_to_process_invoice(MODULE_LEVEL_WORKER) is False
    assert worker_delegates_to_process_invoice(NO_IMPORT_WORKER) is False


def test_worker_path_requires_observed_idempotency() -> None:
    assert WORKER_CALLER_PATH_VERSION == 2
    good = {**_receipt(), "repeat": _receipt(), "conflict": _receipt()}
    passed = _worker_path(LIVE_WORKER, good)
    assert passed.outcome == CheckOutcome.PASS_ and passed.check_version == 2

    replaced = {**_receipt(), "repeat": _receipt(receipt_id="rcpt-2"), "conflict": _receipt()}
    failed = _worker_path(LIVE_WORKER, replaced)
    assert failed.outcome == CheckOutcome.FAIL and "repeating" in failed.reason

    conflict_won = {**_receipt(), "repeat": _receipt(), "conflict": _receipt(total="3.00")}
    failed = _worker_path(LIVE_WORKER, conflict_won)
    assert failed.outcome == CheckOutcome.FAIL and "conflicting" in failed.reason

    unobserved = _worker_path(LIVE_WORKER, _receipt())
    assert unobserved.outcome == CheckOutcome.UNKNOWN and "not observed" in unobserved.reason

    dead = _worker_path(DEAD_CODE_WORKER, good)
    assert dead.outcome == CheckOutcome.FAIL and "no live call" in dead.reason
    assert _worker_path(None, good).outcome == CheckOutcome.UNKNOWN
    assert _worker_path("def broken(:\n", good).outcome == CheckOutcome.UNKNOWN


def test_in_process_harness_observes_worker_repeat_and_conflict() -> None:
    obs = collect_observations_in_process(CLEAN)
    assert {"repeat", "conflict"} <= set(obs["worker"])
    worker_source = (CLEAN / "worker.py").read_text(encoding="utf-8")
    results = evaluate_observations(obs, worker_source)
    check = next(r for r in results if r.check_id == "worker-caller-path")
    assert check.outcome == CheckOutcome.PASS_ and check.check_version == 2

    tampered = json.loads(json.dumps(obs))
    tampered["worker"]["repeat"]["stored_receipt"]["response"]["receipt_id"] = "another-receipt"
    check = next(r for r in evaluate_observations(tampered, worker_source) if r.check_id == "worker-caller-path")
    assert check.outcome == CheckOutcome.FAIL


# ── Hashes are line-ending independent; fixture ids are strict ───────────────────

def test_source_hashes_do_not_depend_on_the_checkout_line_endings(tmp_path: Path) -> None:
    lf = tmp_path / "lf" / "app"
    crlf = tmp_path / "crlf" / "app"
    for directory in (lf, crlf):
        directory.mkdir(parents=True)
    (lf / "m.py").write_bytes(b"x = 1\ny = 2\n")
    (crlf / "m.py").write_bytes(b"x = 1\r\ny = 2\r\n")
    assert canonical_source_bytes(crlf / "m.py") == b"x = 1\ny = 2\n"
    assert source_hash_for_dir(lf) == source_hash_for_dir(crlf)
    assert inspect_source_tree(lf)["source_hash"] == source_hash_for_dir(crlf)
    assert sha256_file(lf / "m.py") == sha256_file(crlf / "m.py")
    assert tree_hash(lf, (".py",)) == tree_hash(crlf, (".py",))
    (crlf / "m.py").write_bytes(b"x = 1\r\ny = 3\r\n")  # a real content change is still detected
    assert source_hash_for_dir(lf) != source_hash_for_dir(crlf)
    assert tree_hash(lf, (".py",)) != tree_hash(crlf, (".py",))


@pytest.mark.parametrize("bad", ["", "..", "a/b", "a\\b", "C:x", ".hidden", "MC-01/../AC-01", "x" * 65])
def test_fixture_dir_rejects_unsafe_ids(bad: str) -> None:
    with pytest.raises(ValueError, match="unsafe fixture id"):
        fixture_dir(bad)


def test_fixture_dir_accepts_plain_ids() -> None:
    assert fixture_dir("MC-01").name == "MC-01"


# ── Patch application: zero-length old ranges and CRLF inputs ───────────────────

def test_zero_length_old_range_inserts_after_the_named_line() -> None:
    original = "a\nb\nc\n"
    after_first = "--- a/app/x.py\n+++ b/app/x.py\n@@ -1,0 +2 @@\n+inserted\n"
    assert apply_patch_to_file(original, after_first) == "a\ninserted\nb\nc\n"
    at_top = "--- a/app/x.py\n+++ b/app/x.py\n@@ -0,0 +1 @@\n+first\n"
    assert apply_patch_to_file(original, at_top) == "first\na\nb\nc\n"


def test_crlf_source_and_diff_produce_lf_output() -> None:
    original = "a\r\nb\r\nc\r\n"
    diff = "--- a/app/x.py\r\n+++ b/app/x.py\r\n@@ -2 +2 @@\r\n-b\r\n+B\r\n"
    out = apply_patch_to_file(original, diff)
    assert out == "a\nB\nc\n" and "\r" not in out


def test_applied_files_are_written_with_lf_regardless_of_platform(tmp_path: Path) -> None:
    base = fixture_dir("MC-01") / "app"
    proposal = PatchProposal(
        patch_id="p-lf", audit_id="a-lf", base_source_hash=source_hash_for_dir(base),
        target_files=["app/money.py"], diff=get_canonical_mc01_repair_diff(),
    )
    dest, candidate_hash = apply_patch_to_dir(base, proposal, tmp_path / "app")
    assert b"\r\n" not in (dest / "money.py").read_bytes()
    assert candidate_hash == source_hash_for_dir(dest)


# ── Lifecycle: atomic batches, attempts, guarded writes, idempotent creation ─────

@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = _db(tmp_path)
    save_audit(
        AuditRecord(audit_id="audit-1", owner_ref="o", fixture_id="MC-01", source_hash="s" * 64, contract_hash=contract_hash()),
        path,
    )
    return path


def test_check_results_record_per_attempt_atomically(db: Path) -> None:
    assert next_check_attempt("audit-1", db) == 1
    record_check_results(
        "audit-1", [_res("a", CheckOutcome.PASS_), _res("b", CheckOutcome.FAIL)],
        author=TRUSTED_EVALUATOR, attempt=1, db_path=db,
    )
    with pytest.raises(ImmutableRecordError):  # a duplicate inside the batch stores nothing from it
        record_check_results(
            "audit-1", [_res("c", CheckOutcome.PASS_), _res("c", CheckOutcome.PASS_)],
            author=TRUSTED_EVALUATOR, attempt=2, db_path=db,
        )
    assert latest_check_attempt("audit-1", db) == 1
    assert list_check_results("audit-1", attempt=2, db_path=db) == []
    record_check_results("audit-1", [_res("a", CheckOutcome.FAIL)], author=TRUSTED_EVALUATOR, attempt=2, db_path=db)
    assert latest_check_attempt("audit-1", db) == 2
    latest = list_check_results("audit-1", db_path=db)
    assert [(r["attempt"], r["check_id"], r["outcome"]) for r in latest] == [(2, "a", "FAIL")]
    assert len(list_check_results("audit-1", attempt=1, db_path=db)) == 2
    with pytest.raises(VerdictAuthorityError):
        record_check_results("audit-1", [_res("z", CheckOutcome.PASS_)], author="candidate", attempt=3, db_path=db)


def test_transition_commits_state_and_event_together(db: Path) -> None:
    before = len(list_events("audit-1", db_path=db))
    assert transition("audit-1", {RunState.COMPLETED}, RunState.PREPARING, db) is False
    assert len(list_events("audit-1", db_path=db)) == before  # a rejected CAS leaves no event behind
    assert transition("audit-1", {RunState.QUEUED}, RunState.PREPARING, db) is True
    events = list_events("audit-1", db_path=db)
    assert events[-1]["event_type"] == "state_changed" and events[-1]["payload"]["to"] == "PREPARING"
    assert get_audit("audit-1", db)["run_state"] == "PREPARING"


def test_guarded_state_write_leaves_inactive_audits_alone(db: Path) -> None:
    assert update_audit_state("audit-1", RunState.INVESTIGATING, db_path=db, only_if_active=True) is True
    assert request_cancellation("audit-1", remote_reconciliation_required=False, db_path=db) == RunState.CANCELLED
    assert update_audit_state(
        "audit-1", RunState.COMPLETED, GateVerdict.VERIFIED, db_path=db, only_if_active=True
    ) is False
    row = get_audit("audit-1", db)
    assert row["run_state"] == "CANCELLED" and row["gate_verdict"] == "PENDING"


def test_idempotent_creation_is_atomic_and_replays(db: Path) -> None:
    endpoint = "POST /api/v1/audits"
    audit = AuditRecord(audit_id="audit-k", owner_ref="o", fixture_id="MC-01", source_hash="s" * 64, contract_hash=contract_hash())
    response = audit.model_dump(mode="json")
    first, replayed = create_audit_idempotent("o", endpoint, "key-1", "body-hash", audit, response, db)
    assert replayed is False and first == response
    assert get_audit("audit-k", db) is not None
    assert [e["event_type"] for e in list_events("audit-k", db_path=db)] == ["audit_created"]

    other = AuditRecord(audit_id="audit-k2", owner_ref="o", fixture_id="MC-01", source_hash="s" * 64, contract_hash=contract_hash())
    again, replayed = create_audit_idempotent("o", endpoint, "key-1", "body-hash", other, other.model_dump(mode="json"), db)
    assert replayed is True and again == response
    assert get_audit("audit-k2", db) is None  # the replay never wrote a second audit
    with pytest.raises(IdempotencyConflict):
        create_audit_idempotent("o", endpoint, "key-1", "other-body", other, other.model_dump(mode="json"), db)
    assert get_audit("audit-k2", db) is None


# ── Gate: attempts, patch policy authority, preserved state ─────────────────────

def test_reverification_records_a_new_attempt_and_the_gate_owns_patch_policy(tmp_path: Path) -> None:
    db = _db(tmp_path)
    record = _mc01_audit(db)
    first = execute_acceptance_gate(audit_id=record.audit_id, db_path=db)  # unpatched MC-01
    assert first["verdict"] == "REJECTED" and first["attempt"] == 1 and first["state_updated"] is True

    save_patch(
        patch_id="p-1", audit_id=record.audit_id, base_hash=record.source_hash, diff_hash="dh",
        diff_text=get_canonical_mc01_repair_diff(), approved_paths=["app/money.py"], changed_lines=6, db_path=db,
    )
    assert get_patch("p-1", db)["policy_result"] == "PENDING"
    second = execute_acceptance_gate(audit_id=record.audit_id, patch_id="p-1", db_path=db)
    assert second["verdict"] == "VERIFIED" and second["attempt"] == 2
    assert second["policy_result"] == "APPROVED" and get_patch("p-1", db)["policy_result"] == "APPROVED"

    assert latest_check_attempt(record.audit_id, db) == 2
    latest = list_check_results(record.audit_id, db_path=db)
    assert {r["attempt"] for r in latest} == {2} and {r["patch_id"] for r in latest} == {"p-1"}
    assert {r["patch_id"] for r in list_check_results(record.audit_id, attempt=1, db_path=db)} == {None}
    row = get_audit(record.audit_id, db)
    assert row["gate_verdict"] == "VERIFIED" and row["run_state"] == "COMPLETED"


def test_cancelled_audit_keeps_its_state_after_verification(tmp_path: Path) -> None:
    db = _db(tmp_path)
    record = _mc01_audit(db, "audit-cancelled")
    assert request_cancellation(record.audit_id, remote_reconciliation_required=False, db_path=db) == RunState.CANCELLED
    result = execute_acceptance_gate(audit_id=record.audit_id, db_path=db)
    assert result["verdict"] == "REJECTED" and result["state_updated"] is False
    row = get_audit(record.audit_id, db)
    assert row["run_state"] == "CANCELLED" and row["gate_verdict"] == "PENDING"
    assert len(list_check_results(record.audit_id, db_path=db)) == 7  # the evidence itself is preserved
    assert list_events(record.audit_id, db_path=db)[-1]["payload"]["state_updated"] is False


# ── Mutations: unspent reservations are returned ───────────────────────────────

def test_unverified_baseline_returns_the_unused_mutant_budget(tmp_path: Path) -> None:
    db = _db(tmp_path)
    record = _mc01_audit(db, "audit-mutation")
    with pytest.raises(MutationError) as exc:
        run_mutation_assessment(record.audit_id, max_mutants=3, db_path=db)
    assert exc.value.code == "CANDIDATE_NOT_VERIFIED"
    snapshot = budget_snapshot(record.audit_id, db)
    assert snapshot["used_executions"] == 1  # the spent baseline stays charged; three mutant slots are returned
    assert snapshot["max_executions"] == 11


# ── Decisions: superseding retires the prior record ────────────────────────────

def test_superseded_decision_leaves_context_and_stays_superseded(tmp_path: Path) -> None:
    db = _db(tmp_path)
    app_dir = tmp_path / "fixture" / "app"
    app_dir.mkdir(parents=True)
    (app_dir / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    save_audit(
        AuditRecord(audit_id="audit-d", owner_ref="o", fixture_id="fixture", source_hash=source_hash_for_dir(app_dir), contract_hash="contract-v1"),
        db,
    )
    shared = {
        "audit_id": "audit-d", "app_dir": app_dir, "owner": "o", "review_status": DecisionReviewStatus.REVIEWED,
        "current_contract_hash": "contract-v1", "dependency_paths": ["app/core.py"], "db_path": db,
    }
    first = create_decision(statement="Keep VALUE at 1.", **shared)
    second = create_decision(statement="Allow VALUE to change.", supersedes=first.decision_id, **shared)
    assert get_decision(first.decision_id, db)["status"] == "SUPERSEDED"
    ledger = refresh_decisions("audit-d", app_dir, "contract-v1", db)
    by_id = {d["decision_id"]: d for d in ledger["decisions"]}
    assert by_id[first.decision_id]["status"] == "SUPERSEDED"
    assert "Superseded by" in (by_id[first.decision_id]["stale_reason"] or "")
    assert ledger["current_decision_ids"] == [second.decision_id]
