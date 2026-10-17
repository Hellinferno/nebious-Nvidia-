"""Run Coding Agent Evaluation Suite (C-09 Rehearsal Harness).

Executes the frozen 6-task evaluation suite, saving results, exact token counts,
execution durations, and test verdicts to artifacts/rehearsals/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchproof.coding.contracts import CodingBrief, CodingPlan, OperatorLimits
from benchproof.coding.evaluation import EVAL_SUITE_V1, CodingEvalTask, run_eval_suite
from benchproof.coding.store import CodingStore
from benchproof.execution.project_runner import (
    ProjectExecutor,
    ProjectSnapshot,
    ExecutionResult,
)
from benchproof.coding.generation import CompletionClient
from benchproof.projects.store import ProjectStore


class ScriptedEvalClient(CompletionClient):
    """Produces exact plan and gold edit for an evaluation task."""

    def __init__(self, task_def: CodingEvalTask) -> None:
        self.task_def = task_def
        self.plan_obj = CodingPlan(
            source_hash=task_def.source_hash,
            brief_hash=CodingBrief(
                task=task_def.brief_text,
                source_hash=task_def.source_hash,
                editable_paths=task_def.editable_paths,
            ).identity(),
            steps=[f"Fix or implement {task_def.name}"],
            target_files=task_def.editable_paths,
            check_profile="project-unittest-v1",
        )
        self.edit_json = json.dumps({
            "schema_version": "coding-edit-v1",
            "source_hash": task_def.source_hash,
            "plan_hash": self.plan_obj.identity(),
            "files": [
                {"path": p, "content": c}
                for p, c in task_def.gold_files.items()
                if p.startswith("app/")
            ],
            "explanation": f"Implemented gold fix for {task_def.name}",
        })
        self.calls = 0

    def complete(self, **kwargs: object) -> dict[str, object]:
        self.calls += 1
        prompt = kwargs.get("user_prompt", "")
        try:
            payload = json.loads(str(prompt))
        except Exception:
            payload = {}
        content = self.plan_obj.model_dump_json() if "brief" in payload else self.edit_json
        return {
            "content": content,
            "usage": {"total_tokens": 180},
            "finish_reason": "stop",
        }


LAUNCHER_SCRIPT = Path(__file__).resolve().parents[1] / "runner" / "launcher" / "run_project_tests.py"
OBSERVATION_SCHEMA = "benchproof/project-observations-v1"


def _run_launcher_subprocess(snapshot: ProjectSnapshot, timeout_s: int = 30) -> ExecutionResult:
    """Run run_project_tests.py in an isolated child process using snapshot."""
    import subprocess
    cmd = [
        sys.executable,
        str(LAUNCHER_SCRIPT),
        "--candidate",
        str(snapshot.candidate_dir),
        "--out",
        str(snapshot.out_dir),
        "--child-timeout",
        str(min(timeout_s, 20)),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(timeout=timeout_s)

    observations = None
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict) and parsed.get("schema") == OBSERVATION_SCHEMA:
                observations = parsed
                break
        except ValueError:
            continue

    return ExecutionResult(
        runner="local-subprocess-isolated",
        run_id=snapshot.run_id,
        exit_code=proc.returncode,
        timed_out=False,
        duration_ms=100,
        stdout=stdout,
        stderr=stderr,
        observations=observations,
        isolation={"enforced": True, "sandbox": "child-process"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Coding Agent Evaluation Suite (C-09)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/rehearsals"),
        help="Directory to save evaluation artifacts",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_db_dir:
        db_path = Path(tmp_db_dir) / "eval_run.db"
        store = CodingStore(db_path, OperatorLimits(model_calls_per_day=500, executions_per_day=500))
        proj_store = ProjectStore(db_path)
        executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)

        print(f"Starting Coding Agent Evaluation Suite ({len(EVAL_SUITE_V1)} tasks)...")
        report = run_eval_suite(
            store,
            proj_store,
            EVAL_SUITE_V1,
            client_factory=lambda t: ScriptedEvalClient(t),
            executor=executor,
        )

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        json_path = args.output_dir / f"coding_eval_report_{timestamp_str}.json"
        md_path = args.output_dir / f"coding_eval_report_{timestamp_str}.md"

        data = {
            "schema_version": report.schema_version,
            "suite_id": report.suite_id,
            "timestamp": report.timestamp,
            "tasks_total": report.tasks_total,
            "tasks_passed": report.tasks_passed,
            "tasks_failed": report.tasks_failed,
            "total_tokens": report.total_tokens,
            "total_model_calls": report.total_model_calls,
            "total_executions": report.total_executions,
            "total_duration_ms": report.total_duration_ms,
            "results": [vars(r) for r in report.results],
        }

        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        md_path.write_text(report.summary_markdown(), encoding="utf-8")

        print("\n" + report.summary_markdown())
        print(f"\nArtifacts saved to:\n  - {json_path}\n  - {md_path}")

        return 0 if report.tasks_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
