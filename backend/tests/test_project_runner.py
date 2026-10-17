"""Acceptance verification for generic project test execution (C-04).

Acceptance gate:
- Two distinct non-invoice small projects run unchanged with unittest test suites.
- Passing tests report VERIFIED with structured per-check results.
- Intentional failures report REJECTED with traceback details.
- Missing/zero tests collected fail clearly with ZERO_TESTS_COLLECTED.
- Full end-to-end CodingEngine integration: Baseline -> Edit -> Candidate -> Final -> REVIEW_READY.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from benchproof.coding.contracts import CodingBrief, CodingPlan, OperatorLimits
from benchproof.coding.engine import CodingEngine
from benchproof.coding.generation import CompletionClient
from benchproof.coding.store import CodingStore
from benchproof.coding.worker import CodingWorker
from benchproof.execution.base import ExecutionResult
from benchproof.execution.project_runner import (
    OBSERVATION_SCHEMA,
    PROJECT_CONTRACT_HASH,
    PROJECT_LAUNCHER_FILE,
    ProjectExecutor,
    ProjectSnapshot,
)
from benchproof.projects.intake import validate_project_intake
from benchproof.projects.store import ProjectStore

LAUNCHER_SCRIPT = Path(__file__).resolve().parents[1] / "runner" / "launcher" / PROJECT_LAUNCHER_FILE


# ── Sample Project 1: StringCalculator ──────────────────────────────────────

PROJECT_1_FILES = {
    "app/calculator.py": (
        "def add(numbers: str) -> int:\n"
        "    if not numbers.strip():\n"
        "        return 0\n"
        "    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
        "    return sum(parts)\n\n"
        "def multiply(numbers: str) -> int:\n"
        "    if not numbers.strip():\n"
        "        return 1\n"
        "    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
        "    total = 1\n"
        "    for p in parts:\n"
        "        total *= p\n"
        "    return total\n"
    ),
    "tests/test_calculator.py": (
        "import unittest\n"
        "from app.calculator import add, multiply\n\n"
        "class TestStringCalculator(unittest.TestCase):\n"
        "    def test_add_empty(self):\n"
        "        self.assertEqual(add(''), 0)\n\n"
        "    def test_add_numbers(self):\n"
        "        self.assertEqual(add('1, 2, 3'), 6)\n\n"
        "    def test_multiply_numbers(self):\n"
        "        self.assertEqual(multiply('2, 3, 4'), 24)\n"
    ),
}


# ── Sample Project 2: BankAccount ───────────────────────────────────────────

PROJECT_2_FILES = {
    "app/account.py": (
        "class InsufficientFundsError(Exception):\n"
        "    pass\n\n"
        "class BankAccount:\n"
        "    def __init__(self, initial_balance: int = 0) -> None:\n"
        "        if initial_balance < 0:\n"
        "            raise ValueError('Initial balance cannot be negative')\n"
        "        self._balance = initial_balance\n"
        "        self._transactions: list[int] = []\n\n"
        "    @property\n"
        "    def balance(self) -> int:\n"
        "        return self._balance\n\n"
        "    def deposit(self, amount: int) -> None:\n"
        "        if amount <= 0:\n"
        "            raise ValueError('Deposit amount must be positive')\n"
        "        self._balance += amount\n"
        "        self._transactions.append(amount)\n\n"
        "    def withdraw(self, amount: int) -> None:\n"
        "        if amount <= 0:\n"
        "            raise ValueError('Withdrawal amount must be positive')\n"
        "        if amount > self._balance:\n"
        "            raise InsufficientFundsError('Insufficient funds')\n"
        "        self._balance -= amount\n"
        "        self._transactions.append(-amount)\n"
    ),
    "tests/test_account.py": (
        "import unittest\n"
        "from app.account import BankAccount, InsufficientFundsError\n\n"
        "class TestBankAccount(unittest.TestCase):\n"
        "    def test_deposit(self):\n"
        "        acc = BankAccount(100)\n"
        "        acc.deposit(50)\n"
        "        self.assertEqual(acc.balance, 150)\n\n"
        "    def test_withdraw(self):\n"
        "        acc = BankAccount(200)\n"
        "        acc.withdraw(70)\n"
        "        self.assertEqual(acc.balance, 130)\n\n"
        "    def test_overdraft(self):\n"
        "        acc = BankAccount(50)\n"
        "        with self.assertRaises(InsufficientFundsError):\n"
        "            acc.withdraw(100)\n"
    ),
}


def _run_launcher_subprocess(snapshot: ProjectSnapshot, timeout_s: int = 30) -> ExecutionResult:
    """Run run_project_tests.py in an isolated child process using snapshot."""
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


def test_project_1_string_calculator_runs_unchanged_and_passes() -> None:
    executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)
    report = executor.run(PROJECT_1_FILES, operation_id="test-p1-run")

    assert report["profile"] == "project-unittest-v1"
    assert report["verdict"] == "VERIFIED"
    assert report["summary"]["test_count"] == 3
    assert report["summary"]["passed"] == 3
    assert report["summary"]["failures"] == 0
    assert report["summary"]["errors"] == 0

    check_ids = {c["check_id"] for c in report["checks"]}
    assert any("test_add_empty" in cid for cid in check_ids)
    assert any("test_add_numbers" in cid for cid in check_ids)
    assert any("test_multiply_numbers" in cid for cid in check_ids)


def test_project_2_bank_account_runs_unchanged_and_passes() -> None:
    executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)
    report = executor.run(PROJECT_2_FILES, operation_id="test-p2-run")

    assert report["profile"] == "project-unittest-v1"
    assert report["verdict"] == "VERIFIED"
    assert report["summary"]["test_count"] == 3
    assert report["summary"]["passed"] == 3
    assert report["summary"]["failures"] == 0
    assert report["summary"]["errors"] == 0

    check_ids = {c["check_id"] for c in report["checks"]}
    assert any("test_deposit" in cid for cid in check_ids)
    assert any("test_withdraw" in cid for cid in check_ids)
    assert any("test_overdraft" in cid for cid in check_ids)


def test_project_failure_detection() -> None:
    buggy_files = dict(PROJECT_1_FILES)
    # Introduce intentional bug: add subtracts instead of summing
    buggy_files["app/calculator.py"] = (
        "def add(numbers: str) -> int:\n"
        "    return 999  # Bug\n\n"
        "def multiply(numbers: str) -> int:\n"
        "    return 1\n"
    )

    executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)
    report = executor.run(buggy_files, operation_id="test-buggy-run")

    assert report["verdict"] == "REJECTED"
    assert report["summary"]["failures"] >= 1
    failed_checks = [c for c in report["checks"] if c["status"] == "FAILED"]
    assert len(failed_checks) >= 1
    assert any("AssertionError" in c["detail"] for c in failed_checks)


def test_project_zero_tests_collected_fails() -> None:
    empty_test_project = {
        "app/service.py": "def do_work(): pass\n",
        "tests/test_nothing.py": "# No test cases defined here\nx = 1\n",
    }

    executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)
    report = executor.run(empty_test_project, operation_id="test-empty-tests")

    assert report["verdict"] == "REJECTED"
    failed_checks = [c for c in report["checks"] if c["status"] == "FAILED"]
    assert any(c["check_id"] == "ZERO_TESTS_COLLECTED" for c in failed_checks)


def test_e2e_coding_loop_on_user_project(tmp_path: Path) -> None:
    """Full C-03/C-04 vertical slice on a user-provided project."""
    db_path = tmp_path / "coding_projects_e2e.db"
    project_store = ProjectStore(db_path)
    coding_store = CodingStore(db_path, OperatorLimits(model_calls_per_day=50, executions_per_day=50))

    owner = "owner-e2e-project-tester"

    # Step 1: User submits project with a bug in app/calculator.py
    buggy_project = {
        "app/calculator.py": (
            "def add(numbers: str) -> int:\n"
            "    # Bug: returns 0 always\n"
            "    return 0\n"
        ),
        "tests/test_calculator.py": (
            "import unittest\n"
            "from app.calculator import add\n\n"
            "class TestCalc(unittest.TestCase):\n"
            "    def test_add_two(self):\n"
            "        self.assertEqual(add('2, 3'), 5)\n"
        ),
    }

    _manifest, _ = validate_project_intake(buggy_project)
    project_record = project_store.create_project(
        owner_ref=owner,
        name="Buggy Calculator",
        files=buggy_project,
        runner_profile="unittest",
    )
    assert project_record.project_id.startswith("proj-")

    # Step 2: Create Coding Task against project_record.project_id
    brief = CodingBrief(
        task="Fix the add function in app/calculator.py so test_add_two passes.",
        source_hash=project_record.source_hash,
        editable_paths=["app/calculator.py"],
    )

    task = coding_store.create_task(
        owner_ref=owner,
        fixture_id=project_record.project_id,
        brief=brief,
        source_files=project_record.files,
        contract_hash=PROJECT_CONTRACT_HASH,
        idempotency_key="idemp-proj-e2e-1",
    )
    task_id = task["task_id"]

    # Step 3: Wire mock client that generates plan and fix
    fixed_code = (
        "def add(numbers: str) -> int:\n"
        "    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
        "    return sum(parts)\n"
    )

    plan_obj = CodingPlan(
        source_hash=brief.source_hash,
        brief_hash=brief.identity(),
        steps=["Parse comma-separated values into integers", "Sum integers and return total"],
        target_files=["app/calculator.py"],
        check_profile="project-unittest-v1",
    )
    plan_json = plan_obj.model_dump_json()

    edit_json = json.dumps({
        "schema_version": "coding-edit-v1",
        "source_hash": brief.source_hash,
        "plan_hash": plan_obj.identity(),
        "files": [
            {
                "path": "app/calculator.py",
                "content": fixed_code,
            }
        ],
        "explanation": "Parse comma-separated numbers and return sum.",
    })

    class ProjectMockClient(CompletionClient):
        def complete(self, **kwargs: Any) -> dict[str, Any]:
            prompt = kwargs.get("user_prompt", "")
            try:
                payload = json.loads(prompt)
            except Exception:
                payload = {}
            if "brief" in payload:
                content = plan_json
            else:
                content = edit_json

            return {
                "content": content,
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 80,
                    "total_tokens": 180,
                },
                "latency_ms": 50,
            }

    executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)
    engine = CodingEngine(
        client=ProjectMockClient(),
        model_id="mock-proj-model",
        executor=executor,
        synthetic=True,
    )

    worker = CodingWorker(coding_store, engine, worker_id="worker-proj-test")

    # Action 1: Enqueue planning and run
    coding_store.enqueue(owner, task_id, "plan-step", phase="plan")
    res1 = worker.run_once()
    assert res1 is not None and res1["state"] == "AWAITING_APPROVAL"

    task = coding_store.get_task(owner, task_id)
    assert task["state"] == "AWAITING_APPROVAL"
    plan_hash = CodingPlan.model_validate(task["plan"]).identity()

    # Action 2: Approve plan and enqueue run
    coding_store.approve_plan(owner, task_id, plan_hash)
    coding_store.enqueue(owner, task_id, "start-step", phase="run")

    # Action 3: BASELINE (fails because original code has bug) -> transitions to EDIT
    res2 = worker.run_once()
    assert res2 is not None and res2["stage"] == "EDIT"
    task = coding_store.get_task(owner, task_id)
    assert task["checkpoint"]["baseline"]["verdict"] == "REJECTED"

    # Action 4: EDIT (generates patch) -> transitions to CANDIDATE
    res3 = worker.run_once()
    assert res3 is not None and res3["stage"] == "CANDIDATE"

    # Action 5: CANDIDATE (tests patched code -> passes) -> transitions to FINAL
    res4 = worker.run_once()
    assert res4 is not None and res4["stage"] == "FINAL"

    # Action 6: FINAL (fresh independent check -> VERIFIED) -> REVIEW_READY
    res5 = worker.run_once()
    assert res5 is not None and res5["state"] == "REVIEW_READY"

    task = coding_store.get_task(owner, task_id)
    assert task["state"] == "REVIEW_READY"
    assert task["next_stage"] == "FINAL"
    assert "diff" in task["result"]
    assert "+    return sum(parts)" in task["result"]["diff"]
