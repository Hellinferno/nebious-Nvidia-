"""Constrained project intake and validation (C-04).

Enforces:
- File count <= 20
- File size <= 24 KiB per file (24,576 bytes)
- Total size <= 128 KiB (131,072 bytes)
- Documented layout: editable 'app/', protected imported 'tests/'
- Path safety: no path traversal, absolute paths, backslashes, drive letters
- Exclusion of secrets, dot-files, bytecode, and common unsafe files
- Case-collision detection
- UTF-8 text only with no null bytes
- Canonical manifest fingerprinting
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from benchproof.projects.models import ProjectManifest

MAX_FILES = 20
MAX_FILE_BYTES = 24_576       # 24 KiB
MAX_TOTAL_BYTES = 131_072     # 128 KiB
MAX_ENCODED_BODY_BYTES = 262_144  # 256 KiB
MANIFEST_VERSION = "project-manifest-v1"
SUPPORTED_RUNNER_PROFILES = {"unittest"}

_DISALLOWED_EXACT_NAMES = {
    ".env", ".git", ".gitignore", ".gitattributes", ".dockerignore", "Dockerfile",
    "credentials", "secrets", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
}
_DISALLOWED_PREFIXES = (
    ".env", ".git", ".github", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    ".vscode", ".idea", "__pycache__", "venv", ".venv", "node_modules",
)
_DISALLOWED_EXTENSIONS = (
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".key", ".pem", ".p12", ".pfx", ".cer", ".crt", ".tar", ".gz",
    ".zip", ".7z", ".rar", ".db", ".sqlite", ".sqlite3",
)
_SECRET_KEYWORDS = ("secret", "token", "password", "private_key", "credential", "api_key")

_PATH_PATTERN = re.compile(r"^(app|tests)/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+$")


class ProjectIntakeError(Exception):
    """Raised when project files violate intake safety, layout, or limits."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_relative_path(path: str) -> str:
    """Validate and normalize a project-relative file path."""
    if not isinstance(path, str) or not path.strip():
        raise ProjectIntakeError("INVALID_PATH", "Path must be non-empty text")
    
    # Reject backslashes and drive letters
    if "\\" in path or re.match(r"^[A-Za-z]:", path):
        raise ProjectIntakeError("INVALID_PATH", f"Windows-style paths and backslashes are forbidden: {path}")

    norm = path.strip()
    if norm.startswith("/"):
        raise ProjectIntakeError("INVALID_PATH", f"Absolute paths are forbidden: {path}")

    parts = norm.split("/")
    if any(p == ".." or p == "." for p in parts):
        raise ProjectIntakeError("PATH_TRAVERSAL", f"Path traversal components are forbidden: {path}")
    if any(not p for p in parts):
        raise ProjectIntakeError("INVALID_PATH", f"Empty path segments are forbidden: {path}")

    # Check prefix requirement
    if not norm.startswith(("app/", "tests/")):
        raise ProjectIntakeError("INVALID_LAYOUT", f"Path must reside under 'app/' or 'tests/': {path}")

    # Check filename and components against disallowed names/secrets
    filename = parts[-1]
    name_lower = filename.casefold()

    if name_lower in _DISALLOWED_EXACT_NAMES:
        raise ProjectIntakeError("UNSAFE_FILE", f"Disallowed filename forbidden: {filename}")

    for prefix in _DISALLOWED_PREFIXES:
        if any(part.casefold().startswith(prefix) for part in parts):
            raise ProjectIntakeError("UNSAFE_FILE", f"Disallowed component forbidden: {path}")

    for ext in _DISALLOWED_EXTENSIONS:
        if name_lower.endswith(ext):
            raise ProjectIntakeError("UNSAFE_FILE", f"Disallowed file extension ({ext}) forbidden: {path}")

    for keyword in _SECRET_KEYWORDS:
        if keyword in name_lower:
            raise ProjectIntakeError("SECRET_DETECTED", f"Potential secret or credential pattern in filename: {filename}")

    if not _PATH_PATTERN.fullmatch(norm):
        raise ProjectIntakeError("INVALID_PATH", f"Path contains unsupported characters: {path}")

    return norm


