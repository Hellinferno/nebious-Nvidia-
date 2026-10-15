"""Freeze or verify the B-19 evaluation configuration.

Writes `backend/evaluation/eval-config-v1.json`. The configuration is `frozen` only
when the runtime source is committed and the candidate image reference is known;
otherwise it is written as a `candidate` with its blockers. A frozen configuration is
never overwritten: a changed runtime needs a new configuration version.

Usage:
    python scripts/freeze_eval_config.py            # write (or refresh a candidate) configuration
    python scripts/freeze_eval_config.py --verify   # compare the stored configuration with the current runtime
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

from benchproof.execution.docker_runner import DockerRunner
from benchproof.trials.config import (
    CONFIG_PATH,
    DEFAULT_MODEL_ID,
    REPO_ROOT,
    build_config,
    identity,
    load_config,
    verify_config,
)


def candidate_image_ref() -> tuple[str | None, str]:
    runner = DockerRunner()
    ok, detail = runner.available()
    return (runner.image_ref() if ok else None), detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--model", default=None, help="model id (default: NEBIUS_MODEL_ID or the pinned model)")
    parser.add_argument("--no-docker", action="store_true", help="skip the image probe (writes a candidate)")
    args = parser.parse_args()

    image_ref, docker_detail = (None, "skipped") if args.no_docker else candidate_image_ref()

    if args.verify:
        config = load_config()
        model_id = config["identity"]["model"]["model_id"]
        problems = verify_config(config, identity(model_id, image_ref))
        print(json.dumps({"config": str(CONFIG_PATH.relative_to(REPO_ROOT)), "freeze_status": config["freeze_status"],
                          "config_hash": config["config_hash"], "docker": docker_detail, "problems": problems},
                         indent=2))
        return 1 if problems else 0

    load_dotenv(REPO_ROOT / ".env")
    model_id = args.model or os.getenv("NEBIUS_MODEL_ID", "").strip() or DEFAULT_MODEL_ID
    config = build_config(model_id, image_ref)
    if CONFIG_PATH.exists():
        existing = load_config()
        if existing.get("freeze_status") == "frozen" and existing["config_hash"] != config["config_hash"]:
            print(f"refusing to overwrite frozen configuration {existing['config_hash'][:16]}; "
                  "a changed runtime needs a new configuration version", file=sys.stderr)
            return 1
        if existing.get("freeze_status") == "frozen":
            print(json.dumps({"unchanged": True, "config_hash": existing["config_hash"]}))
            return 0
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "config": str(CONFIG_PATH.relative_to(REPO_ROOT)),
        "freeze_status": config["freeze_status"],
        "freeze_blockers": config["freeze_blockers"],
        "config_hash": config["config_hash"],
        "model_id": model_id,
        "image_ref": image_ref,
        "docker": docker_detail,
        "plans": {k: v["trials"] for k, v in config["identity"]["suites"]["plans"].items()},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
