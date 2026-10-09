#!/usr/bin/env python3
"""CLI tool for independent evidence bundle validation and replay.

Usage:
    python scripts/replay_bundle.py --bundle artifacts/bundles/benchproof-audit-XYZ.zip
    python scripts/replay_bundle.py --bundle artifacts/bundles/benchproof-audit-XYZ.zip --verify-only
    python scripts/replay_bundle.py --bundle artifacts/bundles/benchproof-audit-XYZ.zip --output replay_record.json
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from benchproof.bundle.replay import replay_bundle
from benchproof.bundle.validator import validate_bundle_nonexecuting


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BenchProof Independent Evidence Bundle Validator and Replayer"
    )
    parser.add_argument(
        "--bundle",
        "-b",
        type=Path,
        required=True,
        help="Path to the evidence bundle ZIP archive",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run non-executing cryptographic validation (no candidate execution)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Path to save the resulting verification/replay JSON record",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON output instead of human-readable tables",
    )

    args = parser.parse_args()

    if not args.bundle.exists():
        print(f"Error: Bundle file not found at {args.bundle}", file=sys.stderr)
        return 1

    print("\n=======================================================")
    print("  BenchProof v2 Evidence Assurance Validator")
    print(f"  Target Bundle: {args.bundle.name}")
    print("=======================================================\n")

    if args.verify_only:
        print("[*] Running non-executing cryptographic validation...")
        val_result = validate_bundle_nonexecuting(args.bundle)

        if args.json:
            print(json.dumps(val_result, indent=2))
        else:
            print(f"Audit ID:          {val_result.get('audit_id')}")
            print(f"Fixture:           {val_result.get('fixture_id')}")
            print(f"Recorded Verdict:  {val_result.get('gate_verdict')}")
            print(f"Files Verified:    {val_result.get('verified_files')}/{val_result.get('total_files')}")
            print(f"Manifest Hash:     {'VALID' if val_result.get('manifest_hash_valid') else 'INVALID'}")
            print(f"Cryptographic SHA: {'PASS - ALL MATCH' if val_result.get('valid') else 'FAIL - TAMPERED'}")

            if val_result.get("discrepancies"):
                print("\n[!] Discrepancies detected:")
                for d in val_result["discrepancies"]:
                    print(f"    - {d}")

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(val_result, indent=2), encoding="utf-8")
            print(f"\nSaved validation result to {args.output}")

        return 0 if val_result["valid"] else 1

    print("[*] Performing independent isolated replay with external evaluator oracle...")
    replay_rec = replay_bundle(args.bundle)
    rec_dict = replay_rec.model_dump()

    if args.json:
        print(json.dumps(rec_dict, indent=2))
    else:
        print(f"Replay ID:         {replay_rec.replay_id}")
        print(f"Original Audit ID: {replay_rec.original_audit_id}")
        print(f"Original Verdict:  {replay_rec.original_verdict}")
        print(f"Replayed Verdict:  {replay_rec.replayed_verdict}")
        print(f"Verdict Match:     {'YES' if replay_rec.verdict_matches else 'NO'}")
        print(f"Checks Matched:    {'YES - 100%' if replay_rec.checks_matched else 'NO - MISMATCH'}")
        print(f"Tampered Detected: {'YES (TAMPERED)' if replay_rec.tampered else 'NO (AUTHENTIC)'}")

        if replay_rec.tamper_details:
            print("\n[!] Tamper Details:")
            for d in replay_rec.tamper_details:
                print(f"    - {d}")

        print("\nReplayed Checks Comparison:")
        print(f"{'Check ID':<25} {'Original':<12} {'Replayed':<12} {'Match'}")
        print("-" * 58)
        for c in replay_rec.check_comparisons:
            m = "PASS" if c["match"] else "FAIL"
            print(f"{c['check_id']:<25} {c['original_outcome']:<12} {c['replayed_outcome']:<12} {m}")

        print("\n" + "=" * 58)
        if not replay_rec.tampered and replay_rec.verdict_matches and replay_rec.checks_matched:
            print("  REPLAY SUCCESSFUL: All checks independently verified.")
        else:
            print("  REPLAY FAILED: Discrepancy or tampering detected.")
        print("=" * 58 + "\n")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rec_dict, indent=2), encoding="utf-8")
        print(f"Saved replay record to {args.output}")

    return 0 if (not replay_rec.tampered and replay_rec.verdict_matches and replay_rec.checks_matched) else 1


if __name__ == "__main__":
    sys.exit(main())
