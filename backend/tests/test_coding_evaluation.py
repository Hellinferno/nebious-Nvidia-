"""Tests for Coding Agent Evaluation Suite (C-09).

Verifies task definitions, source hash stability, evaluation runner execution,
accurate metric accounting, and no-change handling without regressions.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

import pytest

from benchproof.coding.contracts import CodingBrief, CodingPlan, OperatorLimits
from benchproof.coding.evaluation import (
    EVAL_SUITE_V1,
    TASK_01_CALC,
    TASK_04_BANK,
    TASK_06_URL_CLEAN,
    CodingEvalTask,
    evaluate_task,
    run_eval_suite,
)
from benchproof.coding.store import CodingStore
from benchproof.execution.base import ExecutionResult
from benchproof.execution.project_runner import ProjectExecutor, ProjectSnapshot
from benchproof.projects.store import ProjectStore
from benchproof.coding.generation import CompletionClient


class MockScriptedClient(CompletionClient):
    """Deterministic script client matching task plan and gold edits."""

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

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        prompt = kwargs.get("user_prompt", "")
        try:
            payload = json.loads(str(prompt))
        except Exception:
            payload = {}
        content = self.plan_obj.model_dump_json() if "brief" in payload else self.edit_json
        return {
            "content": content,
            "usage": {"total_tokens": 150},
            "finish_reason": "stop",
        }


from tests.test_project_runner import _run_launcher_subprocess


def make_executor() -> ProjectExecutor:
    return ProjectExecutor(synthetic_runner=_run_launcher_subprocess)


def test_eval_suite_manifest_integrity() -> None:
    """Verifies all 6 tasks in the suite have unique IDs, valid schemas, and clean paths."""
    assert len(EVAL_SUITE_V1) == 6
    task_ids = [t.task_id for t in EVAL_SUITE_V1]
    assert len(set(task_ids)) == 6

    categories = [t.category for t in EVAL_SUITE_V1]
    assert categories.count("bug_fix") == 3
    assert categories.count("bounded_feature") == 2
    assert categories.count("no_change") == 1

    for t in EVAL_SUITE_V1:
        assert len(t.source_hash) == 64
        assert all(p.startswith("app/") for p in t.editable_paths)
        assert any(p.startswith("tests/") for p in t.initial_files.keys())


def test_evaluate_single_bug_fix_task(tmp_path: Path) -> None:
    """Tests evaluating a single bug fix task (String Calculator)."""
    db = tmp_path / "eval_bug.db"
    store = CodingStore(db, OperatorLimits(model_calls_per_day=50, executions_per_day=50))
    proj_store = ProjectStore(db)

    executor = make_executor()
    client = MockScriptedClient(TASK_01_CALC)

    result = evaluate_task(
        store,
        proj_store,
        TASK_01_CALC,
        client=client,
        executor=executor,
        owner_ref="owner-eval-bug",
    )

    assert result.task_id == TASK_01_CALC.task_id
    assert result.category == "bug_fix"
    assert result.verdict == "PASSED"
    assert result.model_calls == 2  # 1 plan + 1 edit
    assert result.executions >= 2   # baseline + candidate
    assert result.checks_passed == 3
    assert "negatives" in result.patch_diff


def test_evaluate_bounded_feature_task(tmp_path: Path) -> None:
    """Tests evaluating a single bounded feature task (BankAccount transfer)."""
    db = tmp_path / "eval_feat.db"
    store = CodingStore(db, OperatorLimits(model_calls_per_day=50, executions_per_day=50))
    proj_store = ProjectStore(db)

    executor = make_executor()
    client = MockScriptedClient(TASK_04_BANK)

    result = evaluate_task(
        store,
        proj_store,
        TASK_04_BANK,
        client=client,
        executor=executor,
        owner_ref="owner-eval-feat",
    )

    assert result.task_id == TASK_04_BANK.task_id
    assert result.category == "bounded_feature"
    assert result.verdict == "PASSED"
    assert "def transfer(" in result.patch_diff


def test_evaluate_no_change_clean_task(tmp_path: Path) -> None:
    """Tests evaluating a clean project that needs no change."""
    db = tmp_path / "eval_clean.db"
    store = CodingStore(db, OperatorLimits(model_calls_per_day=50, executions_per_day=50))
    proj_store = ProjectStore(db)

    executor = make_executor()
    client = MockScriptedClient(TASK_06_URL_CLEAN)

    result = evaluate_task(
        store,
        proj_store,
        TASK_06_URL_CLEAN,
        client=client,
        executor=executor,
        owner_ref="owner-eval-clean",
    )

    assert result.task_id == TASK_06_URL_CLEAN.task_id
    assert result.category == "no_change"
    assert result.verdict == "NOOP_PASSED"
    assert result.model_calls == 0  # No unnecessary model calls!
    assert result.patch_diff == ""


def test_run_full_eval_suite(tmp_path: Path) -> None:
    """Runs the entire 6-task evaluation suite and verifies aggregated report."""
    db = tmp_path / "eval_suite.db"
    store = CodingStore(db, OperatorLimits(model_calls_per_day=500, executions_per_day=500))
    proj_store = ProjectStore(db)
    executor = make_executor()

    report = run_eval_suite(
        store,
        proj_store,
        EVAL_SUITE_V1,
        client_factory=lambda t: MockScriptedClient(t),
        executor=executor,
    )

    assert report.tasks_total == 6
    assert report.tasks_passed == 6
    assert report.tasks_failed == 0
    assert report.total_model_calls == 10  # 5 tasks * 2 calls + 1 noop * 0 calls
    assert report.total_executions >= 11
    assert len(report.results) == 6

    md = report.summary_markdown()
    assert "**Pass Rate**: 6/6 (100.0%)" in md
    assert "TASK-01-CALC-NEG" in md
    assert "TASK-06-URL-CLEAN" in md
