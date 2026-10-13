"""Generate development-only B-16 mutation validation and executed-run evidence."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.gate import verify_candidate_app
from benchproof.mutations import (
    TEMPLATE_SET_VERSION,
    TEMPLATES,
    MutationTemplate,
    Replacement,
    execute_mutant,
    run_mutation_assessment,
)
from benchproof.storage import migrate, save_audit


def build_evidence() -> dict[str, object]:
    accepted = fixture_dir("clean-service") / "app"
    baseline = verify_candidate_app(accepted)
    baseline_checks = {item["check_id"]: item["outcome"] for item in baseline["checks"]}
    validations = [
        execute_mutant(accepted, template, baseline_checks).model_dump(mode="json")
        for template in TEMPLATES
    ]
    invalid = MutationTemplate(
        "development-invalid-syntax",
        1,
        "idempotency",
        "Malformed test-only control.",
        ("idempotency-duplicate",),
        (
            Replacement(
                "repository.py",
                "return _store.get(tenant_id, {}).get(request_id)",
                "return (",
            ),
        ),
    )
    invalid_result = execute_mutant(accepted, invalid, baseline_checks).model_dump(mode="json")

    output_dir = ROOT / "artifacts" / "mutations"
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bp-mutation-evidence-", dir=output_dir) as tmp:
        db = Path(tmp) / "evidence.db"
        migrate(db)
        audit = AuditRecord(
            audit_id="audit-development-mutation-strength",
            owner_ref="development-evidence",
            fixture_id="clean-service",
            source_hash=source_hash_for_dir(accepted),
            contract_hash=contract_hash(),
        )
        save_audit(audit, db)
        executed = run_mutation_assessment(audit.audit_id, max_mutants=3, db_path=db)

    return {
        "schema_version": "benchproof/development-mutation-evidence-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "development-only; not final M12 evaluation outcomes",
        "template_set_version": TEMPLATE_SET_VERSION,
        "baseline_verdict": baseline["verdict"],
        "base_candidate_hash": source_hash_for_dir(accepted),
        "template_validation": validations,
        "invalid_control": invalid_result,
        "executed_relevant_run": executed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "mutations" / "development_strength.json",
    )
    args = parser.parse_args()
    evidence = build_evidence()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    run = evidence["executed_relevant_run"]
    assert isinstance(run, dict)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": run["strength_status"],
                "counts": run["counts"],
                "candidate_unchanged": run["candidate_unchanged"],
                "overhead_ms": run["overhead_ms"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
