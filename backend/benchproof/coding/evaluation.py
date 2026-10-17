"""Frozen evaluation suite and benchmark harness for coding tasks (C-09).

Defines six versioned tasks (three bugs, two bounded features, one correct/no-change),
frozen task assets, deterministic expected behavior oracles, and an evaluation
runner that measures exact token usage, model calls, execution count, duration,
and correctness without holdout tuning or host pollution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any, Callable, Literal

from benchproof.coding.contracts import CodingBrief, CodingPlan, OperatorLimits
from benchproof.coding.engine import CodingEngine
from benchproof.coding.store import CodingStore
from benchproof.coding.worker import CodingWorker
from benchproof.execution.project_runner import PROJECT_CONTRACT_HASH, ProjectExecutor
from benchproof.projects.intake import validate_project_intake
from benchproof.projects.store import ProjectStore


# ── 1. The Six Frozen Evaluation Tasks ───────────────────────────────────────

@dataclass(frozen=True)
class CodingEvalTask:
    task_id: str
    name: str
    category: Literal["bug_fix", "bounded_feature", "no_change"]
    brief_text: str
    editable_paths: list[str]
    initial_files: dict[str, str]
    gold_patch: str
    gold_files: dict[str, str]

    @property
    def source_hash(self) -> str:
        manifest, _ = validate_project_intake(self.initial_files, runner_profile="unittest")
        return manifest.source_hash


# Task 1 (Bug 1): String Calculator negatives validation
TASK_01_CALC = CodingEvalTask(
    task_id="TASK-01-CALC-NEG",
    name="String Calculator Negative Numbers",
    category="bug_fix",
    brief_text="Disallow negative numbers in add(); raise ValueError with list of negative numbers found.",
    editable_paths=["app/calculator.py"],
    initial_files={
        "app/calculator.py": (
            "def add(numbers: str) -> int:\n"
            "    if not numbers.strip():\n"
            "        return 0\n"
            "    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
            "    return sum(parts)\n"
        ),
        "tests/test_calculator.py": (
            "import unittest\n"
            "from app.calculator import add\n\n"
            "class TestStringCalculator(unittest.TestCase):\n"
            "    def test_empty(self):\n"
            "        self.assertEqual(add(''), 0)\n"
            "    def test_single_and_two_numbers(self):\n"
            "        self.assertEqual(add('1'), 1)\n"
            "        self.assertEqual(add('1, 2'), 3)\n"
            "    def test_negative_raises_value_error(self):\n"
            "        with self.assertRaises(ValueError):\n"
            "            add('1, -2, 3')\n"
        ),
    },
    gold_patch=(
        "--- a/app/calculator.py\n"
        "+++ b/app/calculator.py\n"
        "@@ -3,3 +3,5 @@\n"
        "     parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
        "+    negatives = [n for n in parts if n < 0]\n"
        "+    if negatives:\n"
        "+        raise ValueError(f'negatives not allowed: {negatives}')\n"
        "     return sum(parts)\n"
    ),
    gold_files={
        "app/calculator.py": (
            "def add(numbers: str) -> int:\n"
            "    if not numbers.strip():\n"
            "        return 0\n"
            "    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]\n"
            "    negatives = [n for n in parts if n < 0]\n"
            "    if negatives:\n"
            "        raise ValueError(f'negatives not allowed: {negatives}')\n"
            "    return sum(parts)\n"
        ),
        "tests/test_calculator.py": (
            "import unittest\n"
            "from app.calculator import add\n\n"
            "class TestStringCalculator(unittest.TestCase):\n"
            "    def test_empty(self):\n"
            "        self.assertEqual(add(''), 0)\n"
            "    def test_single_and_two_numbers(self):\n"
            "        self.assertEqual(add('1'), 1)\n"
            "        self.assertEqual(add('1, 2'), 3)\n"
            "    def test_negative_raises_value_error(self):\n"
            "        with self.assertRaises(ValueError):\n"
            "            add('1, -2, 3')\n"
        ),
    },
)

# Task 2 (Bug 2): Markdown Parser emphasis tags
TASK_02_MARKDOWN = CodingEvalTask(
    task_id="TASK-02-MD-EMPH",
    name="Markdown Parser Emphasis",
    category="bug_fix",
    brief_text="Fix markdown italic rendering: replace matched *text* with <em>text</em> without breaking bold **text**.",
    editable_paths=["app/parser.py"],
    initial_files={
        "app/parser.py": (
            "import re\n\n"
            "def parse_markdown(text: str) -> str:\n"
            "    # Broken: replaces all asterisks without word boundary matching\n"
            "    text = re.sub(r'\\*\\*(.*?)\\*\\*', r'<strong>\\1</strong>', text)\n"
            "    return text\n"
        ),
        "tests/test_parser.py": (
            "import unittest\n"
            "from app.parser import parse_markdown\n\n"
            "class TestMarkdownParser(unittest.TestCase):\n"
            "    def test_bold(self):\n"
            "        self.assertEqual(parse_markdown('**bold**'), '<strong>bold</strong>')\n"
            "    def test_italic(self):\n"
            "        self.assertEqual(parse_markdown('*italic*'), '<em>italic</em>')\n"
            "    def test_plain(self):\n"
            "        self.assertEqual(parse_markdown('plain'), 'plain')\n"
        ),
    },
    gold_patch=(
        "--- a/app/parser.py\n"
        "+++ b/app/parser.py\n"
        "@@ -4,3 +4,4 @@\n"
        "     text = re.sub(r'\\*\\*(.*?)\\*\\*', r'<strong>\\1</strong>', text)\n"
        "+    text = re.sub(r'(?<!\\*)\\*(?!\\*)(.*?)(?<!\\*)\\*(?!\\*)', r'<em>\\1</em>', text)\n"
        "     return text\n"
    ),
    gold_files={
        "app/parser.py": (
            "import re\n\n"
            "def parse_markdown(text: str) -> str:\n"
            "    text = re.sub(r'\\*\\*(.*?)\\*\\*', r'<strong>\\1</strong>', text)\n"
            "    text = re.sub(r'(?<!\\*)\\*(?!\\*)(.*?)(?<!\\*)\\*(?!\\*)', r'<em>\\1</em>', text)\n"
            "    return text\n"
        ),
        "tests/test_parser.py": (
            "import unittest\n"
            "from app.parser import parse_markdown\n\n"
            "class TestMarkdownParser(unittest.TestCase):\n"
            "    def test_bold(self):\n"
            "        self.assertEqual(parse_markdown('**bold**'), '<strong>bold</strong>')\n"
            "    def test_italic(self):\n"
            "        self.assertEqual(parse_markdown('*italic*'), '<em>italic</em>')\n"
            "    def test_plain(self):\n"
            "        self.assertEqual(parse_markdown('plain'), 'plain')\n"
        ),
    },
)

# Task 3 (Bug 3): Inventory stock underflow
TASK_03_INVENTORY = CodingEvalTask(
    task_id="TASK-03-STOCK-UNDERFLOW",
    name="Inventory Stock Underflow",
    category="bug_fix",
    brief_text="Prevent stock underflow in deduct_stock: raise ValueError('Insufficient stock') if requested qty exceeds available.",
    editable_paths=["app/inventory.py"],
    initial_files={
        "app/inventory.py": (
            "class Inventory:\n"
            "    def __init__(self) -> None:\n"
            "        self._stock: dict[str, int] = {}\n"
            "    def add_stock(self, item: str, qty: int) -> None:\n"
            "        self._stock[item] = self._stock.get(item, 0) + qty\n"
            "    def get_stock(self, item: str) -> int:\n"
            "        return self._stock.get(item, 0)\n"
            "    def deduct_stock(self, item: str, qty: int) -> None:\n"
            "        # Bug: allows stock to become negative\n"
            "        self._stock[item] = self._stock.get(item, 0) - qty\n"
        ),
        "tests/test_inventory.py": (
            "import unittest\n"
            "from app.inventory import Inventory\n\n"
            "class TestInventory(unittest.TestCase):\n"
            "    def test_add_and_get(self):\n"
            "        inv = Inventory()\n"
            "        inv.add_stock('apple', 10)\n"
            "        self.assertEqual(inv.get_stock('apple'), 10)\n"
            "    def test_deduct_normal(self):\n"
            "        inv = Inventory()\n"
            "        inv.add_stock('apple', 10)\n"
            "        inv.deduct_stock('apple', 4)\n"
            "        self.assertEqual(inv.get_stock('apple'), 6)\n"
            "    def test_deduct_underflow_raises(self):\n"
            "        inv = Inventory()\n"
            "        inv.add_stock('apple', 5)\n"
            "        with self.assertRaises(ValueError):\n"
            "            inv.deduct_stock('apple', 10)\n"
        ),
    },
    gold_patch=(
        "--- a/app/inventory.py\n"
        "+++ b/app/inventory.py\n"
        "@@ -7,2 +7,5 @@\n"
        "     def deduct_stock(self, item: str, qty: int) -> None:\n"
        "+        current = self._stock.get(item, 0)\n"
        "+        if qty > current:\n"
        "+            raise ValueError('Insufficient stock')\n"
        "         self._stock[item] = current - qty\n"
    ),
    gold_files={
        "app/inventory.py": (
            "class Inventory:\n"
            "    def __init__(self) -> None:\n"
            "        self._stock: dict[str, int] = {}\n"
            "    def add_stock(self, item: str, qty: int) -> None:\n"
            "        self._stock[item] = self._stock.get(item, 0) + qty\n"
            "    def get_stock(self, item: str) -> int:\n"
            "        return self._stock.get(item, 0)\n"
            "    def deduct_stock(self, item: str, qty: int) -> None:\n"
            "        current = self._stock.get(item, 0)\n"
            "        if qty > current:\n"
            "            raise ValueError('Insufficient stock')\n"
            "        self._stock[item] = current - qty\n"
        ),
        "tests/test_inventory.py": (
            "import unittest\n"
            "from app.inventory import Inventory\n\n"
            "class TestInventory(unittest.TestCase):\n"
            "    def test_add_and_get(self):\n"
            "        inv = Inventory()\n"
            "        inv.add_stock('apple', 10)\n"
            "        self.assertEqual(inv.get_stock('apple'), 10)\n"
            "    def test_deduct_normal(self):\n"
            "        inv = Inventory()\n"
            "        inv.add_stock('apple', 10)\n"
            "        inv.deduct_stock('apple', 4)\n"
            "        self.assertEqual(inv.get_stock('apple'), 6)\n"
            "    def test_deduct_underflow_raises(self):\n"
            "        inv = Inventory()\n"
            "        inv.add_stock('apple', 5)\n"
            "        with self.assertRaises(ValueError):\n"
            "            inv.deduct_stock('apple', 10)\n"
        ),
    },
)

# Task 4 (Bounded Feature 1): BankAccount transfer method
TASK_04_BANK = CodingEvalTask(
    task_id="TASK-04-BANK-TRANSFER",
    name="Bank Account Transfer Method",
    category="bounded_feature",
    brief_text="Add transfer(target, amount) to BankAccount: withdraw from self, deposit to target; raise ValueError if insufficient funds.",
    editable_paths=["app/account.py"],
    initial_files={
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
    },
    gold_patch=(
        "--- a/app/account.py\n"
        "+++ b/app/account.py\n"
        "@@ -17,0 +18,3 @@\n"
        "+    def transfer(self, target: 'BankAccount', amount: int) -> None:\n"
        "+        self.withdraw(amount)\n"
        "+        target.deposit(amount)\n"
    ),
    gold_files={
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
            "        return self.balance\n\n"
            "    def transfer(self, target: 'BankAccount', amount: int) -> None:\n"
            "        self.withdraw(amount)\n"
            "        target.deposit(amount)\n"
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
    },
)

# Task 5 (Bounded Feature 2): RateLimiter reset_key method
TASK_05_RATELIMIT = CodingEvalTask(
    task_id="TASK-05-RATE-RESET",
    name="Rate Limiter Reset Key Method",
    category="bounded_feature",
    brief_text="Add reset_key(key) method to RateLimiter that clears timestamps for the given key and returns count of cleared records.",
    editable_paths=["app/limiter.py"],
    initial_files={
        "app/limiter.py": (
            "class RateLimiter:\n"
            "    def __init__(self, max_requests: int = 5) -> None:\n"
            "        self.max_requests = max_requests\n"
            "        self.calls: dict[str, list[float]] = {}\n\n"
            "    def allow(self, key: str, timestamp: float) -> bool:\n"
            "        history = self.calls.setdefault(key, [])\n"
            "        if len(history) >= self.max_requests:\n"
            "            return False\n"
            "        history.append(timestamp)\n"
            "        return True\n"
        ),
        "tests/test_limiter.py": (
            "import unittest\n"
            "from app.limiter import RateLimiter\n\n"
            "class TestRateLimiter(unittest.TestCase):\n"
            "    def test_allow_within_limit(self):\n"
            "        lim = RateLimiter(2)\n"
            "        self.assertTrue(lim.allow('user1', 1.0))\n"
            "        self.assertTrue(lim.allow('user1', 2.0))\n"
            "        self.assertFalse(lim.allow('user1', 3.0))\n\n"
            "    def test_reset_key(self):\n"
            "        lim = RateLimiter(2)\n"
            "        lim.allow('user1', 1.0)\n"
            "        lim.allow('user1', 2.0)\n"
            "        cleared = lim.reset_key('user1')\n"
            "        self.assertEqual(cleared, 2)\n"
            "        self.assertTrue(lim.allow('user1', 3.0))\n"
        ),
    },
    gold_patch=(
        "--- a/app/limiter.py\n"
        "+++ b/app/limiter.py\n"
        "@@ -10,0 +11,4 @@\n"
        "+    def reset_key(self, key: str) -> int:\n"
        "+        history = self.calls.pop(key, [])\n"
        "+        return len(history)\n"
    ),
    gold_files={
        "app/limiter.py": (
            "class RateLimiter:\n"
            "    def __init__(self, max_requests: int = 5) -> None:\n"
            "        self.max_requests = max_requests\n"
            "        self.calls: dict[str, list[float]] = {}\n\n"
            "    def allow(self, key: str, timestamp: float) -> bool:\n"
            "        history = self.calls.setdefault(key, [])\n"
            "        if len(history) >= self.max_requests:\n"
            "            return False\n"
            "        history.append(timestamp)\n"
            "        return True\n\n"
            "    def reset_key(self, key: str) -> int:\n"
            "        history = self.calls.pop(key, [])\n"
            "        return len(history)\n"
        ),
        "tests/test_limiter.py": (
            "import unittest\n"
            "from app.limiter import RateLimiter\n\n"
            "class TestRateLimiter(unittest.TestCase):\n"
            "    def test_allow_within_limit(self):\n"
            "        lim = RateLimiter(2)\n"
            "        self.assertTrue(lim.allow('user1', 1.0))\n"
            "        self.assertTrue(lim.allow('user1', 2.0))\n"
            "        self.assertFalse(lim.allow('user1', 3.0))\n\n"
            "    def test_reset_key(self):\n"
            "        lim = RateLimiter(2)\n"
            "        lim.allow('user1', 1.0)\n"
            "        lim.allow('user1', 2.0)\n"
            "        cleared = lim.reset_key('user1')\n"
            "        self.assertEqual(cleared, 2)\n"
            "        self.assertTrue(lim.allow('user1', 3.0))\n"
        ),
    },
)

# Task 6 (No-Change Project): URL Normalizer (all tests pass, no edits needed)
TASK_06_URL_CLEAN = CodingEvalTask(
    task_id="TASK-06-URL-CLEAN",
    name="URL Normalizer Clean Baseline",
    category="no_change",
    brief_text="Verify URL normalizer handles query parameter ordering and scheme lowercasing. All tests should pass without edits.",
    editable_paths=["app/normalizer.py"],
    initial_files={
        "app/normalizer.py": (
            "from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode\n\n"
            "def normalize_url(url: str) -> str:\n"
            "    parts = urlparse(url.strip())\n"
            "    scheme = parts.scheme.lower()\n"
            "    netloc = parts.netloc.lower()\n"
            "    path = parts.path or '/'\n"
            "    query = urlencode(sorted(parse_qsl(parts.query)))\n"
            "    return urlunparse((scheme, netloc, path, '', query, ''))\n"
        ),
        "tests/test_normalizer.py": (
            "import unittest\n"
            "from app.normalizer import normalize_url\n\n"
            "class TestUrlNormalizer(unittest.TestCase):\n"
            "    def test_normalize_scheme_and_netloc(self):\n"
            "        self.assertEqual(normalize_url('HTTP://EXAMPLE.COM'), 'http://example.com/')\n"
            "    def test_normalize_query_params(self):\n"
            "        self.assertEqual(normalize_url('http://example.com?b=2&a=1'), 'http://example.com/?a=1&b=2')\n"
        ),
    },
    gold_patch="",  # No changes expected
    gold_files={
        "app/normalizer.py": (
            "from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode\n\n"
            "def normalize_url(url: str) -> str:\n"
            "    parts = urlparse(url.strip())\n"
            "    scheme = parts.scheme.lower()\n"
            "    netloc = parts.netloc.lower()\n"
            "    path = parts.path or '/'\n"
            "    query = urlencode(sorted(parse_qsl(parts.query)))\n"
            "    return urlunparse((scheme, netloc, path, '', query, ''))\n"
        ),
        "tests/test_normalizer.py": (
            "import unittest\n"
            "from app.normalizer import normalize_url\n\n"
            "class TestUrlNormalizer(unittest.TestCase):\n"
            "    def test_normalize_scheme_and_netloc(self):\n"
            "        self.assertEqual(normalize_url('HTTP://EXAMPLE.COM'), 'http://example.com/')\n"
            "    def test_normalize_query_params(self):\n"
            "        self.assertEqual(normalize_url('http://example.com?b=2&a=1'), 'http://example.com/?a=1&b=2')\n"
        ),
    },
)

EVAL_SUITE_V1: tuple[CodingEvalTask, ...] = (
    TASK_01_CALC,
    TASK_02_MARKDOWN,
    TASK_03_INVENTORY,
    TASK_04_BANK,
    TASK_05_RATELIMIT,
    TASK_06_URL_CLEAN,
)


# ── 2. Evaluation Result Models ──────────────────────────────────────────────

@dataclass
class CodingEvalTaskResult:
    task_id: str
    category: str
    verdict: Literal["PASSED", "FAILED", "NOOP_PASSED", "ERROR"]
    checks_total: int
    checks_passed: int
    model_calls: int
    patch_attempts: int
    executions: int
    tokens_used: int
    duration_ms: int
    patch_diff: str = ""
    error_code: str | None = None


@dataclass
class CodingEvalReport:
    schema_version: Literal["coding-eval-report-v1"] = "coding-eval-report-v1"
    suite_id: str = "coding-eval-suite-v1"
    timestamp: float = field(default_factory=time.time)
    tasks_total: int = 0
    tasks_passed: int = 0
    tasks_failed: int = 0
    total_tokens: int = 0
    total_model_calls: int = 0
    total_executions: int = 0
    total_duration_ms: int = 0
    results: list[CodingEvalTaskResult] = field(default_factory=list)

    def summary_markdown(self) -> str:
        pct = (self.tasks_passed / self.tasks_total * 100) if self.tasks_total > 0 else 0.0
        lines = [
            f"# Coding Evaluation Report: {self.suite_id}",
            f"- **Pass Rate**: {self.tasks_passed}/{self.tasks_total} ({pct:.1f}%)",
            f"- **Total Model Calls**: {self.total_model_calls}",
            f"- **Total Executions**: {self.total_executions}",
            f"- **Total Tokens Recorded**: {self.total_tokens}",
            f"- **Total Duration**: {self.total_duration_ms / 1000.0:.2f}s",
            "",
            "| Task ID | Category | Verdict | Checks | Calls | Executions | Tokens | Time (ms) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for r in self.results:
            lines.append(
                f"| {r.task_id} | {r.category} | {r.verdict} | {r.checks_passed}/{r.checks_total} | "
                f"{r.model_calls} | {r.executions} | {r.tokens_used} | {r.duration_ms} |"
            )
        return "\n".join(lines)


# ── 3. Evaluation Harness ────────────────────────────────────────────────────

def evaluate_task(
    store: CodingStore,
    proj_store: ProjectStore,
    task_def: CodingEvalTask,
    *,
    client: Any,
    executor: ProjectExecutor,
    owner_ref: str = "eval-owner",
) -> CodingEvalTaskResult:
    """Runs a single evaluation task through the engine and worker to completion."""
    start_time = time.monotonic()

    # 1. Register project
    proj = proj_store.create_project(
        owner_ref=owner_ref,
        name=task_def.name,
        files=task_def.initial_files,
    )

    # 2. Create coding brief and task
    brief = CodingBrief(
        task=task_def.brief_text,
        source_hash=proj.source_hash,
        editable_paths=task_def.editable_paths,
    )
    task_record = store.create_task(
        owner_ref=owner_ref,
        fixture_id=proj.project_id,
        brief=brief,
        source_files=proj.files,
        contract_hash=PROJECT_CONTRACT_HASH,
        idempotency_key=f"eval-{task_def.task_id}-{time.time()}",
    )
    task_id = task_record["task_id"]

    # 3. Setup Engine and Worker
    engine = CodingEngine(
        client=client,
        model_id="eval-model",
        executor=executor,
        synthetic=True,
    )
    worker = CodingWorker(
        store,
        engine,
        worker_id=f"eval-worker-{task_def.task_id.lower()}",
        lease_seconds=120,
    )

    # 4. Handle no-change tasks specially
    if task_def.category == "no_change":
        # Baseline execution directly verifies all tests pass
        report = executor.run(
            task_def.initial_files,
            operation_id=f"eval-noop-{task_def.task_id}",
            runner_profile="unittest",
        )
        checks = report.get("checks", [])
        checks_total = len(checks)
        checks_passed = sum(1 for c in checks if c.get("passed"))
        passed = report.get("verdict") == "VERIFIED" or report.get("passed", False)
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return CodingEvalTaskResult(
            task_id=task_def.task_id,
            category=task_def.category,
            verdict="NOOP_PASSED" if passed else "FAILED",
            checks_total=checks_total,
            checks_passed=checks_passed,
            model_calls=0,
            patch_attempts=0,
            executions=1,
            tokens_used=0,
            duration_ms=duration_ms,
        )

    # 5. Enqueue Plan
    store.enqueue(owner_ref, task_id, f"plan-{task_id}", phase="plan")
    res_plan = worker.run_once()
    if res_plan is None or res_plan.get("state") != "AWAITING_APPROVAL":
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return CodingEvalTaskResult(
            task_id=task_def.task_id,
            category=task_def.category,
            verdict="ERROR",
            checks_total=0,
            checks_passed=0,
            model_calls=1,
            patch_attempts=0,
            executions=0,
            tokens_used=0,
            duration_ms=duration_ms,
            error_code=res_plan.get("code") if res_plan else "PLAN_TIMEOUT",
        )

    # 6. Approve Plan
    task_state = store.get_task(owner_ref, task_id)
    plan_obj = CodingPlan.model_validate(task_state["plan"])
    store.approve_plan(owner_ref, task_id, plan_obj.identity())
    store.enqueue(owner_ref, task_id, f"run-{task_id}", phase="run")

    # 7. Drain worker execution loop (Baseline -> Edit -> Candidate -> Final)
    for _ in range(8):
        res = worker.run_once()
        if res is None:
            break
        if res.get("state") in {"REVIEW_READY", "BLOCKED", "FAILED"}:
            break

    # 8. Fetch final task state
    final_task = store.get_task(owner_ref, task_id)
    chk = final_task.get("checkpoint") or {}
    last_cand = chk.get("last_candidate") or chk.get("final") or {}
    patch_diff = (chk.get("patch") or {}).get("diff", "")

    duration_ms = int((time.monotonic() - start_time) * 1000)
    passed = last_cand.get("verdict") == "VERIFIED" or last_cand.get("passed", False)
    verdict: Literal["PASSED", "FAILED", "NOOP_PASSED", "ERROR"] = (
        "PASSED" if final_task["state"] == "REVIEW_READY" and passed
        else "FAILED"
    )

    checks = last_cand.get("checks", [])
    checks_total = last_cand.get("checks_total") or len(checks)
    checks_passed = last_cand.get("checks_passed") or sum(1 for c in checks if c.get("passed"))
    tokens_used = sum((a.get("usage") or {}).get("total_tokens", 0) for a in final_task.get("actions", []))

    return CodingEvalTaskResult(
        task_id=task_def.task_id,
        category=task_def.category,
        verdict=verdict,
        checks_total=checks_total,
        checks_passed=checks_passed,
        model_calls=final_task["counters"]["model_calls"],
        patch_attempts=final_task["counters"]["patch_attempts"],
        executions=final_task["counters"]["executions"],
        tokens_used=tokens_used,
        duration_ms=duration_ms,
        patch_diff=patch_diff,
    )


def run_eval_suite(
    store: CodingStore,
    proj_store: ProjectStore,
    tasks: tuple[CodingEvalTask, ...] = EVAL_SUITE_V1,
    *,
    client_factory: Callable[[CodingEvalTask], Any],
    executor: ProjectExecutor,
) -> CodingEvalReport:
    """Executes the full frozen evaluation suite and aggregates metrics."""
    report = CodingEvalReport(tasks_total=len(tasks))

    for task_def in tasks:
        client = client_factory(task_def)
        result = evaluate_task(
            store,
            proj_store,
            task_def,
            client=client,
            executor=executor,
            owner_ref=f"eval-owner-{task_def.task_id.lower()}",
        )
        report.results.append(result)
        if result.verdict in {"PASSED", "NOOP_PASSED"}:
            report.tasks_passed += 1
        else:
            report.tasks_failed += 1
        report.total_model_calls += result.model_calls
        report.total_executions += result.executions
        report.total_tokens += result.tokens_used
        report.total_duration_ms += result.duration_ms

    return report
