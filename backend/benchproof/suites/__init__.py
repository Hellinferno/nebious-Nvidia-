"""Frozen evaluation suites (B-18).

Held-out assets live under `backend/fixtures/heldout/`. Every suite has a
manifest under `manifests/`; `truth.lock.json` pins the SHA-256 of each
agent-visible source tree, every trusted truth file and every manifest so a
later measurement can prove the assets were not changed after the freeze.

Nothing here is reachable from the public API. Trusted truth is read only by
the evaluator-side scoring scripts.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

HELDOUT_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "heldout"
MANIFEST_DIR = HELDOUT_ROOT / "manifests"
LOCK_PATH = HELDOUT_ROOT / "truth.lock.json"
LOCK_SCHEMA = "benchproof/suite-lock-v1"

REPAIR_SUITE = "repair-r12-v1"
GATE_SUITE = "gate-v12-v1"
GRAPH_SUITE = "graph-g8-v1"
FRESHNESS_SUITE = "freshness-f6-v1"
TRAJECTORY_SUITE = "trajectory-w8-v1"
MUTANT_SUITE = "mutants-m12-v1"
SUITE_IDS: tuple[str, ...] = (
    REPAIR_SUITE,
    GATE_SUITE,
    GRAPH_SUITE,
    FRESHNESS_SUITE,
    TRAJECTORY_SUITE,
    MUTANT_SUITE,
)


class SuiteIntegrityError(RuntimeError):
    """Frozen assets differ from the committed lock."""


def repair_root() -> Path:
    return HELDOUT_ROOT / REPAIR_SUITE


def gate_root() -> Path:
    return HELDOUT_ROOT / GATE_SUITE


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """SHA-256 of a frozen text asset with CRLF normalized to LF.

    Every held-out asset is text (.py, .json, .diff). Git's autocrlf rewrites
    line endings per checkout, so a raw byte hash would make the lock fail on
    the first Linux clone; normalizing keeps the lock platform-independent
    while still detecting every content change.
    """
    return _sha256_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def tree_hash(root: Path, suffixes: tuple[str, ...] | None = None) -> str:
    """Canonical hash of a directory: sorted relative posix paths and LF-normalized byte hashes."""
    entries: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if suffixes and path.suffix not in suffixes:
            continue
        entries[path.relative_to(root).as_posix()] = sha256_file(path)
    raw = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(raw.encode("utf-8"))


def canonical_json_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_bytes(raw.encode("utf-8"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(suite_id: str) -> dict[str, Any]:
    path = MANIFEST_DIR / f"{suite_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"suite manifest missing: {suite_id}")
    return load_json(path)


def load_scope() -> dict[str, Any]:
    return load_json(MANIFEST_DIR / "scope.json")


def repair_case_ids() -> list[str]:
    return sorted(p.name for p in repair_root().iterdir() if (p / "fixture.json").exists())


def gate_candidate_ids() -> list[str]:
    candidates = load_json(gate_root() / "candidates.json")["candidates"]
    return [item["candidate_id"] for item in candidates]


# ── Lock computation and verification ────────────────────────────────────

def compute_lock_entries() -> dict[str, str]:
    """Hash every frozen asset. Keys are posix paths relative to the held-out root."""
    entries: dict[str, str] = {}
    for case_id in repair_case_ids():
        case_dir = repair_root() / case_id
        entries[f"{REPAIR_SUITE}/{case_id}/app"] = tree_hash(case_dir / "app", (".py",))
        entries[f"{REPAIR_SUITE}/{case_id}/fixture.json"] = sha256_file(case_dir / "fixture.json")
        entries[f"{REPAIR_SUITE}/{case_id}/expected.json"] = sha256_file(case_dir / "expected.json")
        if (case_dir / "reference").exists():
            entries[f"{REPAIR_SUITE}/{case_id}/reference"] = tree_hash(case_dir / "reference", (".py",))
    if gate_root().exists():
        for path in sorted(gate_root().rglob("*")):
            if path.is_file():
                entries[path.relative_to(HELDOUT_ROOT).as_posix()] = sha256_file(path)
    if MANIFEST_DIR.exists():
        for path in sorted(MANIFEST_DIR.glob("*.json")):
            entries[path.relative_to(HELDOUT_ROOT).as_posix()] = sha256_file(path)
    return entries


def lock_hash(entries: dict[str, str]) -> str:
    return canonical_json_hash(entries)


def load_lock() -> dict[str, Any]:
    if not LOCK_PATH.exists():
        raise FileNotFoundError("truth.lock.json has not been written; run scripts/freeze_suites.py")
    return load_json(LOCK_PATH)


def verify_lock() -> list[str]:
    """Return discrepancies between the committed lock and the current assets."""
    lock = load_lock()
    if lock.get("schema") != LOCK_SCHEMA:
        return [f"unexpected lock schema {lock.get('schema')!r}"]
    expected: dict[str, str] = lock.get("entries", {})
    actual = compute_lock_entries()
    problems: list[str] = []
    for key in sorted(set(expected) | set(actual)):
        if key not in actual:
            problems.append(f"missing asset: {key}")
        elif key not in expected:
            problems.append(f"unlocked asset added after freeze: {key}")
        elif expected[key] != actual[key]:
            problems.append(f"asset changed after freeze: {key}")
    if lock_hash(expected) != lock.get("lock_hash"):
        problems.append("lock_hash does not match its own entries")
    return problems


def require_frozen() -> dict[str, Any]:
    """Raise unless the held-out assets match the committed lock. Used before scoring."""
    problems = verify_lock()
    if problems:
        raise SuiteIntegrityError("; ".join(problems))
    return load_lock()


# ── Agent-visibility guard ───────────────────────────────────────────────

LEAK_WORDS = re.compile(r"\b(fault|faulty|defect|defects|bug|bugs|broken|wrong)\b")
LEAK_MARKERS: tuple[str, ...] = (
    "intended_failing",
    "expected.json",
    "reference/",
    "api-field-presence",
    "api-status-code",
    "amount-boundary",
    "caller-consistency",
    "idempotency-duplicate",
    "idempotency-conflict",
    "worker-caller-path",
    "c-api",
    "c-amount",
    "c-integrity",
    "api compatibility",
    "exact amount boundary",
    "cross-module caller",
    "tenant-scoped idempotency",
    "clean control",
)


def agent_visible_leaks(case_dir: Path) -> list[str]:
    """Scan agent-visible files of one held-out case for answer-bearing text."""
    leaks: list[str] = []
    manifest = load_json(case_dir / "fixture.json")
    texts: list[tuple[str, str]] = [
        ("fixture.json", " ".join(str(value) for value in manifest.values() if value is not None).lower())
    ]
    for path in sorted((case_dir / "app").rglob("*.py")):
        texts.append((path.relative_to(case_dir).as_posix(), path.read_text(encoding="utf-8").lower()))
    for name, text in texts:
        for marker in LEAK_MARKERS:
            if marker in text:
                leaks.append(f"{name} contains {marker!r}")
        for match in sorted(set(LEAK_WORDS.findall(text))):
            leaks.append(f"{name} contains {match!r}")
    return leaks
