"""Fixture IDs resolve consistently without importing candidate code."""

import json

import pytest

from benchproof.fixtures import fixture_dir, list_fixture_ids, load_manifest, source_hash


@pytest.mark.parametrize("requested", ["MC-01", "mc-01", "Mc-01", "mC-01"])
def test_fixture_lookup_uses_canonical_directory_case(tmp_path, monkeypatch, requested):
    root = tmp_path / "fixtures"
    canonical = root / "MC-01"
    (canonical / "app").mkdir(parents=True)
    (canonical / "app" / "money.py").write_text("VALUE = 1\n", encoding="utf-8")
    (canonical / "fixture.json").write_text(json.dumps({"fixture_id": "MC-01"}), encoding="utf-8")
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(root))

    resolved = fixture_dir(requested)
    assert resolved.name == "MC-01"
    assert resolved == canonical
    assert load_manifest(requested)["fixture_id"] == "MC-01"
    assert source_hash(requested) == source_hash("MC-01")
    assert list_fixture_ids() == ["MC-01"]


@pytest.mark.parametrize("requested", ["../MC-01", "MC-01/app", "MC-01\\app", "C:MC-01", "/MC-01", "MC..01", ""])
def test_case_lookup_does_not_weaken_path_validation(tmp_path, monkeypatch, requested):
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="unsafe fixture id"):
        fixture_dir(requested)


def test_missing_fixture_keeps_not_found_behavior(tmp_path, monkeypatch):
    root = tmp_path / "absent"
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(root))
    assert fixture_dir("missing") == root / "missing"
    with pytest.raises(FileNotFoundError):
        load_manifest("missing")


def test_case_collisions_fail_closed_even_for_an_exact_match(tmp_path, monkeypatch):
    (tmp_path / "MC-01").mkdir()
    (tmp_path / "mc-01").mkdir(exist_ok=True)
    if len(list(tmp_path.iterdir())) != 2:
        pytest.skip("Filesystem is case-insensitive; collision cannot be created")
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(tmp_path))
    for requested in ("MC-01", "mc-01", "Mc-01"):
        with pytest.raises(ValueError, match="ambiguous fixture id"):
            fixture_dir(requested)


@pytest.mark.parametrize("requested", ["ESCAPE", "escape"])
def test_case_alias_cannot_follow_a_link_outside_fixture_root(tmp_path, monkeypatch, requested):
    root = tmp_path / "fixtures"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        (root / "ESCAPE").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating directory links requires unavailable OS permissions")
    monkeypatch.setenv("BENCHPROOF_FIXTURES_DIR", str(root))
    with pytest.raises(ValueError, match="unsafe fixture id"):
        fixture_dir(requested)
