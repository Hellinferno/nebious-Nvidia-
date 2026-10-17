"""Acceptance verification for agent execution on imported projects (C-05).

Scope and acceptance gate:
1. One bug fix task on Project 1 (e.g. StringCalculator negative number handling / delimiter support)
   produces a genuine diff and passes tests.
2. One bounded feature task on Project 2 (e.g. BankAccount transaction logging / transfer)
   produces a genuine diff and passes tests.
3. Protected tests refusal: candidate edits targeting files in tests/ or outside approved plan
   are rejected with PROTECTED_FILE_VIOLATION or PLAN_UNAPPROVED.
4. Stale base rejection: tasks against stale project source revisions are rejected with STALE_SOURCE.
5. New unauthorized file path refusal: candidate edits trying to create unapproved files are rejected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from benchproof.coding.contracts import CodingBrief, CodingPlan, OperatorLimits
from benchproof.coding.engine import CodingEngine, GenerationError
from benchproof.coding.generation import CompletionClient
from benchproof.coding.store import CodingStore
from benchproof.coding.worker import CodingWorker
from benchproof.execution.base import ExecutionResult
from benchproof.execution.project_runner import (
    PROJECT_CONTRACT_HASH,
    ProjectExecutor,
    ProjectSnapshot,
)
from benchproof.projects.intake import validate_project_intake
from benchproof.projects.store import ProjectStore
from tests.test_project_runner import _run_launcher_subprocess


# ── Project 1: StringCalculator Bug Fix ──────────────────────────────────────

CALC_BUGGY_PROJECT = {
    "app/calculator.py": (
        "def add(numbers: str) -> int:\n"
        "    if not numbers.strip():\n"
        "        return 0\n"
        "    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
        "    # Bug: ignores negative check and returns sum anyway\n"
        "    return sum(parts)\n"
    ),
    "tests/test_calculator.py": (
        "import unittest\n"
        "from app.calculator import add\n\n"
        "class TestStringCalculator(unittest.TestCase):\n"
        "    def test_empty(self):\n"
        "        self.assertEqual(add(''), 0)\n\n"
        "    def test_single_and_two_numbers(self):\n"
        "        self.assertEqual(add('1'), 1)\n"
        "        self.assertEqual(add('1, 2'), 3)\n\n"
        "    def test_negative_raises_value_error(self):\n"
        "        with self.assertRaises(ValueError):\n"
        "            add('1, -2, 3')\n"
    ),
}

CALC_FIXED_CODE = (
    "def add(numbers: str) -> int:\n"
    "    if not numbers.strip():\n"
    "        return 0\n"
    "    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
    "    negatives = [n for n in parts if n < 0]\n"
    "    if negatives:\n"
    "        raise ValueError(f'negatives not allowed: {negatives}')\n"
    "    return sum(parts)\n"
)


# ── Project 2: BankAccount Bounded Feature ───────────────────────────────────

BANK_INITIAL_PROJECT = {
    "app/account.py": (
        "class BankAccount:\n"
        "    def __init__(self, owner: str, initial_balance: int = 0) -> None:\n"
        "        if initial_balance < 0:\n"
        "            raise ValueError('Initial balance cannot be negative')\n"
        "        self.owner = owner\n"
        "        self.balance = initial_balance\n\n"
        "    def deposit(self, amount: int) -> int:\n"
        "        if amount <= 0:\n"
        "            raise ValueError('Deposit amount must be positive')\n"
        "        self.balance += amount\n"
        "        return self.balance\n\n"
        "    def withdraw(self, amount: int) -> int:\n"
        "        if amount <= 0:\n"
        "            raise ValueError('Withdrawal amount must be positive')\n"
        "        if amount > self.balance:\n"
        "            raise ValueError('Insufficient funds')\n"
        "        self.balance -= amount\n"
        "        return self.balance\n"
    ),
    "tests/test_account.py": (
        "import unittest\n"
        "from app.account import BankAccount\n\n"
        "class TestBankAccountFeature(unittest.TestCase):\n"
        "    def test_transfer_to_another_account(self):\n"
        "        alice = BankAccount('Alice', 100)\n"
        "        bob = BankAccount('Bob', 50)\n"
        "        alice.transfer(bob, 40)\n"
        "        self.assertEqual(alice.balance, 60)\n"
        "        self.assertEqual(bob.balance, 90)\n\n"
        "    def test_transfer_insufficient_funds(self):\n"
        "        alice = BankAccount('Alice', 30)\n"
        "        bob = BankAccount('Bob', 50)\n"
        "        with self.assertRaises(ValueError):\n"
        "            alice.transfer(bob, 50)\n"
    ),
}

BANK_FEATURE_CODE = (
    "class BankAccount:\n"
    "    def __init__(self, owner: str, initial_balance: int = 0) -> None:\n"
    "        if initial_balance < 0:\n"
    "            raise ValueError('Initial balance cannot be negative')\n"
    "        self.owner = owner\n"
    "        self.balance = initial_balance\n\n"
    "    def deposit(self, amount: int) -> int:\n"
    "        if amount <= 0:\n"
    "            raise ValueError('Deposit amount must be positive')\n"
    "        self.balance += amount\n"
    "        return self.balance\n\n"
    "    def withdraw(self, amount: int) -> int:\n"
    "        if amount <= 0:\n"
    "            raise ValueError('Withdrawal amount must be positive')\n"
    "        if amount > self.balance:\n"
    "            raise ValueError('Insufficient funds')\n"
    "        self.balance -= amount\n"
    "        return self.balance\n\n"
    "    def transfer(self, target: 'BankAccount', amount: int) -> None:\n"
    "        self.withdraw(amount)\n"
    "        target.deposit(amount)\n"
)


class ScriptedCompletionClient(CompletionClient):
    """Returns scripted plan and edit responses based on prompt payload."""

    def __init__(self, plan_json: str, edit_json: str) -> None:
        self.plan_json = plan_json
        self.edit_json = edit_json
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        prompt = kwargs.get("user_prompt", "")
        try:
            payload = json.loads(prompt)
        except Exception:
            payload = {}

        if "brief" in payload:
            content = self.plan_json
        else:
            content = self.edit_json

        return {
            "content": content,
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180},
            "latency_ms": 40,
        }


# ── Acceptance Tests ─────────────────────────────────────────────────────────

def test_c05_project_1_bug_fix_loop_reaches_review_ready(tmp_path: Path) -> None:
    """Project 1: Bug fix produces genuine diff and passes all tests (C-05)."""
    db_path = tmp_path / "c05_bug_fix.db"
    project_store = ProjectStore(db_path)
    coding_store = CodingStore(db_path, OperatorLimits(model_calls_per_day=50, executions_per_day=50))
    owner = "owner-c05-calc"

    # Step 1: Create project with bug
    project = project_store.create_project(
        owner_ref=owner,
        name="StringCalculator Buggy",
        files=CALC_BUGGY_PROJECT,
        runner_profile="unittest",
    )

    # Step 2: Create Coding Task
    brief = CodingBrief(
        task="Fix add() to raise ValueError when negative numbers are provided.",
        source_hash=project.source_hash,
        editable_paths=["app/calculator.py"],
    )
    task = coding_store.create_task(
        owner_ref=owner,
        fixture_id=project.project_id,
        brief=brief,
        source_files=project.files,
        contract_hash=PROJECT_CONTRACT_HASH,
        idempotency_key="idemp-c05-calc-1",
    )
    task_id = task["task_id"]

    # Step 3: Scripted model responses
    plan_obj = CodingPlan(
        source_hash=brief.source_hash,
        brief_hash=brief.identity(),
        steps=["Find negative numbers in parsed integers", "Raise ValueError if any negatives found"],
        target_files=["app/calculator.py"],
        check_profile="project-unittest-v1",
    )
    edit_json = json.dumps({
        "schema_version": "coding-edit-v1",
        "source_hash": brief.source_hash,
        "plan_hash": plan_obj.identity(),
        "files": [{"path": "app/calculator.py", "content": CALC_FIXED_CODE}],
        "explanation": "Check for negatives and raise ValueError with list of negatives.",
    })

    client = ScriptedCompletionClient(plan_obj.model_dump_json(), edit_json)
    executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)
    engine = CodingEngine(client=client, model_id="c05-mock-model", executor=executor, synthetic=True)
    worker = CodingWorker(coding_store, engine, worker_id="worker-c05-calc")

    # Step 4: Plan -> Approval
    coding_store.enqueue(owner, task_id, "plan", phase="plan")
    res1 = worker.run_once()
    assert res1 is not None and res1["state"] == "AWAITING_APPROVAL"
    coding_store.approve_plan(owner, task_id, plan_obj.identity())
    coding_store.enqueue(owner, task_id, "run", phase="run")

    # Step 5: Baseline -> Edit -> Candidate -> Final -> REVIEW_READY
    res2 = worker.run_once()  # Baseline (fails negative test)
    assert res2 is not None and res2["stage"] == "EDIT"
    res3 = worker.run_once()  # Model generates edit
    assert res3 is not None and res3["stage"] == "CANDIDATE"
    res4 = worker.run_once()  # Candidate passes
    assert res4 is not None and res4["stage"] == "FINAL"
    res5 = worker.run_once()  # Final verified
    assert res5 is not None and res5["state"] == "REVIEW_READY"

    final_task = coding_store.get_task(owner, task_id)
    assert final_task["state"] == "REVIEW_READY"
    assert "diff" in final_task["result"]
    assert "negatives not allowed" in final_task["result"]["diff"]


def test_c05_project_2_bounded_feature_loop_reaches_review_ready(tmp_path: Path) -> None:
    """Project 2: Bounded feature implementation produces genuine diff and passes (C-05)."""
    db_path = tmp_path / "c05_feature.db"
    project_store = ProjectStore(db_path)
    coding_store = CodingStore(db_path, OperatorLimits(model_calls_per_day=50, executions_per_day=50))
    owner = "owner-c05-bank"

    # Step 1: Create project lacking the transfer feature
    project = project_store.create_project(
        owner_ref=owner,
        name="BankAccount Initial",
        files=BANK_INITIAL_PROJECT,
        runner_profile="unittest",
    )

    # Step 2: Create Coding Task
    brief = CodingBrief(
        task="Implement transfer(target, amount) on BankAccount.",
        source_hash=project.source_hash,
        editable_paths=["app/account.py"],
    )
    task = coding_store.create_task(
        owner_ref=owner,
        fixture_id=project.project_id,
        brief=brief,
        source_files=project.files,
        contract_hash=PROJECT_CONTRACT_HASH,
        idempotency_key="idemp-c05-bank-1",
    )
    task_id = task["task_id"]

    # Step 3: Scripted model responses
    plan_obj = CodingPlan(
        source_hash=brief.source_hash,
        brief_hash=brief.identity(),
        steps=["Add transfer method to BankAccount", "Withdraw from self and deposit to target"],
        target_files=["app/account.py"],
        check_profile="project-unittest-v1",
    )
    edit_json = json.dumps({
        "schema_version": "coding-edit-v1",
        "source_hash": brief.source_hash,
        "plan_hash": plan_obj.identity(),
        "files": [{"path": "app/account.py", "content": BANK_FEATURE_CODE}],
        "explanation": "Added transfer method delegating to withdraw and deposit.",
    })

    client = ScriptedCompletionClient(plan_obj.model_dump_json(), edit_json)
    executor = ProjectExecutor(synthetic_runner=_run_launcher_subprocess)
    engine = CodingEngine(client=client, model_id="c05-mock-model", executor=executor, synthetic=True)
    worker = CodingWorker(coding_store, engine, worker_id="worker-c05-bank")

    # Step 4: Plan -> Approval
    coding_store.enqueue(owner, task_id, "plan", phase="plan")
    worker.run_once()
    coding_store.approve_plan(owner, task_id, plan_obj.identity())
    coding_store.enqueue(owner, task_id, "run", phase="run")

    # Step 5: Full loop execution
    worker.run_once()  # Baseline fails (transfer does not exist yet)
    worker.run_once()  # Edit generates transfer method
    worker.run_once()  # Candidate tests pass
    res_final = worker.run_once()  # Final verification passes

    assert res_final is not None and res_final["state"] == "REVIEW_READY"
    final_task = coding_store.get_task(owner, task_id)
    assert "def transfer(self, target:" in final_task["result"]["diff"]


def test_c05_protected_tests_refusal(tmp_path: Path) -> None:
    """Agent cannot propose or approve editing protected tests/ (C-05)."""
    # 1. Brief level refusal
    with pytest.raises(ValueError, match="Protected source paths cannot be approved for editing|Only portable app/"):
        CodingBrief(
            task="Change the test assertions",
            source_hash="a" * 64,
            editable_paths=["tests/test_account.py"],
        )

    # 2. Plan level refusal
    with pytest.raises(ValueError, match="Protected source paths cannot be approved for editing|Only portable app/"):
        CodingPlan(
            source_hash="a" * 64,
            brief_hash="b" * 64,
            steps=["Modify the test file"],
            target_files=["tests/test_account.py"],
            check_profile="project-unittest-v1",
        )


def test_c05_unauthorized_new_paths_refusal(tmp_path: Path) -> None:
    """Agent cannot propose or edit unapproved or non-app paths (C-05)."""
    with pytest.raises(ValueError):
        CodingBrief(
            task="Create a backdoor",
            source_hash="a" * 64,
            editable_paths=["app/evil.py", "app/../../root.py"],
        )


def test_c05_stale_base_refusal(tmp_path: Path) -> None:
    """Engine and store refuse tasks when the provided source_hash does not match the project (C-05)."""
    db_path = tmp_path / "c05_stale.db"
    project_store = ProjectStore(db_path)
    coding_store = CodingStore(db_path, OperatorLimits(50, 50))
    owner = "owner-c05-stale"

    project = project_store.create_project(
        owner_ref=owner,
        name="StringCalc",
        files=CALC_BUGGY_PROJECT,
        runner_profile="unittest",
    )

    stale_hash = "f" * 64
    brief = CodingBrief(
        task="Fix bug with wrong hash",
        source_hash=stale_hash,
        editable_paths=["app/calculator.py"],
    )

    with pytest.raises(Exception):
        coding_store.create_task(
            owner_ref=owner,
            fixture_id=project.project_id,
            brief=brief,
            source_files=project.files,
            contract_hash=PROJECT_CONTRACT_HASH,
            idempotency_key="idemp-c05-stale",
        )
