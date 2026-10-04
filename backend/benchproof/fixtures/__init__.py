"""Development fixture registry — manifests, source hashing and public listing.

Only `app/` files are candidate-visible. `expected.json` and `reference/` are
trusted evaluator assets and must never be copied into a candidate tree.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

CANDIDATE_DIR = "app"
TRUSTED_FILES = {"expected.json"}
TRUSTED_DIRS = {"reference"}


def fixtures_root() -> Path:
    env = os.getenv("BENCHPROOF_FIXTURES_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "fixtures" / "development"


def fixture_dir(fixture_id: str) -> Path:
    if not fixture_id or "/" in fixture_id or "\\" in fixture_id or ".." in fixture_id:
        raise ValueError("INVALID_INPUT: unsafe fixture id")
    return fixtures_root() / fixture_id


def list_fixture_ids() -> list[str]:
    root = fixtures_root()
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "fixture.json").exists())


def load_manifest(fixture_id: str) -> dict[str, Any]:
    path = fixture_dir(fixture_id) / "fixture.json"
    if not path.exists():
        raise FileNotFoundError(f"fixture manifest missing: {fixture_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_expected(fixture_id: str) -> dict[str, Any]:
    """Trusted expected properties. Evaluator-only; never returned by public APIs."""
    path = fixture_dir(fixture_id) / "expected.json"
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_files(app_dir: Path) -> list[Path]:
    return sorted(p for p in app_dir.rglob("*.py") if "__pycache__" not in p.parts)


def source_manifest(app_dir: Path) -> dict[str, str]:
    """Relative path -> sha256 of file bytes, for every candidate-visible file."""
    out: dict[str, str] = {}
    for p in candidate_files(app_dir):
        rel = p.relative_to(app_dir.parent).as_posix()
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def source_hash_for_dir(app_dir: Path) -> str:
    manifest = source_manifest(app_dir)
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_hash(fixture_id: str) -> str:
    return source_hash_for_dir(fixture_dir(fixture_id) / CANDIDATE_DIR)


def public_example(fixture_id: str) -> dict[str, Any]:
    """Public manifest fields plus the current source hash. No trusted fields."""
    m = load_manifest(fixture_id)
    return {
        "id": m["fixture_id"],
        "suite": m.get("suite", ""),
        "family": m.get("family", ""),
        "constraint": m.get("constraint"),
        "defect": m.get("defect"),
        "visibility": m.get("visibility", "development"),
        "synthetic": bool(m.get("synthetic", True)),
        "candidate_editable_paths": m.get("candidate_editable_paths", [CANDIDATE_DIR + "/"]),
        "source_hash": source_hash(fixture_id),
    }


def list_public_examples() -> list[dict[str, Any]]:
    return [public_example(fid) for fid in list_fixture_ids()]


def assert_no_trusted_assets(app_dir: Path) -> None:
    """Raise if evaluator assets leaked into a candidate-visible tree."""
    for p in app_dir.rglob("*"):
        if p.name in TRUSTED_FILES or any(part in TRUSTED_DIRS for part in p.relative_to(app_dir).parts):
            raise RuntimeError(f"trusted asset present in candidate tree: {p}")
