"""Tests for compute_dir_fingerprint memoization.

Covers:
- Baseline correctness (same fingerprint across calls when nothing changes).
- Memo hit on second call when prefix is unchanged (_hash_child_names NOT called).
- Memo miss + recompute when the dir changes (a new subdir with SKILL.md added).
- Cross-call equivalence: fingerprint matches the value the un-memoized path would produce.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from skill_manager.core import discovery
from skill_manager.core.discovery import _hash_child_names, compute_dir_fingerprint


def _make_skill_dir(parent: Path, name: str) -> Path:
    """Create `<parent>/<name>/SKILL.md` and return the skill subdir."""
    skill = parent / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return skill


def test_fingerprint_is_stable_across_calls(tmp_path: Path) -> None:
    """Two calls on an unchanged dir return the same fingerprint."""
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")
    _make_skill_dir(d, "bravo")

    fp1 = compute_dir_fingerprint(d)
    fp2 = compute_dir_fingerprint(d)

    assert fp1 == fp2
    assert len(fp1) == len(hashlib.md5(b"").hexdigest())


def test_fingerprint_matches_unmemoized_formula(tmp_path: Path) -> None:
    """Fingerprint equals md5 of the documented raw format string."""
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")
    _make_skill_dir(d, "bravo")

    # Compute the expected raw string using only the public building blocks,
    # independent of the memoization path inside compute_dir_fingerprint.
    stat = d.stat()
    skill_dirs = [c for c in d.iterdir() if c.is_dir() and (c / "SKILL.md").is_file()]
    skill_count = len(skill_dirs)
    max_sub_mtime = max(s.stat().st_mtime for s in skill_dirs) if skill_dirs else 0.0
    child_names_hash = _hash_child_names(d)
    expected_raw = (
        f"{stat.st_mtime}:{stat.st_size}:{skill_count}:{max_sub_mtime}:{child_names_hash}"
    )
    expected_fp = hashlib.md5(expected_raw.encode()).hexdigest()

    assert compute_dir_fingerprint(d) == expected_fp


def test_second_call_hits_memo_and_skips_child_hash(tmp_path: Path) -> None:
    """When the cheap prefix is unchanged, the second call does NOT
    invoke _hash_child_names (the expensive iterdir + sort + sha1).
    """
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")

    # Prime the memo.
    fp1 = compute_dir_fingerprint(d)
    assert fp1, "Baseline fingerprint should be non-empty"

    # Patch _hash_child_names with a tracking wrapper around the real impl,
    # installed on the discovery module so compute_dir_fingerprint sees it.
    real = _hash_child_names
    calls = {"n": 0}

    def wrapper(p: Path) -> str:
        calls["n"] += 1
        return real(p)

    with patch.object(discovery, "_hash_child_names", side_effect=wrapper):
        fp2 = compute_dir_fingerprint(d)

    assert fp1 == fp2, "Memo hit must return the same fingerprint"
    assert calls["n"] == 0, (
        f"_hash_child_names must NOT run on a memo hit; ran {calls['n']} time(s)"
    )


def test_memo_miss_when_dir_changes(tmp_path: Path) -> None:
    """When a new subdir with SKILL.md is added, the memo is invalidated,
    _hash_child_names IS called again, and the fingerprint changes.
    """
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")

    fp_before = compute_dir_fingerprint(d)

    real = _hash_child_names
    calls = {"n": 0}

    def wrapper(p: Path) -> str:
        calls["n"] += 1
        return real(p)

    # Mutate the dir: add a new skill subdir, which shifts skill_count and
    # the parent's mtime/size (and possibly max_sub_mtime). Either way the
    # prefix tuple changes and we expect a cache miss.
    _make_skill_dir(d, "bravo")

    with patch.object(discovery, "_hash_child_names", side_effect=wrapper):
        fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after, "Fingerprint MUST change after a real mutation"
    assert calls["n"] == 1, (
        f"_hash_child_names must run exactly once on a memo miss; ran {calls['n']} time(s)"
    )

    # And a third call (no further mutation) should hit the memo again.
    calls["n"] = 0
    with patch.object(discovery, "_hash_child_names", side_effect=wrapper):
        fp_after_again = compute_dir_fingerprint(d)
    assert fp_after_again == fp_after
    assert calls["n"] == 0, "Third call on stable dir should be a memo hit"


def test_memo_key_is_normcase_insensitive(tmp_path: Path) -> None:
    """On case-insensitive filesystems (Windows), the memo must be keyed
    by normcase so that 'Foo' and 'foo' share a cache entry.

    Skipped on case-sensitive filesystems (Linux) where ``Path(str(d).upper())``
    refers to a non-existent directory.
    """
    import sys

    # Detect case-insensitive filesystem: on Linux (the CI host), /tmp is
    # almost always case-sensitive, so the uppercased path won't exist and
    # compute_dir_fingerprint returns ''.  Skip on case-sensitive FS.
    if sys.platform != "win32" and not Path(str(tmp_path).upper()).exists():
        pytest.skip("case-insensitive normcase test requires case-insensitive FS")

    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")

    fp1 = compute_dir_fingerprint(d)

    # Same path, different case in the string form — normcase collapses it.
    fp2 = compute_dir_fingerprint(Path(str(d).upper()))

    assert fp1 == fp2


def test_memo_does_not_leak_across_distinct_dirs(tmp_path: Path) -> None:
    """Two different directories must not share a memo entry."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _make_skill_dir(a, "x")
    _make_skill_dir(b, "y")

    fp_a = compute_dir_fingerprint(a)
    fp_b = compute_dir_fingerprint(b)

    assert fp_a != fp_b
    # Second calls on each must still return their own value (no cross-pollution).
    assert compute_dir_fingerprint(a) == fp_a
    assert compute_dir_fingerprint(b) == fp_b