def validate_project_intake(
    files: dict[str, Any],
    runner_profile: str = "unittest",
) -> tuple[ProjectManifest, dict[str, str]]:
    """Validate submitted project files, enforce limits, and build canonical manifest.

    Returns:
        (ProjectManifest, normalized_files_dict)
    """
    if runner_profile not in SUPPORTED_RUNNER_PROFILES:
        raise ProjectIntakeError(
            "UNSUPPORTED_RUNNER",
            f"Runner profile '{runner_profile}' is unsupported; choose from {sorted(SUPPORTED_RUNNER_PROFILES)}",
        )

    if not isinstance(files, dict):
        raise ProjectIntakeError("INVALID_INPUT", "Project files must be provided as a dictionary")

    if len(files) == 0:
        raise ProjectIntakeError("EMPTY_PROJECT", "Project must contain at least one file")
    if len(files) > MAX_FILES:
        raise ProjectIntakeError(
            "FILE_COUNT_EXCEEDED",
            f"Project contains {len(files)} files, exceeding the limit of {MAX_FILES}",
        )

    # Check case collisions
    case_folded: dict[str, str] = {}
    normalized_files: dict[str, str] = {}
    file_hashes: dict[str, str] = {}
    app_files: list[str] = []
    test_files: list[str] = []
    total_raw_bytes = 0

    for raw_path, content in files.items():
        if not isinstance(content, str):
            raise ProjectIntakeError("INVALID_CONTENT", f"File content for '{raw_path}' must be a string")

        clean_path = validate_relative_path(raw_path)
        folded = clean_path.casefold()
        if folded in case_folded:
            raise ProjectIntakeError(
                "CASE_COLLISION",
                f"Path case collision detected: '{clean_path}' collides with '{case_folded[folded]}'",
            )
        case_folded[folded] = clean_path

        # Validate UTF-8 and check null bytes
        try:
            raw_bytes = content.encode("utf-8")
        except UnicodeError as exc:
            raise ProjectIntakeError("INVALID_ENCODING", f"File '{clean_path}' is not valid UTF-8") from exc

        if b"\x00" in raw_bytes:
            raise ProjectIntakeError("BINARY_FILE", f"Binary or null byte detected in '{clean_path}'")

        file_len = len(raw_bytes)
        if file_len > MAX_FILE_BYTES:
            raise ProjectIntakeError(
                "FILE_TOO_LARGE",
                f"File '{clean_path}' ({file_len} bytes) exceeds the limit of {MAX_FILE_BYTES} bytes",
            )

        total_raw_bytes += file_len
        if total_raw_bytes > MAX_TOTAL_BYTES:
            raise ProjectIntakeError(
                "TOTAL_SIZE_EXCEEDED",
                f"Total project size ({total_raw_bytes} bytes) exceeds limit of {MAX_TOTAL_BYTES} bytes",
            )

        # Normalize line endings to LF for fingerprinting
        canonical_content = content.replace("\r\n", "\n")
        file_hash = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()
        file_hashes[clean_path] = file_hash
        normalized_files[clean_path] = canonical_content

        if clean_path.startswith("app/"):
            app_files.append(clean_path)
        elif clean_path.startswith("tests/"):
            test_files.append(clean_path)

    # Layout requirements: must have at least one app/ python file and one tests/ python test file
    app_py_files = [p for p in app_files if p.endswith(".py")]
    test_py_files = [p for p in test_files if p.endswith(".py")]

    if not app_py_files:
        raise ProjectIntakeError("MISSING_APP_FILES", "Project must contain at least one Python file under 'app/'")
    if not test_py_files:
        raise ProjectIntakeError("MISSING_TEST_FILES", "Project must contain at least one Python test file under 'tests/'")

    # Canonical sorted manifest representation
    canonical_manifest_json = json.dumps(file_hashes, sort_keys=True, separators=(",", ":"))
    source_hash = hashlib.sha256(canonical_manifest_json.encode("utf-8")).hexdigest()

    manifest = ProjectManifest(
        manifest_version=MANIFEST_VERSION,
        runner_profile=runner_profile,
        source_hash=source_hash,
        files=file_hashes,
        app_files=sorted(app_files),
        test_files=sorted(test_files),
        total_files=len(normalized_files),
        total_bytes=total_raw_bytes,
    )

    return manifest, normalized_files
