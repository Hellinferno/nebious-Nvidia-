"""Script to execute full Day 7 Evidence Bundle export and independent replay suite.

Generates real bundle archives and replay records for:
1. MC-01 canonical repair (VERIFIED)
2. AC-01 canonical repair (VERIFIED)
3. Clean service untouched control (VERIFIED)
4. Tampered bundle detection (BLOCKED / TAMPERED)
"""

import argparse
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from benchproof.bundle import export_bundle, replay_bundle, validate_bundle_nonexecuting
from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord, GateVerdict, RunState
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import source_hash
from benchproof.gate import execute_acceptance_gate
from benchproof.patch import (
    compute_diff_hash,
    extract_diff_paths,
    get_canonical_ac01_repair_diff,
    get_canonical_mc01_repair_diff,
)
from benchproof.storage import migrate, save_audit, save_patch
from benchproof.storage.lifecycle import migrate_lifecycle


def setup_audit_and_gate(db_path: Path, fixture_id: str, patch_diff: str | None = None) -> str:
    audit_id = f"aud-export-{fixture_id}"
    shash = source_hash(fixture_id)
    chash = contract_hash()

    audit = AuditRecord(
        audit_id=audit_id,
        owner_ref="benchproof-evaluator",
        fixture_id=fixture_id,
        source_hash=shash,
        contract_hash=chash,
        run_state=RunState.QUEUED,
        gate_verdict=GateVerdict.PENDING,
        mode="live",
    )
    save_audit(audit, db_path=db_path)

    patch_id = None
    if patch_diff:
        patch_id = f"patch-{audit_id}"
        save_patch(
            patch_id=patch_id,
            audit_id=audit_id,
            base_hash=shash,
            diff_hash=compute_diff_hash(patch_diff),
            diff_text=patch_diff,
            approved_paths=extract_diff_paths(patch_diff),
            changed_lines=sum(
                line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
                for line in patch_diff.splitlines()
            ),
            policy_result="PENDING",
            author="trusted-reference-repair",
            db_path=db_path,
        )

    res = execute_acceptance_gate(audit_id, patch_id=patch_id, use_docker=True, db_path=db_path)
    if res["verdict"] != "VERIFIED":
        raise RuntimeError(f"Reference scenario {fixture_id} did not verify: {res['verdict']}")
    print(f"  [+] Gate executed for {fixture_id}: {res['verdict']}")
    return audit_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="new directory; existing paths are refused")
    args = parser.parse_args()
    available, detail = DockerRunner().available()
    if not available:
        print(f"RUNNER_UNAVAILABLE: {detail}", file=sys.stderr)
        return 2
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    artifacts_dir = args.output_dir or backend_dir.parent / "artifacts" / "release-replay" / stamp
    artifacts_dir.mkdir(parents=True, exist_ok=False)
    db_path = artifacts_dir / "replay-evidence.db"
    migrate(db_path)
    migrate_lifecycle(db_path)

    bundles_dir = artifacts_dir / "bundles"
    replay_dir = artifacts_dir / "replay"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)

    print("=========================================================")
    print("  BenchProof Day 7: Bundle Export & Independent Replay")
    print("=========================================================\n")

    # 1. MC-01 Canonical Repair
    print("[1/4] Processing MC-01 Canonical Repair Bundle...")
    mc01_audit = setup_audit_and_gate(db_path, "MC-01", get_canonical_mc01_repair_diff())
    mc01_zip, _mc01_manifest = export_bundle(mc01_audit, bundles_dir / "mc01_canonical_repair_bundle.zip", db_path=db_path)
    mc01_val = validate_bundle_nonexecuting(mc01_zip)
    mc01_replay = replay_bundle(mc01_zip)
    (replay_dir / "mc01_canonical_repair_replay.json").write_text(
        json.dumps(mc01_replay.model_dump(), indent=2), encoding="utf-8"
    )
    print(f"      Verified: {mc01_val['valid']} | Replayed Verdict: {mc01_replay.replayed_verdict}")

    # 2. AC-01 Canonical Repair
    print("[2/4] Processing AC-01 Canonical Repair Bundle...")
    ac01_audit = setup_audit_and_gate(db_path, "AC-01", get_canonical_ac01_repair_diff())
    ac01_zip, _ac01_manifest = export_bundle(ac01_audit, bundles_dir / "ac01_canonical_repair_bundle.zip", db_path=db_path)
    ac01_val = validate_bundle_nonexecuting(ac01_zip)
    ac01_replay = replay_bundle(ac01_zip)
    (replay_dir / "ac01_canonical_repair_replay.json").write_text(
        json.dumps(ac01_replay.model_dump(), indent=2), encoding="utf-8"
    )
    print(f"      Verified: {ac01_val['valid']} | Replayed Verdict: {ac01_replay.replayed_verdict}")

    # 3. Clean Service Untouched Control
    print("[3/4] Processing Clean Service Control Bundle...")
    clean_audit = setup_audit_and_gate(db_path, "clean-service", None)
    clean_zip, _clean_manifest = export_bundle(clean_audit, bundles_dir / "clean_service_control_bundle.zip", db_path=db_path)
    clean_val = validate_bundle_nonexecuting(clean_zip)
    clean_replay = replay_bundle(clean_zip)
    (replay_dir / "clean_service_control_replay.json").write_text(
        json.dumps(clean_replay.model_dump(), indent=2), encoding="utf-8"
    )
    print(f"      Verified: {clean_val['valid']} | Replayed Verdict: {clean_replay.replayed_verdict}")

    # 4. Tampered Bundle Defense Detection
    print("[4/4] Generating Tampered Bundle Defense Evidence...")
    tampered_zip = bundles_dir / "tampered_candidate_diff_bundle.zip"
    with zipfile.ZipFile(mc01_zip, "r") as zin, zipfile.ZipFile(tampered_zip, "w") as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "candidate.diff":
                content = content + b"\n# MALICIOUS TAMPERED LINE"
            zout.writestr(item, content)

    tampered_val = validate_bundle_nonexecuting(tampered_zip)
    tampered_replay = replay_bundle(tampered_zip)
    (replay_dir / "tampered_bundle_rejection_evidence.json").write_text(
        json.dumps({
            "validation_outcome": tampered_val,
            "replay_record": tampered_replay.model_dump(),
        }, indent=2),
        encoding="utf-8",
    )
    print(f"      Tamper Detected by Validator: {not tampered_val['valid']}")
    print(f"      Tamper Detected by Replayer:  {tampered_replay.tampered} (Verdict: {tampered_replay.replayed_verdict})")

    records = ((mc01_val, mc01_replay), (ac01_val, ac01_replay), (clean_val, clean_replay))
    replays_ok = all(
        validation["valid"] and record.verdict_matches and record.checks_matched
        and record.replayed_verdict == "VERIFIED" and not record.tampered
        for validation, record in records
    )
    tamper_ok = (
        not tampered_val["valid"] and tampered_replay.tampered
        and tampered_replay.replayed_verdict == "BLOCKED"
    )
    if not replays_ok or not tamper_ok:
        print("Replay verification failed; preserved artifacts for inspection", file=sys.stderr)
        return 1

    print("\n=========================================================")
    print("  ALL 4 BUNDLE & REPLAY EVIDENCE ARTIFACTS GENERATED!")
    print(f"  Bundles: {bundles_dir}")
    print(f"  Replay:  {replay_dir}")
    print("=========================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
