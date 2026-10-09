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


def extract_diff_paths(diff_text: str) -> list[str]:
    """Extract affected relative file paths from a unified diff."""
    paths: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith(("--- ", "+++ ")):
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                raw_path = parts[1].strip()
                # strip common diff prefixes like a/ or b/
                cleaned = re.sub(r"^[ab]/", "", raw_path)
                if cleaned and cleaned != "/dev/null":
                    paths.add(cleaned)
    return sorted(paths)



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

    # 4. Extract and validate touched paths
    affected_paths = extract_diff_paths(proposal.diff)
    all_paths = set(affected_paths) | set(proposal.target_files)
    if not all_paths:
        raise PatchValidationError("NO_TARGET_FILES", "No valid target files found in patch diff")

    approved_paths: list[str] = []
    for p in all_paths:
        norm_p = p.replace("\\", "/").strip()
        # Traversal check
        if ".." in norm_p.split("/") or norm_p.startswith("/") or ":" in norm_p:
            raise PatchValidationError(
                "PROTECTED_FILE_VIOLATION",
                f"Path traversal or absolute path detected: {norm_p}",
            )

        # Allowlist check: Must target app/ tree
        # Note: diff might be "app/money.py" or "money.py" if relative to app
        if norm_p.startswith("app/"):
            rel_within_app = norm_p[4:]
        else:
            rel_within_app = norm_p

        # Check for protected files
        for protected in PROTECTED_PATTERNS:
            if protected in norm_p.split("/"):
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

    return True, sorted(approved_paths)


def apply_patch_to_file(original_content: str, patch_diff: str) -> str:
    """Apply a unified diff hunk to single file content."""
    lines = original_content.splitlines(keepends=True)
    # Parse diff lines
    diff_lines = patch_diff.splitlines(keepends=True)
    
    # Simple, reliable hunk application for clean patches
    # If standard patch tools are unavailable, perform precise block replacement
    # by matching unified diff hunks
    hunk_regex = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    
    current_line = 0
    result: list[str] = []
    hunk_started = False
    
    i = 0
    while i < len(diff_lines):
        dline = diff_lines[i]
        match = hunk_regex.match(dline)
        if match:
            hunk_started = True
            orig_start = int(match.group(1)) - 1
            # copy unchanged lines up to hunk start
            while current_line < orig_start and current_line < len(lines):
                result.append(lines[current_line])
                current_line += 1
            i += 1
            continue
            
        if hunk_started:
            if dline.startswith(" "):
                # Context line: verify and advance
                if current_line < len(lines):
                    result.append(lines[current_line])
                    current_line += 1
                i += 1
            elif dline.startswith("-"):
                # Deleted line: skip in original
                current_line += 1
                i += 1
            elif dline.startswith("+"):
                # Added line: insert
                result.append(dline[1:])
                i += 1
            elif dline.startswith("\\"):
                # "\ No newline at end of file"
                i += 1
            else:
                i += 1
        else:
            i += 1

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
    # Ensure fresh copy of base_app_dir into dest_dir
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(base_app_dir, dest_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    # Split diff by file
    file_diffs: dict[str, list[str]] = {}
    current_file: str | None = None
    
    for line in proposal.diff.splitlines(keepends=True):
        if line.startswith("--- "):
            raw = line.split(maxsplit=1)[1].strip()
            clean = re.sub(r"^[ab]/", "", raw)
            clean = clean.removeprefix("app/")
            current_file = clean
            file_diffs[current_file] = [line]
        elif line.startswith("+++ "):
            raw = line.split(maxsplit=1)[1].strip()
            clean = re.sub(r"^[ab]/", "", raw)
            clean = clean.removeprefix("app/")
            current_file = clean
            if current_file in file_diffs:
                file_diffs[current_file].append(line)
            else:
                file_diffs[current_file] = [line]

        elif current_file:
            file_diffs[current_file].append(line)

    if not file_diffs:
        raise PatchValidationError("MALFORMED_DIFF", "No file diff hunks could be parsed")

    for rel_file, dlines in file_diffs.items():
        target_file = dest_dir / rel_file
        if not target_file.exists():
            raise PatchValidationError(
                "PATCH_APPLICATION_FAILED",
                f"Target file does not exist in candidate directory: {rel_file}",
            )
        original_text = target_file.read_text(encoding="utf-8")
        patched_text = apply_patch_to_file(original_text, "".join(dlines))
        target_file.write_text(patched_text, encoding="utf-8")

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
@@ -13,3 +13,2 @@
-    amount: str  # Fault: renamed from total_amount
-    # Fault: status field is missing
+    total_amount: str
+    status: str
--- a/app/services.py
+++ b/app/services.py
@@ -24,2 +24,2 @@
-        "amount": total, # Fault applied here
+        "total_amount": total,
+        "status": "processed"
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
@@ -9,4 +9,4 @@
     total = Decimal("0")
     for line in lines:
-        val = Decimal(line).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
+        val = Decimal(str(round(float(line), 2)))
         total += val
"""
