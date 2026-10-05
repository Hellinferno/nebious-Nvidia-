"""Minimal durable worker (B-02): heartbeat only. No candidate execution exists yet.

Runs until interrupted, writing a heartbeat every few seconds so /api/v1/ready
can report worker liveness. It deliberately does not pick up QUEUED audits:
there is no isolated runner adapter, and candidate code must never run here.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from benchproof.storage import migrate
from benchproof.storage.heartbeat import record_heartbeat
from benchproof.storage.lifecycle import migrate_lifecycle

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    db = Path(os.getenv("DATABASE_PATH", "benchproof.db"))
    runner = os.getenv("BENCHPROOF_RUNNER", "mock")
    if runner not in {"mock", "docker", "contree"}:
        print(f"Invalid BENCHPROOF_RUNNER={runner!r}; expected mock, docker or contree")
        return 2
    interval = float(os.getenv("BENCHPROOF_HEARTBEAT_S", "5"))
    max_beats = int(os.getenv("BENCHPROOF_HEARTBEAT_MAX", "0"))  # 0 = run forever
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    migrate(db)
    migrate_lifecycle(db)
    print(f"{worker_id} started; runner={runner}; db={db}; no candidate execution in this version")
    beats = 0
    try:
        while True:
            record_heartbeat(worker_id, runner, db)
            beats += 1
            if max_beats and beats >= max_beats:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    print(f"{worker_id} stopped after {beats} heartbeat(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
