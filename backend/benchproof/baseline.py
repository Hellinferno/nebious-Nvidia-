"""Baseline execution and graph linkage (B-07).

Executes the candidate app in isolation to establish a visible baseline,
evaluates observations using the trusted evaluator, links results to
graph nodes and contracts, and records baseline artifacts.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchproof.constraints import contract_hash
from benchproof.domain import CheckOutcome, GateVerdict
from benchproof.evaluator.harness import collect_observations_in_process, evaluator_hash
from benchproof.evaluator.observations import evaluate_observations
from benchproof.execution.docker_runner import DockerRunner
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.graph.builder import build_state_graph
from benchproof.storage import save_graph
from benchproof.storage.lifecycle import TRUSTED_EVALUATOR, append_event, record_check_result


def run_baseline(
    fixture_id: str,
    audit_id: str | None = None,
    use_docker: bool = False,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Execute isolated baseline for a fixture and link observations to graph."""
    fdir = fixture_dir(fixture_id)
    app_dir = fdir / "app"
    shash = source_hash_for_dir(app_dir)
    chash = contract_hash()
    ehash = evaluator_hash()

    # 1. Build State Graph
    graph = build_state_graph(app_dir, chash)

    # 2. Execute in Runner
    obs: dict[str, Any]
    image_hash = "local-in-process"
    start_time = time.perf_counter()

    if use_docker:
        runner = DockerRunner()
        avail, _ = runner.available()
        if avail:
            res = runner.run_candidate(app_dir, timeout_s=30)
            obs = res.observations or {"error": res.logs, "route": {}, "worker": {}}
            image_hash = res.image_digest
        else:
            obs = collect_observations_in_process(app_dir)
    else:
        obs = collect_observations_in_process(app_dir)

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    # 3. Judge Observations with Trusted Evaluator
    worker_file = app_dir / "worker.py"
    worker_src = worker_file.read_text(encoding="utf-8") if worker_file.exists() else None
    check_results = evaluate_observations(obs, worker_src)
    for cr in check_results:
        cr.source_hash = shash
        cr.contract_hash = chash
        cr.evaluator_hash = ehash
        cr.image_hash = image_hash

    # 4. Link Check Results to Graph
    verdict = GateVerdict.VERIFIED
    failed_checks: list[str] = []
    for cr in check_results:
        if cr.outcome != CheckOutcome.PASS_:
            verdict = GateVerdict.REJECTED
            failed_checks.append(cr.check_id)

    # Save to database if audit_id provided
    if audit_id:
        save_graph(
            graph_id=graph.graph_id,
            source_hash=shash,
            contract_hash=chash,
            graph_hash=graph.graph_hash,
            coverage=graph.coverage,
            graph_data=graph.model_dump(),
            audit_id=audit_id,
            db_path=db_path,
        )
        for cr in check_results:
            record_check_result(
                audit_id=audit_id,
                result=cr,
                author=TRUSTED_EVALUATOR,
                db_path=db_path,
            )
        append_event(
            audit_id,
            "baseline_completed",
            {
                "gate_verdict": verdict.value,
                "failed_checks": failed_checks,
                "elapsed_ms": elapsed_ms,
                "graph_hash": graph.graph_hash,
            },
            db_path=db_path,
        )

    # 5. Build Baseline Artifact
    baseline_record = {
        "schema_version": "benchproof/v2",
        "fixture_id": fixture_id,
        "audit_id": audit_id,
        "source_hash": shash,
        "contract_hash": chash,
        "evaluator_hash": ehash,
        "image_hash": image_hash,
        "graph_id": graph.graph_id,
        "graph_hash": graph.graph_hash,
        "graph_coverage": graph.coverage,
        "gate_verdict": verdict.value,
        "failed_checks": failed_checks,
        "check_results": [cr.model_dump() for cr in check_results],
        "observations": obs,
        "elapsed_ms": elapsed_ms,
        "created_at": datetime.now(UTC).isoformat(),
    }

    return baseline_record
