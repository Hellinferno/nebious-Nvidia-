"""Heartbeat service with explicitly enabled, separately budgeted coding-task work."""

from __future__ import annotations

import math
import os
import sys
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from benchproof.storage import migrate
from benchproof.storage.heartbeat import record_heartbeat
from benchproof.storage.lifecycle import migrate_lifecycle

REPO_ROOT = Path(__file__).resolve().parents[2]


class DisabledCompletionClient:
    def complete(self, **kwargs):
        raise RuntimeError("Paid work is disabled in reconciliation-only mode")


def coding_config_from_environment():
    from benchproof.coding.runtime import CodingRuntimeConfig

    enabled = os.getenv("BENCHPROOF_CODING_ENABLED", "false").strip().lower()
    if enabled not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
        raise ValueError("Unsupported coding enable flag")
    return CodingRuntimeConfig(
        enabled=enabled in {"true", "1", "yes", "on"},
        model_calls_per_day=int(os.getenv("BENCHPROOF_CODING_MODEL_CALLS_PER_DAY", "0")),
        executions_per_day=int(os.getenv("BENCHPROOF_CODING_EXECUTIONS_PER_DAY", "0")),
        max_tasks=int(os.getenv("BENCHPROOF_CODING_MAX_TASKS", "100")),
        deadline_epoch=float(os.getenv("BENCHPROOF_CODING_DEADLINE_EPOCH", "0")),
        max_output_tokens=int(os.getenv("BENCHPROOF_CODING_OUTPUT_TOKENS", "2048")),
    )


def configured_coding_worker(db: Path, worker_id: str, runner_mode: str):
    from benchproof.coding.engine import CodingEngine, DispatchingExecutor, InvoiceExecutor
    from benchproof.coding.store import CodingStore
    from benchproof.coding.worker import CodingWorker
    from benchproof.execution.docker_runner import DockerRunner
    from benchproof.execution.project_runner import ProjectExecutor
    from benchproof.providers import NebiusAdapter

    config = coding_config_from_environment()
    records = CodingStore(db, config.operator_limits())
    model = os.getenv("NEBIUS_MODEL_ID", "").strip()
    key = os.getenv("NEBIUS_API_KEY", "")
    reason = config.blocked_reason(
        provider_configured=key not in {"", "your_api_key_here"} and bool(model),
        runner_ready=runner_mode == "docker",
    )
    if reason:
        if not records.pending_executions():
            if config.enabled:
                raise ValueError(reason)
            return None
        cleanup_adapter = DockerRunner()
        engine = CodingEngine(
            client=DisabledCompletionClient(), model_id="disabled-cleanup-only",
            executor=DispatchingExecutor(InvoiceExecutor(cleanup_adapter), ProjectExecutor(cleanup_adapter)),
        )
        return CodingWorker(records, engine, worker_id=worker_id, live_enabled=False)
    adapter = DockerRunner()
    ready, _detail = adapter.available()
    if not ready:
        raise ValueError("RUNNER_UNAVAILABLE")
    provider = NebiusAdapter(
        api_key=key, base_url=os.getenv("NEBIUS_BASE_URL") or None, timeout_s=30,
    )
    executor = DispatchingExecutor(InvoiceExecutor(adapter), ProjectExecutor(adapter))
    engine = CodingEngine(
        client=provider, model_id=model, executor=executor,
        max_output_tokens=config.max_output_tokens,
    )
    return CodingWorker(
        records, engine, worker_id=f"coding-{worker_id}", live_enabled=True,
        session_seconds_remaining=config.seconds_remaining,
    )


def heartbeat_loop(worker_id, runner, db, interval, max_beats, processor=None) -> int:
    pool = ThreadPoolExecutor(max_workers=1) if processor is not None else None
    pending: Future | None = None
    beats = 0
    try:
        while True:
            record_heartbeat(worker_id, runner, db)
            beats += 1
            if pending is not None and pending.done():
                failure = pending.exception()
                if failure is not None:
                    print(f"Coding action stopped unexpectedly: {type(failure).__name__}", flush=True)
                pending = None
            if pool is not None and pending is None:
                pending = pool.submit(processor.run_once)
            if max_beats and beats >= max_beats:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
    return beats


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
    if not math.isfinite(interval) or not 0 < interval <= 30 or max_beats < 0:
        print("Invalid heartbeat interval or beat limit")
        return 2
    try:
        processor = configured_coding_worker(db, worker_id, runner)
    except ValueError:
        print("Coding startup refused: check explicit enablement, provider, Docker, daily allowances and trusted deadline")
        return 2
    if processor is not None and processor.live_enabled:
        worker_id = processor.worker_id
    mode = "enabled" if processor is not None and processor.live_enabled else "disabled; reconciliation only if needed"
    print(f"{worker_id} started; runner={runner}; db={db}; coding={mode}")
    beats = heartbeat_loop(worker_id, runner, db, interval, max_beats, processor)
    print(f"{worker_id} stopped after {beats} heartbeat(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
