"""Non-executing evidence bundle validator — verifies schema, hashes, and archive safety without executing any code."""

from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path
from typing import Any

from benchproof.bundle.exporter import (
    SAFE_FILENAME_PATTERN,
    SecurityExclusionError,
    scan_for_secrets,
)
from benchproof.domain import _canonical_hash

MANDATORY_BUNDLE_FILES = {
    "constraints.json",
    "state.json",
    "coverage.json",
    "decisions.json",
    "trajectory.jsonl",
    "candidate.diff",
    "source-manifest.json",
    "checks.json",
    "mutations.json",
    "environment.json",
    "usage.json",
    "report.md",
    "REPLAY.md",
}
MAX_ARCHIVE_ENTRIES = 32
MAX_ARCHIVE_ENTRY_BYTES = 1 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 4 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100


def validate_bundle_nonexecuting(bundle_zip_path: Path) -> dict[str, Any]:
    """Validate all artifact hashes and manifest structure without executing candidate code.

    Returns a dict with:
        valid: bool
        audit_id: str
        fixture_id: str
        gate_verdict: str
        total_files: int
        verified_files: int
        discrepancies: list[str]
        manifest_hash_valid: bool
        omissions: list[str]
    """
    if not bundle_zip_path.exists():
        return {
            "valid": False,
            "discrepancies": [f"Bundle archive not found at: {bundle_zip_path}"],
            "verified_files": 0,
            "total_files": 0,
        }

    discrepancies: list[str] = []

    try:
        with zipfile.ZipFile(bundle_zip_path, "r") as zf:
            entries = zf.infolist()
            names = [entry.filename for entry in entries]
            file_names = set(names)

            if len(entries) > MAX_ARCHIVE_ENTRIES:
                discrepancies.append(
                    f"Archive entry count exceeds limit: {len(entries)} > {MAX_ARCHIVE_ENTRIES}"
                )
            if len(file_names) != len(names):
                discrepancies.append("Duplicate archive entry names are forbidden")

            total_uncompressed = 0
            for entry in entries:
                total_uncompressed += entry.file_size
                mode = (entry.external_attr >> 16) & 0o170000
                if entry.is_dir() or mode == stat.S_IFLNK:
                    discrepancies.append(f"Non-regular archive entry forbidden: {entry.filename}")
                if entry.flag_bits & 0x1:
                    discrepancies.append(f"Encrypted archive entry forbidden: {entry.filename}")
                if entry.file_size > MAX_ARCHIVE_ENTRY_BYTES:
                    discrepancies.append(
                        f"Archive entry exceeds size limit: {entry.filename} ({entry.file_size} bytes)"
                    )
                if entry.file_size and entry.compress_size == 0:
                    discrepancies.append(f"Invalid zero-size compressed stream: {entry.filename}")
                elif entry.compress_size and entry.file_size / entry.compress_size > MAX_COMPRESSION_RATIO:
                    discrepancies.append(f"Archive compression ratio exceeds limit: {entry.filename}")
            if total_uncompressed > MAX_ARCHIVE_TOTAL_BYTES:
                discrepancies.append(
                    f"Archive uncompressed size exceeds limit: {total_uncompressed} > {MAX_ARCHIVE_TOTAL_BYTES}"
                )

            # 1. Archive safety checks (no zip-slip, traversal, or weird filenames)
            for name in file_names:
                if ".." in name or name.startswith(("/", "\\")):
                    discrepancies.append(f"Unsafe path traversal detected in archive entry: {name}")
                if not SAFE_FILENAME_PATTERN.match(name):
                    discrepancies.append(f"Invalid characters in archive entry filename: {name}")

            if discrepancies:
                return {
                    "valid": False,
                    "discrepancies": discrepancies,
                    "verified_files": 0,
                    "total_files": len(file_names),
                }

            # 2. Manifest presence
            if "manifest.json" not in file_names:
                discrepancies.append("manifest.json missing from bundle root")
                return {
                    "valid": False,
                    "discrepancies": discrepancies,
                    "verified_files": 0,
                    "total_files": len(file_names),
                }

            # 3. Read manifest
            try:
                manifest_bytes = zf.read("manifest.json")
                manifest_data = json.loads(manifest_bytes.decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile) as e:
                discrepancies.append(f"Failed to parse manifest.json: {e}")
                return {
                    "valid": False,
                    "discrepancies": discrepancies,
                    "verified_files": 0,
                    "total_files": len(file_names),
                }

            # 4. Validate manifest canonical hash
            recorded_manifest_hash = manifest_data.get("manifest_hash", "")
            payload = {k: v for k, v in manifest_data.items() if k != "manifest_hash"}
            computed_manifest_hash = _canonical_hash(payload)
            manifest_hash_valid = (recorded_manifest_hash == computed_manifest_hash)
            if not manifest_hash_valid:
                discrepancies.append(
                    f"manifest_hash mismatch: expected {recorded_manifest_hash}, computed {computed_manifest_hash}"
                )

            # 5. Check mandatory files
            artifact_hashes: dict[str, str] = manifest_data.get("artifact_hashes", {})
            for req in MANDATORY_BUNDLE_FILES:
                if req not in file_names:
                    discrepancies.append(f"Mandatory bundle file missing: {req}")
                if req not in artifact_hashes:
                    discrepancies.append(f"Mandatory bundle file unmanifested: {req}")

            # 6. Check for unmanifested extra files
            for fname in file_names:
                if fname != "manifest.json" and fname not in artifact_hashes:
                    discrepancies.append(f"Unmanifested extra file in bundle: {fname}")

            # 7. Non-executing cryptographic SHA-256 validation
            verified_count = 0
            for fname, expected_sha in artifact_hashes.items():
                if fname not in file_names:
                    discrepancies.append(f"Manifested file missing from archive: {fname}")
                    continue

                try:
                    content_bytes = zf.read(fname)
                    try:
                        scan_for_secrets(content_bytes.decode("utf-8"), fname)
                    except UnicodeDecodeError:
                        discrepancies.append(f"Bundle artifact is not UTF-8 text: {fname}")
                        continue
                    except SecurityExclusionError as exc:
                        discrepancies.append(str(exc))
                        continue
                    actual_sha = hashlib.sha256(content_bytes).hexdigest()
                    if actual_sha != expected_sha:
                        discrepancies.append(
                            f"Hash mismatch for {fname}: manifest={expected_sha}, computed={actual_sha}"
                        )
                    else:
                        verified_count += 1
                except (KeyError, OSError, zipfile.BadZipFile) as e:
                    discrepancies.append(f"Failed to read and hash {fname}: {e}")

            return {
                "valid": len(discrepancies) == 0,
                "audit_id": manifest_data.get("audit_id", ""),
                "fixture_id": manifest_data.get("fixture_id", ""),
                "gate_verdict": manifest_data.get("gate_verdict", ""),
                "total_files": len(artifact_hashes),
                "verified_files": verified_count,
                "discrepancies": discrepancies,
                "manifest_hash_valid": manifest_hash_valid,
                "omissions": manifest_data.get("omissions", []),
            }

    except zipfile.BadZipFile:
        return {
            "valid": False,
            "discrepancies": ["Corrupted or invalid ZIP archive"],
            "verified_files": 0,
            "total_files": 0,
        }
    except (OSError, AttributeError, TypeError) as e:
        return {
            "valid": False,
            "discrepancies": [f"Unexpected error validating bundle: {e}"],
            "verified_files": 0,
            "total_files": 0,
        }
