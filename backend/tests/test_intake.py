"""Tests for source intake validation and limits (B-07)."""

import pytest

from benchproof.fixtures import fixture_dir, source_hash
from benchproof.intake import (
    IntakeError,
    inspect_source_tree,
    validate_relative_path,
    verify_base_source_hash,
)


def test_validate_relative_path_safe():
    assert validate_relative_path("app/routes.py") == "app/routes.py"
    assert validate_relative_path("app/sub/module.py") == "app/sub/module.py"
    assert validate_relative_path("app\\money.py") == "app/money.py"


def test_validate_relative_path_traversal_rejected():
    with pytest.raises(IntakeError, match="Path traversal forbidden"):
        validate_relative_path("app/../secret.txt")

    with pytest.raises(IntakeError, match="Path traversal forbidden"):
        validate_relative_path("app/./routes.py")

    with pytest.raises(IntakeError, match="Absolute path forbidden"):
        validate_relative_path("/etc/passwd")


def test_validate_relative_path_scope_rejected():
    with pytest.raises(IntakeError, match="Path outside editable scope"):
        validate_relative_path("tests/test_api.py")


def test_validate_relative_path_disallowed_names():
    with pytest.raises(IntakeError, match="Disallowed name in path"):
        validate_relative_path("app/expected.json")

    with pytest.raises(IntakeError, match="Disallowed name in path"):
        validate_relative_path("app/reference/file.py")


def test_inspect_clean_service_tree():
    app_dir = fixture_dir("clean-service") / "app"
    info = inspect_source_tree(app_dir)
    assert info["file_count"] >= 5
    assert info["total_bytes"] > 0
    assert "app/routes.py" in info["manifest"]
    assert info["source_hash"] == source_hash("clean-service")


def test_verify_base_source_hash_matching():
    shash = source_hash("clean-service")
    # Should not raise
    verify_base_source_hash(shash, shash)


def test_verify_base_source_hash_mismatch_raises():
    shash = source_hash("clean-service")
    with pytest.raises(IntakeError, match="STALE_SOURCE"):
        verify_base_source_hash(shash, "wrong_hash_123")
