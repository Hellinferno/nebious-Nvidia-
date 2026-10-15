"""Restricted patch authoring and import (B-09).

Enforces strict provider-neutral patch validation:
- Base hash verification (rejects wrong-base/stale requests)
- Path allowlist (only app/* permitted)
- Path traversal and protected-file denial (no .., expected.json, evaluator, contracts)
- Line and byte ceilings (rejects oversized diffs)
- Clean patch application to create fresh candidate snapshots
"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from benchproof.fixtures import source_hash_for_dir

MAX_DIFF_LINES = 100
MAX_DIFF_BYTES = 10_000
MAX_TARGET_FILES = 3
FORBIDDEN_DIFF_METADATA = (
    "diff --git ",
    "new file mode ",
    "deleted file mode ",
    "old mode ",
    "new mode ",
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
    "GIT binary patch",
    "Binary files ",
)
PROTECTED_PATTERNS = [
    "expected.json",
    "fixture.json",
    "reference",
    "runner",
    "evaluator",
    "contracts",
    "benchproof",
    "tests",
]


class PatchValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PatchProposal(BaseModel):
    patch_id: str
    audit_id: str
    base_source_hash: str
    target_files: list[str] = Field(default_factory=list)
    diff: str
    explanation: str = ""
    author: str = "nemotron-repair"


def compute_diff_hash(diff_text: str) -> str:
    return hashlib.sha256(diff_text.strip().encode("utf-8")).hexdigest()


def _header_path(line: str) -> str:
    raw = line[4:].strip()
    if not raw or raw == "/dev/null" or "\t" in raw or " " in raw:
        raise PatchValidationError("MALFORMED_DIFF", f"Unsafe or missing diff header path: {raw!r}")
    return re.sub(r"^[ab]/", "", raw).replace("\\", "/")


def _split_file_diffs(diff_text: str) -> dict[str, list[str]]:
    """Parse strict modify-only unified diffs and pair old/new paths."""
    lines = diff_text.splitlines(keepends=True)
    file_diffs: dict[str, list[str]] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not line.startswith("--- ") or index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
            raise PatchValidationError("MALFORMED_DIFF", "Expected paired ---/+++ file headers")
        old_path = _header_path(line)
        new_path = _header_path(lines[index + 1])
        if old_path != new_path:
            raise PatchValidationError(
                "PROTECTED_FILE_VIOLATION",
                f"Rename, creation, or deletion is forbidden: {old_path} -> {new_path}",
            )
        if old_path in file_diffs:
            raise PatchValidationError("MALFORMED_DIFF", f"Duplicate file section: {old_path}")
        section = [line, lines[index + 1]]
        index += 2
        while index < len(lines) and not lines[index].startswith("--- "):
            section.append(lines[index])
            index += 1
        if not any(item.startswith("@@ ") for item in section):
            raise PatchValidationError("MALFORMED_DIFF", f"No hunk found for {old_path}")
        file_diffs[old_path] = section
    if not file_diffs:
        raise PatchValidationError("MALFORMED_DIFF", "No file diff sections found")
    return file_diffs


def extract_diff_paths(diff_text: str) -> list[str]:
    """Extract affected paths from a strict, modify-only unified diff."""
    return sorted(_split_file_diffs(diff_text))



def validate_patch(
    proposal: PatchProposal,
    current_source_hash: str,
) -> tuple[bool, list[str]]:
    """Validate patch proposal against security and bounds policies."""
    # 1. Base Hash Verification
    if proposal.base_source_hash != current_source_hash:
        raise PatchValidationError(
            "PATCH_BASE_MISMATCH",
            f"Base source hash mismatch: proposed {proposal.base_source_hash} != current {current_source_hash}",
        )

    # 2. Non-empty diff check
    diff_text = proposal.diff.strip()
    if not diff_text:
        raise PatchValidationError("EMPTY_DIFF", "Patch diff content is empty")

    # 3. Line and byte ceilings
    diff_lines = proposal.diff.splitlines()
    if len(diff_lines) > MAX_DIFF_LINES:
        raise PatchValidationError(
            "PATCH_TOO_LARGE",
            f"Patch exceeds line ceiling: {len(diff_lines)} lines > {MAX_DIFF_LINES}",
        )
    diff_bytes = len(proposal.diff.encode("utf-8"))
    if diff_bytes > MAX_DIFF_BYTES:
        raise PatchValidationError(
            "PATCH_TOO_LARGE",
            f"Patch exceeds byte ceiling: {diff_bytes} bytes > {MAX_DIFF_BYTES}",
        )

    if "\x00" in proposal.diff or any(
        line.startswith(FORBIDDEN_DIFF_METADATA) for line in diff_lines
    ):
        raise PatchValidationError(
            "PROTECTED_FILE_VIOLATION",
            "File creation, deletion, rename, mode changes, binary patches, and git metadata are forbidden",
        )

    # 4. Extract and validate touched paths
    affected_paths = extract_diff_paths(proposal.diff)
    declared_paths = {p.replace("\\", "/").strip() for p in proposal.target_files}
    if len(affected_paths) > MAX_TARGET_FILES:
        raise PatchValidationError(
            "PATCH_TOO_LARGE",
            f"Patch touches {len(affected_paths)} files; maximum is {MAX_TARGET_FILES}",
        )

    approved_paths: list[str] = []
    for p in affected_paths:
        norm_p = p.replace("\\", "/").strip()
        # Traversal check
        if ".." in norm_p.split("/") or norm_p.startswith("/") or ":" in norm_p:
            raise PatchValidationError(
                "PROTECTED_FILE_VIOLATION",
                f"Path traversal or absolute path detected: {norm_p}",
            )

        if not norm_p.startswith("app/"):
            raise PatchValidationError(
                "PROTECTED_FILE_VIOLATION",
                f"Patch path must be rooted under app/: {norm_p}",
            )
        rel_within_app = norm_p[4:]
        if not rel_within_app or rel_within_app.startswith("/"):
            raise PatchValidationError("PROTECTED_FILE_VIOLATION", f"Invalid app path: {norm_p}")

        # Check for protected files
        path_parts = {part.casefold() for part in norm_p.split("/")}
        for protected in PROTECTED_PATTERNS:
            if protected.casefold() in path_parts:
                raise PatchValidationError(
                    "PROTECTED_FILE_VIOLATION",
                    f"Modification of protected resource denied: {norm_p}",
                )

        if not rel_within_app.endswith(".py"):
            raise PatchValidationError(
                "DISALLOWED_FILE_TYPE",
                f"Only Python source files (.py) within app/ are permitted: {norm_p}",
            )

        approved_paths.append(norm_p)

    if declared_paths and declared_paths != set(approved_paths):
        raise PatchValidationError(
            "TARGET_MISMATCH",
            "Declared target_files must exactly match the diff header paths",
        )

    return True, sorted(approved_paths)


def apply_patch_to_file(original_content: str, patch_diff: str) -> str:
    """Apply a strict unified diff, rejecting stale or forged hunk context.

    Line endings are normalized to LF on both sides so a CRLF checkout or a
    CRLF diff cannot produce mixed endings or a platform-dependent candidate.
    """
    lines = original_content.replace("\r\n", "\n").splitlines(keepends=True)
    diff_lines = patch_diff.replace("\r\n", "\n").splitlines(keepends=True)
    hunk_regex = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    current_line = 0
    result: list[str] = []
    i = 0
    while i < len(diff_lines):
        dline = diff_lines[i]
        match = hunk_regex.match(dline)
        if not match:
            i += 1
            continue

        expected_old = int(match.group(2) if match.group(2) is not None else "1")
        expected_new = int(match.group(4) if match.group(4) is not None else "1")
        # A zero-length old range (`-N,0`) is an insertion *after* line N, as GNU patch applies it.
        orig_start = int(match.group(1)) if expected_old == 0 else int(match.group(1)) - 1
        if orig_start < current_line or orig_start > len(lines):
            raise PatchValidationError("PATCH_APPLICATION_FAILED", "Overlapping or out-of-range hunk")
        result.extend(lines[current_line:orig_start])
        current_line = orig_start
        old_seen = new_seen = 0
        i += 1
        while i < len(diff_lines) and not hunk_regex.match(diff_lines[i]):
            item = diff_lines[i]
            if item.startswith(("--- ", "+++ ")):
                break
            if item.startswith("\\"):
                i += 1
                continue
            if not item or item[0] not in " +-":
                raise PatchValidationError("MALFORMED_DIFF", f"Invalid hunk line: {item!r}")
            if item[0] in " -":
                if current_line >= len(lines) or lines[current_line].rstrip("\r\n") != item[1:].rstrip("\r\n"):
                    raise PatchValidationError(
                        "PATCH_APPLICATION_FAILED",
                        "Patch hunk context does not match the pinned source",
                    )
                if item[0] == " ":
                    result.append(lines[current_line])
                    new_seen += 1
                current_line += 1
                old_seen += 1
            else:
                result.append(item[1:])
                new_seen += 1
            i += 1
        if old_seen != expected_old or new_seen != expected_new:
            raise PatchValidationError(
                "MALFORMED_DIFF",
                f"Hunk line counts do not match header: old {old_seen}/{expected_old}, new {new_seen}/{expected_new}",
            )

    # Append any remaining lines after all hunks
    while current_line < len(lines):
        result.append(lines[current_line])
        current_line += 1

    return "".join(result)


def apply_patch_to_dir(
    base_app_dir: Path,
    proposal: PatchProposal,
    dest_dir: Path,
) -> tuple[Path, str]:
    """Apply validated patch proposal to a copy of base_app_dir in dest_dir."""
    current_hash = source_hash_for_dir(base_app_dir)
    validate_patch(proposal, current_hash)

    # Ensure fresh copy of base_app_dir into dest_dir
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(base_app_dir, dest_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    file_diffs = {
        path.removeprefix("app/"): section
        for path, section in _split_file_diffs(proposal.diff).items()
    }

    for rel_file, dlines in file_diffs.items():
        target_file = dest_dir / rel_file
        if (
            not target_file.exists()
            or target_file.is_symlink()
            or not target_file.resolve().is_relative_to(dest_dir.resolve())
        ):
            raise PatchValidationError(
                "PATCH_APPLICATION_FAILED",
                f"Target file does not exist in candidate directory: {rel_file}",
            )
        original_text = target_file.read_text(encoding="utf-8")
        patched_text = apply_patch_to_file(original_text, "".join(dlines))
        # Write LF explicitly: the default newline translation on Windows would turn an
        # already-CRLF line into "\r\r\n" and change the candidate hash per platform.
        target_file.write_text(patched_text, encoding="utf-8", newline="\n")

    candidate_hash = source_hash_for_dir(dest_dir)
    return dest_dir, candidate_hash


# ── Canonical reference and test repairs ─────────────────────────────────

def get_canonical_mc01_repair_diff() -> str:
    """Minimal canonical repair diff for MC-01 (money.py)."""
    return """--- a/app/money.py
