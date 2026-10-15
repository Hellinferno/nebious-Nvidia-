"""Run B0/B1/B2 trials and write one immutable record per assigned trial (B-19/B-21).

A final run (`--final`) measures the frozen held-out suite. It refuses to start unless
the stored configuration is frozen and matches the current runtime, the suite lock
verifies, the isolated Docker runner is ready and the live NVIDIA provider is used.
Existing records are never overwritten; rerunning the same run id resumes it, and a
trial that started without writing a record is kept as INTERRUPTED instead of retried.

Development runs use the development fixtures. Held-out suites outside a final run are
limited to the mock provider (pipeline dry run), so no live model output is ever tuned
on held-out cases.

Usage:
    python scripts/run_trials.py --suite development --provider mock --executor in-process
    python scripts/run_trials.py --suite repair-r12-v1 --final --run-id r12-final-1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import list_fixture_ids
from benchproof.suites import repair_root, verify_lock
from benchproof.trials import (
    DEFAULT_BUDGETS,
    PLAN_SCHEMA,
    SYSTEMS,
    DockerExecutor,
    InProcessExecutor,
    build_plan,
    plan_hash,
    write_once,
)
from benchproof.trials.config import (
    CONFIG_PATH,
    DEFAULT_MODEL_ID,
    REPO_ROOT,
    build_config,
    final_run_problems,
    identity,
    load_config,
    suite_specs,
)
from benchproof.trials.systems import DryRunMockClient, NebiusModelClient, run_plan

DEV_ROOT = BACKEND / "fixtures" / "development"
TRIALS_DIR = REPO_ROOT / "artifacts" / "trials"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", required=True, choices=["development", "repair-r12-v1", "repair-r6-v1"])
    parser.add_argument("--systems", default=",".join(SYSTEMS))
    parser.add_argument("--provider", choices=["live", "mock"], default="live")
    parser.add_argument("--executor", choices=["docker", "in-process"], default="docker")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--cases", help="development only: comma-separated case ids")
    parser.add_argument("--trials", type=int, default=1, help="development only: trials per case")
    args = parser.parse_args()
    systems = tuple(s.strip() for s in args.systems.split(",") if s.strip())
    if not set(systems) <= set(SYSTEMS):
        parser.error(f"unknown system in {systems}")

    load_dotenv(REPO_ROOT / ".env")
    if args.final:
        if args.suite == "development" or args.cases or systems != SYSTEMS:
            parser.error("a final run uses a frozen suite, every system and every assigned trial")
        args.provider, args.executor = "live", "docker"
    elif args.suite != "development" and args.provider == "live":
        parser.error("live non-final runs on held-out suites are refused (would tune on the holdout)")

    executor = DockerExecutor() if args.executor == "docker" else InProcessExecutor()
    image_ref = None
    if args.executor == "docker":
        ok, detail = DockerRunner().available()
        if not ok:
            print(f"RUNNER_UNAVAILABLE before any trial started: {detail}", file=sys.stderr)
            return 2
        image_ref = DockerRunner().image_ref()

    if args.suite == "development":
        case_root = DEV_ROOT
        case_ids = args.cases.split(",") if args.cases else list_fixture_ids()
        specs = build_plan(case_ids, args.trials, "development-v2", systems)
    else:
        case_root = repair_root()
        specs, _ = suite_specs(args.suite)
        specs = [s for s in specs if s.system in systems]

    if args.final:
        config = load_config(CONFIG_PATH)
        model_id = config["identity"]["model"]["model_id"]
        current = identity(model_id, image_ref)
        problems = final_run_problems(config, current, executor_name=executor.name,
                                      provider_mode=args.provider, model_id=model_id)
        problems += [f"suite lock: {p}" for p in verify_lock()]
        if problems:
            print(json.dumps({"refused": True, "problems": problems}, indent=2), file=sys.stderr)
            return 1
    else:
        model_id = os.getenv("NEBIUS_MODEL_ID", "").strip() or DEFAULT_MODEL_ID
        config = build_config(model_id, image_ref)
        config["freeze_status"] = "development"

    needs_model = any(s.system != "B0" for s in specs)
    client = None
    if needs_model:
        client = (NebiusModelClient(model_id, DEFAULT_BUDGETS["max_output_tokens_per_call"])
                  if args.provider == "live" else DryRunMockClient())

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    run_dir = TRIALS_DIR / (args.run_id or f"{args.suite}-{'final' if args.final else 'dev'}-{stamp}")
    plan = {
        "schema": PLAN_SCHEMA, "suite": args.suite if args.suite != "development" else "development-v2",
        "case_root": case_root.relative_to(REPO_ROOT).as_posix(), "final": args.final,
        "config_id": config["config_id"], "config_hash": config["config_hash"],
        "freeze_status": config["freeze_status"], "provider_mode": args.provider,
        "model_id": model_id if needs_model else None, "executor": executor.name, "image_ref": image_ref,
        "plan_hash": plan_hash(specs), "trials": [s.to_dict() for s in specs],
    }
    plan_path = run_dir / "plan.json"
    if plan_path.exists():
        stored = json.loads(plan_path.read_text(encoding="utf-8"))
        if stored["plan_hash"] != plan["plan_hash"] or stored["config_hash"] != plan["config_hash"]:
            print("refusing to resume: plan or configuration differs from the stored run", file=sys.stderr)
            return 1
    else:
        write_once(plan_path, {**plan, "created_at": datetime.now(UTC).isoformat()})

    counts = run_plan(specs, run_dir=run_dir, case_root=case_root, suite=plan["suite"], config=config,
                      client=client, executor=executor)
    print(json.dumps({"run_dir": str(run_dir.relative_to(REPO_ROOT)), "assigned": len(specs), **counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
