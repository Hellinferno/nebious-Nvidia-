"""Compute separated B0/B1/B2 outcomes from a run's immutable trial records (B-19/B-21).

Writes `summary.json` and `summary.md` next to the records. These are derived files;
the records and `plan.json` are the source of truth and are never modified.

Usage:
    python scripts/summarize_trials.py artifacts/trials/<run_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from benchproof.trials import TrialSpec, load_records
from benchproof.trials.config import REPO_ROOT
from benchproof.trials.summary import summarize, to_markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else Path.cwd() / args.run_dir
    plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    specs = [TrialSpec(t["order"], t["system"], t["case_id"], t["trial_index"]) for t in plan["trials"]]
    summary = summarize(load_records(run_dir), specs, REPO_ROOT / plan["case_root"], plan["suite"])
    summary["final"] = plan["final"]
    summary["development_only"] = summary["development_only"] or not plan["final"]
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "summary.md").write_text(to_markdown(summary), encoding="utf-8")
    print(to_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
