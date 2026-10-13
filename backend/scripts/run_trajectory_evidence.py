"""Generate development-only W8 classification and executed recovery evidence."""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord
from benchproof.fixtures import source_hash
from benchproof.investigation import run_investigation
from benchproof.storage import get_audit, list_actions, migrate, save_audit
from benchproof.storage.lifecycle import list_events, migrate_lifecycle
from benchproof.trajectory import (
    FINGERPRINT_RULE_VERSION,
    RECOVERY_STRATEGY,
    STALL_REPEAT_THRESHOLD,
    classify_trace,
    reserve_recovery,
)
from benchproof.trajectory.development import FROZEN_AT, SUITE_ID, development_traces

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "artifacts" / "trajectory" / "w8_and_executed_recovery.json"


def main() -> int:
    classifications = []
    for trace in development_traces():
        result = classify_trace(trace["steps"])
        classifications.append(
            {
                "trace_id": trace["trace_id"],
                "human_label": trace["label"],
                "classification": result["classification"],
                "correct": result["classification"] == trace["label"],
                "source_reason": trace["reason"],
                "stall_index": result["stall_index"],
                "steps": [step.model_dump(mode="json") for step in trace["steps"]],
            }
        )

    with tempfile.TemporaryDirectory(prefix="benchproof-recovery-") as tmp:
        db = Path(tmp) / "recovery.db"
        migrate(db)
        migrate_lifecycle(db)
        audit_id = f"audit-recovery-{uuid.uuid4().hex[:8]}"
        save_audit(
            AuditRecord(
                audit_id=audit_id,
                owner_ref="evidence-owner",
                fixture_id="MC-01",
                source_hash=source_hash("MC-01"),
                contract_hash=contract_hash(),
                mode="mock",
                limits={
                    "max_actions": 6,
                    "max_patches": 2,
                    "process_timeout_s": 60,
                    "audit_deadline_s": 300,
                },
            ),
            db,
        )
        first = run_investigation("MC-01", audit_id, mode="mock", db_path=db)
        stalled = run_investigation("MC-01", audit_id, mode="mock", db_path=db)
        reserved = reserve_recovery(audit_id, db)
        recovered = run_investigation(
            "MC-01",
            audit_id,
            mode="mock",
            strategy=RECOVERY_STRATEGY,
            db_path=db,
        )
        executed_recovery = {
            "kind": "ACTUAL_EXECUTED_DEVELOPMENT_RECOVERY",
            "fixture_id": "MC-01",
            "provider_mode": "mock",
            "first_outcome": first["trajectory"]["outcome"],
            "repeated_outcome": stalled["trajectory"]["outcome"],
            "strategy": recovered["strategy"],
            "recovery_outcome": recovered["trajectory"]["outcome"],
            "recovery_count": recovered["trajectory"]["recovery_count"],
            "counters_before_recovery": reserved["remaining_limits"],
            "counters_after_recovery": recovered["remaining_limits"],
            "final_run_state": get_audit(audit_id, db)["run_state"],
            "actions": list_actions(audit_id, db),
            "events": list_events(audit_id, db_path=db),
        }

    artifact = {
        "schema_version": "benchproof/v2",
        "artifact_kind": "W8_PREPARATION_AND_EXECUTED_RECOVERY",
        "created_at": datetime.now(UTC).isoformat(),
        "suite_id": SUITE_ID,
        "suite_frozen_at": FROZEN_AT,
        "contamination_status": "development-only synthetic traces; not final W8 outcomes",
        "rule_version": FINGERPRINT_RULE_VERSION,
        "repeat_threshold": STALL_REPEAT_THRESHOLD,
        "synthetic_classification": {
            "correct": sum(1 for item in classifications if item["correct"]),
            "total": len(classifications),
            "traces": classifications,
        },
        "executed_recovery": executed_recovery,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(OUTPUT)
    print(f"classified={artifact['synthetic_classification']['correct']}/{len(classifications)}")
    print(f"recovery={executed_recovery['recovery_outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
