"""Tests for restricted patch authoring and import (B-09)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.patch import (
    MAX_DIFF_BYTES,
    MAX_DIFF_LINES,
    PatchProposal,
    PatchValidationError,
    apply_patch_to_dir,
    compute_diff_hash,
    extract_diff_paths,
    get_canonical_ac01_repair_diff,
    get_canonical_mc01_repair_diff,
    validate_patch,
)


def test_extract_diff_paths_from_unified_diff() -> None:
    diff = get_canonical_ac01_repair_diff()
    paths = extract_diff_paths(diff)
    assert paths == ["app/schemas.py", "app/services.py"]


def test_canonical_mc01_patch_validation_passes() -> None:
    app_dir = fixture_dir("MC-01") / "app"
    shash = source_hash_for_dir(app_dir)
    diff = get_canonical_mc01_repair_diff()

    # Test compute_diff_hash
    dhash = compute_diff_hash(diff)
    assert len(dhash) == 64
    assert dhash == compute_diff_hash(diff)

    proposal = PatchProposal(
        patch_id="patch-mc01-test",
        audit_id="audit-mc01",
        base_source_hash=shash,
        target_files=["app/money.py"],
        diff=diff,
    )
    ok, approved = validate_patch(proposal, shash)
    assert ok is True
    assert "money.py" in approved or "app/money.py" in approved


def test_base_hash_mismatch_rejected() -> None:
    diff = get_canonical_mc01_repair_diff()
    proposal = PatchProposal(
        patch_id="patch-stale",
        audit_id="audit-stale",
        base_source_hash="wrong-stale-hash-12345",
        target_files=["app/money.py"],
        diff=diff,
    )
    with pytest.raises(PatchValidationError) as exc:
        validate_patch(proposal, "actual-correct-hash-67890")
    assert exc.value.code == "PATCH_BASE_MISMATCH"


def test_protected_file_edits_rejected() -> None:
    app_dir = fixture_dir("MC-01") / "app"
    shash = source_hash_for_dir(app_dir)

    # 1. Traversal attempt
    p1 = PatchProposal(
        patch_id="patch-traversal",
        audit_id="audit-1",
        base_source_hash=shash,
        target_files=["../expected.json"],
        diff="--- a/../expected.json\n+++ b/../expected.json\n@@ -1,1 +1,1 @@\n-x\n+y",
    )
    with pytest.raises(PatchValidationError) as exc:
        validate_patch(p1, shash)
    assert exc.value.code == "PROTECTED_FILE_VIOLATION"

    # 2. Protected asset edit
    p2 = PatchProposal(
        patch_id="patch-protected",
        audit_id="audit-2",
        base_source_hash=shash,
        target_files=["app/expected.json"],
        diff="--- a/expected.json\n+++ b/expected.json\n@@ -1,1 +1,1 @@\n-x\n+y",
    )
    with pytest.raises(PatchValidationError) as exc2:
        validate_patch(p2, shash)
    assert exc2.value.code == "PROTECTED_FILE_VIOLATION"


def test_oversized_patch_rejected() -> None:
    app_dir = fixture_dir("MC-01") / "app"
    shash = source_hash_for_dir(app_dir)

    # Exceed line ceiling
    huge_diff = "--- a/app/money.py\n+++ b/app/money.py\n" + "\n".join(f"+# line {i}" for i in range(MAX_DIFF_LINES + 5))
    p = PatchProposal(
        patch_id="patch-huge",
        audit_id="audit-huge",
        base_source_hash=shash,
        target_files=["app/money.py"],
        diff=huge_diff,
    )
    with pytest.raises(PatchValidationError) as exc:
        validate_patch(p, shash)
    assert exc.value.code == "PATCH_TOO_LARGE"

    # Exceed byte ceiling
    huge_bytes = "--- a/app/money.py\n+++ b/app/money.py\n" + ("+# padding long byte line\n" * ((MAX_DIFF_BYTES // 20) + 10))
    p_bytes = PatchProposal(
        patch_id="patch-huge-bytes",
        audit_id="audit-huge-bytes",
        base_source_hash=shash,
        target_files=["app/money.py"],
        diff=huge_bytes,
    )
    with pytest.raises(PatchValidationError) as exc_bytes:
        validate_patch(p_bytes, shash)
    assert exc_bytes.value.code == "PATCH_TOO_LARGE"



def test_empty_diff_rejected() -> None:
    app_dir = fixture_dir("MC-01") / "app"
    shash = source_hash_for_dir(app_dir)

    p = PatchProposal(
        patch_id="patch-empty",
        audit_id="audit-empty",
        base_source_hash=shash,
        target_files=["app/money.py"],
        diff="   ",
    )
    with pytest.raises(PatchValidationError) as exc:
        validate_patch(p, shash)
    assert exc.value.code == "EMPTY_DIFF"


def test_clean_application_of_mc01_repair() -> None:
    base_dir = fixture_dir("MC-01") / "app"
    shash = source_hash_for_dir(base_dir)
    diff = get_canonical_mc01_repair_diff()

    proposal = PatchProposal(
        patch_id="p-mc01",
        audit_id="a-mc01",
        base_source_hash=shash,
        target_files=["app/money.py"],
        diff=diff,
    )

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "candidate_app"
        out_dir, cand_hash = apply_patch_to_dir(base_dir, proposal, dest)
        assert out_dir.exists()
        assert cand_hash != shash
        
        # Verify content was patched
        money_content = (dest / "money.py").read_text(encoding="utf-8")
        assert "sum((Decimal(line) for line in lines), Decimal(\"0\"))" in money_content
        assert "Fault: Rounding each line individually" not in money_content
