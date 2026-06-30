"""Tests for compute_dir_fingerprint detecting child-name changes."""

import hashlib
from pathlib import Path

from skill_manager.core.discovery import _hash_child_names, compute_dir_fingerprint


def test_fingerprint_includes_child_names_hash_component():
    """Fingerprint changes when child directory names change."""
    tmp = Path(__file__).parent / "test_fingerprint_tmp"  # noqa: S100

    # Create dir with one child
    d = tmp / "base"
    d.mkdir(parents=True, exist_ok=True)
    (d / "alpha").mkdir(exist_ok=True)

    fp1 = compute_dir_fingerprint(d)

    # Add a new child
    (d / "bravo").mkdir(exist_ok=True)
    fp2 = compute_dir_fingerprint(d)

    assert fp1 != fp2, "Fingerprint should change when child dir is added"

    # Cleanup
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_fingerprint_changes_when_child_dir_added(tmp_path):
    """Adding a child directory changes the fingerprint."""
    d = tmp_path / "dir"
    d.mkdir()
    fp_before = compute_dir_fingerprint(d)

    (d / "new-child").mkdir()
    fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after


def test_fingerprint_changes_when_child_dir_deleted(tmp_path):
    """Deleting a child directory changes the fingerprint (the brainstorming case)."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "child-a").mkdir()
    (d / "child-b").mkdir()

    fp_before = compute_dir_fingerprint(d)

    # Delete one child (simulates removing brainstorming skill)
    import shutil

    shutil.rmtree(d / "child-a")

    fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after, "Fingerprint MUST change when a child dir is deleted"


def test_fingerprint_changes_when_child_dir_renamed(tmp_path):
    """Renaming a child directory changes the fingerprint."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "old-name").mkdir()

    fp_before = compute_dir_fingerprint(d)

    (d / "old-name").rename(d / "new-name")
    fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after


def test_fingerprint_unchanged_for_unchanged_dir(tmp_path):
    """Fingerprint stays the same when nothing changes."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "child-a").mkdir()
    (d / "child-b").mkdir()

    fp1 = compute_dir_fingerprint(d)
    fp2 = compute_dir_fingerprint(d)

    assert fp1 == fp2


def test_hash_child_names_sorted():
    """_hash_child_names returns same hash regardless of filesystem iteration order."""
    tmp = Path(__file__).parent / "test_hash_tmp"  # noqa: S100
    d = tmp / "dir"
    d.mkdir(parents=True, exist_ok=True)
    (d / "bravo").mkdir(exist_ok=True)
    (d / "alpha").mkdir(exist_ok=True)

    h1 = _hash_child_names(d)
    h2 = _hash_child_names(d)

    assert h1 == h2, "Hash should be deterministic"
    assert len(h1) == 16

    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_hash_child_names_empty_dir(tmp_path):
    """_hash_child_names returns empty string for empty dir on error, or hash of empty string."""
    h = _hash_child_names(tmp_path)
    # Empty dir: sorted names = [], join = "", sha1 of "" = e3b0c44298fc...
    expected = hashlib.sha1(b"").hexdigest()[:16]
    assert h == expected
