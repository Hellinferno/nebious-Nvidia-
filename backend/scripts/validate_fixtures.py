"""Validate development fixtures against trusted expected properties (B-03).

For every fixture in the suite: the original source must fail its intended
checks, the reference repair must be VERIFIED, and the clean control must be
VERIFIED untouched. Writes artifacts/fixtures/<suite>_<timestamp>.json.

DEVELOPMENT ONLY: candidate code is imported in-process on this machine.

Usage: python scripts/validate_fixtures.py --suite development-v2
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchproof.constraints import contract_hash
from benchproof.evaluator.harness import evaluator_hash, validate_fixture
from benchproof.fixtures import list_fixture_ids, load_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="development-v2")
    args = parser.parse_args()

    ids = [f for f in list_fixture_ids() if load_manifest(f).get("suite") == args.suite]
    if not ids:
        print(f"No fixtures found for suite {args.suite!r}")
        return 1

    reports = [validate_fixture(f) for f in ids]
    all_ok = all(r["ok"] for r in reports)

    print(
        f"suite={args.suite} contract_hash={contract_hash()[:12]} "
        f"evaluator_hash={evaluator_hash()[:12]}"
    )
    print(f"{'fixture':14} {'verdict':12} {'failing':46} {'ref repair':12} ok")
    for r in reports:
        ref = r["reference_repair"]["verdict"] if r["reference_repair"] else "n/a"
        failing = ",".join(r["original"]["failing_checks"]) or "-"
        status = "OK" if r["ok"] else "FAIL"
        print(f"{r['fixture_id']:14} {r['original']['verdict']:12} {failing:46} {ref:12} {status}")
        for p in r["problems"]:
            print(f"    ! {p}")

    out_dir = REPO_ROOT / "artifacts" / "fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out_dir / f"{args.suite}_{ts}.json"
    path.write_text(
        json.dumps(
            {
                "suite": args.suite,
                "timestamp": ts,
                "contract_hash": contract_hash(),
                "evaluator_hash": evaluator_hash(),
                "all_ok": all_ok,
                "fixtures": reports,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"Saved {path.relative_to(REPO_ROOT)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