+++ b/app/money.py
@@ -4,12 +4,6 @@
 def compute_total(lines: List[str]) -> str:
-    \"\"\"Faulty: premature rounding of each line.\"\"\"
+    \"\"\"Sum unrounded line amounts, then ROUND_HALF_UP once on the invoice total.\"\"\"
     if not lines:
         return "0.00"
-    
-    total = Decimal("0")
-    for line in lines:
-        # Fault: Rounding each line individually before summing
-        val = Decimal(line).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
-        total += val
-        
+    total = sum((Decimal(line) for line in lines), Decimal("0"))
     return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
"""


def get_canonical_ac01_repair_diff() -> str:
    """Minimal canonical repair diff for AC-01 (schemas.py and services.py)."""
    return """--- a/app/schemas.py
+++ b/app/schemas.py
@@ -13,2 +13,2 @@
-    amount: str  # Fault: renamed from total_amount
-    # Fault: status field is missing
+    total_amount: str
+    status: str
--- a/app/services.py
+++ b/app/services.py
@@ -24,2 +24,3 @@
-        "amount": total, # Fault applied here
+        "total_amount": total,
+        "status": "processed"
     }
"""


def get_shallow_mc01_repair_diff() -> str:
    """Inadequate shallow repair diff that still rounds prematurely or uses float."""
    return """--- a/app/money.py
+++ b/app/money.py
@@ -4,3 +4,3 @@
 def compute_total(lines: List[str]) -> str:
-    \"\"\"Faulty: premature rounding of each line.\"\"\"
+    \"\"\"Shallow fix: rounds to 2 decimals using float.\"\"\"
     if not lines:
@@ -9,5 +9,5 @@
     total = Decimal("0")
     for line in lines:
         # Fault: Rounding each line individually before summing
-        val = Decimal(line).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
+        val = Decimal(str(round(float(line), 2)))
         total += val
"""
