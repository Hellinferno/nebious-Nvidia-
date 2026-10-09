"""Intake validation and safe snapshotting (B-07).

Enforces:
- File path allowlists (only files under candidate directory, e.g. app/).
- Path traversal prevention (no '..', absolute paths, backslashes outside posix).
- Exclusion of trusted evaluator assets (expected.json, reference/).
- Size and count limits (per-file and total byte limits).
- Base hash verification against known fixture manifests.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 64 * 1024  # 64 KB per file
MAX_TOTAL_BYTES = 512 * 1024  # 512 KB total
MAX_FILE_COUNT = 30
DISALLOWED_NAMES = {"expected.json", ".git", ".env"}
DISALLOWED_DIRS = {"reference", "__pycache__", ".pytest_cache"}


class IntakeError(Exception):
    """Raised when source intake violates safety or limits."""


def validate_relative_path(rel_path: str, allowed_prefix: str = "app/") -> str:
    """Normalize and validate a relative path within candidate scope."""
    # Normalize slashes
    norm = rel_path.replace("\\", "/").strip()
    if not norm:
        raise IntakeError("Empty relative path")
    
    # Check for path traversal
    parts = norm.split("/")
    if any(p == ".." or p == "." for p in parts if p):
        raise IntakeError(f"Path traversal forbidden: {rel_path}")
    if norm.startswith("/"):
        raise IntakeError(f"Absolute path forbidden: {rel_path}")
    
    # Check allowed prefix
    if not norm.startswith(allowed_prefix):
        raise IntakeError(f"Path outside editable scope ({allowed_prefix}): {rel_path}")
    
    # Check disallowed file/directory names
    for p in parts:
        if p in DISALLOWED_NAMES or p in DISALLOWED_DIRS:
            raise IntakeError(f"Disallowed name in path: {p}")
            
    return norm


def inspect_source_tree(app_dir: Path) -> dict[str, Any]:
    """Inspect and validate candidate files, enforcing size and count limits."""
    if not app_dir.exists() or not app_dir.is_dir():
        raise IntakeError(f"Candidate directory does not exist: {app_dir}")

    files: list[Path] = []
    total_bytes = 0
    manifest: dict[str, str] = {}

    for root, dirs, filenames in os.walk(app_dir):
        # Filter out disallowed dirs in-place
        dirs[:] = [d for d in dirs if d not in DISALLOWED_DIRS]
        for fname in filenames:
            if fname in DISALLOWED_NAMES or fname.endswith(".pyc"):
                continue
            fpath = Path(root) / fname
            rel = fpath.relative_to(app_dir.parent).as_posix()
            validate_relative_path(rel)
            
            size = fpath.stat().st_size
            if size > MAX_FILE_BYTES:
                raise IntakeError(f"File exceeds maximum size ({size} > {MAX_FILE_BYTES}): {rel}")
            total_bytes += size
            if total_bytes > MAX_TOTAL_BYTES:
                raise IntakeError(f"Total source exceeds maximum size ({total_bytes} > {MAX_TOTAL_BYTES})")
            
            files.append(fpath)
            manifest[rel] = hashlib.sha256(fpath.read_bytes()).hexdigest()

    if len(files) > MAX_FILE_COUNT:
        raise IntakeError(f"File count exceeds maximum ({len(files)} > {MAX_FILE_COUNT})")

    canonical_manifest = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    source_hash = hashlib.sha256(canonical_manifest.encode("utf-8")).hexdigest()

    return {
        "source_hash": source_hash,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "manifest": manifest,
    }


def verify_base_source_hash(actual_hash: str, expected_hash: str) -> None:
    """Verify that current candidate base hash matches expected fixture base."""
    if actual_hash != expected_hash:
        raise IntakeError(
            f"STALE_SOURCE: Base source hash mismatch: actual {actual_hash} != expected {expected_hash}"
        )
