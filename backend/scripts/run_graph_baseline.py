"""Generate and save baseline records for all development fixtures (B-07)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from benchproof.baseline import run_baseline
from benchproof.fixtures import list_fixture_ids

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "baseline"


def main() -> int:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    fids = list_fixture_ids()
    print(f"Generating baseline records for {len(fids)} fixtures...")

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    for fid in fids:
        rec = run_baseline(fid)
        fname = f"{fid}_{ts}.json"
        out_path = ARTIFACTS_DIR / fname
        out_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        print(
            f"  {fid:14} -> verdict={rec['gate_verdict']:12} failed={rec['failed_checks']} -> {fname}"
        )

    print(f"Baseline generation complete. Artifacts saved in {ARTIFACTS_DIR}")
    return 0


if __name__ == "__main__":
    main()
