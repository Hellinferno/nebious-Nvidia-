"""Durable lifecycle tests (B-06): leases, CAS transitions, events, immutability, verdict authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from benchproof.constraints import contract_hash
from benchproof.domain import (
    Artifact,
    AuditRecord,
    CheckOutcome,
    CheckResult,
    GateVerdict,
    RunState,
)
from benchproof.storage import get_audit, migrate, save_audit
from benchproof.storage.lifecycle import (
    TRUSTED_EVALUATOR,
    ImmutableRecordError,
    VerdictAuthorityError,
    acquire_lease,
    append_event,
    lease_holder,
    list_events,
    migrate_lifecycle,
    record_artifact,
    record_check_result,
    record_verdict,
    release_lease,
    transition,
)

REQUIRED = {"a", "b"}


@pytest.fixture
def db(tmp_path: Path) -> Path:
    p = tmp_path / "lc.db"
    migrate(p)
    migrate_lifecycle(p)
    save_audit(
        AuditRecord(audit_id="audit-1", owner_ref="o", fixture_id="MC-01", source_hash="s" * 64, contract_hash=contract_hash()),
        p,
    )
    return p


def _res(cid: str, outcome: CheckOutcome) -> CheckResult:
    return CheckResult(check_id=cid, outcome=outcome, oracle_kind="deterministic", reason="t")


def test_one_lease_per_audit(db: Path) -> None:
    assert acquire_lease("audit-1", "w1", 60, db) is True
    assert acquire_lease("audit-1", "w2", 60, db) is False
    assert acquire_lease("audit-1", "w1", 60, db) is True  # renew
    assert lease_holder("audit-1", db)["worker_id"] == "w1"
    assert release_lease("audit-1", "w2", db) is False
    assert release_lease("audit-1", "w1", db) is True
    assert acquire_lease("audit-1", "w2", 60, db) is True


def test_expired_lease_can_be_taken_over(db: Path) -> None:
    assert acquire_lease("audit-1", "w1", ttl_s=-1, db_path=db) is True
    assert acquire_lease("audit-1", "w2", 60, db) is True


def test_cas_transition_rejects_stale_state(db: Path) -> None:
    assert transition("audit-1", {RunState.QUEUED}, RunState.PREPARING, db) is True
    assert transition("audit-1", {RunState.QUEUED}, RunState.PREPARING, db) is False  # already moved
    assert get_audit("audit-1", db)["run_state"] == "PREPARING"
    events = list_events("audit-1", db_path=db)
    assert [e["event_type"] for e in events] == ["state_changed"]
    assert events[0]["payload"]["to"] == "PREPARING"


def test_events_are_ordered_and_resumable(db: Path) -> None:
    seqs = [append_event("audit-1", f"e{i}", {"i": i}, db_path=db) for i in range(4)]
    assert seqs == [1, 2, 3, 4]
    assert [e["sequence"] for e in list_events("audit-1", after=2, db_path=db)] == [3, 4]


def test_only_trusted_evaluator_writes_check_results(db: Path) -> None:
    with pytest.raises(VerdictAuthorityError):
        record_check_result("audit-1", _res("a", CheckOutcome.PASS_), author="candidate", db_path=db)
    record_check_result("audit-1", _res("a", CheckOutcome.PASS_), author=TRUSTED_EVALUATOR, db_path=db)


def test_check_results_are_immutable(db: Path) -> None:
    record_check_result("audit-1", _res("a", CheckOutcome.FAIL), author=TRUSTED_EVALUATOR, db_path=db)
    with pytest.raises(ImmutableRecordError):
        record_check_result("audit-1", _res("a", CheckOutcome.PASS_), author=TRUSTED_EVALUATOR, db_path=db)
    import sqlite3

    conn = sqlite3.connect(db)
    with pytest.raises(sqlite3.IntegrityError):  # engine-level trigger, independent of app code
        conn.execute("UPDATE check_results SET outcome='PASS' WHERE check_id='a'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM check_results WHERE check_id='a'")
    conn.close()


def test_verdict_requires_matching_checks_and_trusted_author(db: Path) -> None:
    record_check_result("audit-1", _res("a", CheckOutcome.PASS_), author=TRUSTED_EVALUATOR, db_path=db)
    with pytest.raises(VerdictAuthorityError):
        record_verdict("audit-1", GateVerdict.VERIFIED, "candidate", REQUIRED, db_path=db)
    with pytest.raises(VerdictAuthorityError):  # 'b' missing -> cannot be VERIFIED
        record_verdict("audit-1", GateVerdict.VERIFIED, TRUSTED_EVALUATOR, REQUIRED, db_path=db)
    record_verdict("audit-1", GateVerdict.INCONCLUSIVE, TRUSTED_EVALUATOR, REQUIRED, db_path=db)
    assert get_audit("audit-1", db)["gate_verdict"] == "INCONCLUSIVE"
    with pytest.raises(ImmutableRecordError):
        record_verdict("audit-1", GateVerdict.INCONCLUSIVE, TRUSTED_EVALUATOR, REQUIRED, db_path=db)


def test_forged_pass_cannot_become_verified(db: Path) -> None:
    record_check_result("audit-1", _res("a", CheckOutcome.PASS_), author=TRUSTED_EVALUATOR, db_path=db)
    record_check_result("audit-1", _res("b", CheckOutcome.FAIL), author=TRUSTED_EVALUATOR, db_path=db)
    with pytest.raises(VerdictAuthorityError):
        record_verdict("audit-1", GateVerdict.VERIFIED, TRUSTED_EVALUATOR, REQUIRED, db_path=db)
    record_verdict("audit-1", GateVerdict.REJECTED, TRUSTED_EVALUATOR, REQUIRED, db_path=db)


def test_artifacts_are_insert_only(db: Path) -> None:
    art = Artifact(artifact_id="art-1", owner="o", audit_id="audit-1", relative_name="observations.json", sha256="x" * 64)
    record_artifact(art, db)
    with pytest.raises(ImmutableRecordError):
        record_artifact(art, db)
