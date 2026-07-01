"""Tests for skill_manager.utils.joblib_backend.

ADR-0021: In PyInstaller-frozen builds, loky's process-fork mechanism is
broken on Windows (OSError: WinError 6). We switch to threads in frozen mode.
"""

import sys
from unittest.mock import patch

from skill_manager.utils.joblib_backend import joblib_prefer, joblib_workers


def test_joblib_prefer_threads_when_frozen():
    with patch.object(sys, "frozen", True, create=True):
        assert joblib_prefer() == "threads"


def test_joblib_prefer_processes_when_dev():
    with patch.object(sys, "frozen", False, create=True):
        assert joblib_prefer() == "processes"


def test_joblib_prefer_uses_frozen_flag():
    assert joblib_prefer() in ("threads", "processes")


def test_joblib_workers_capped():
    workers = joblib_workers()
    assert workers >= 1
    assert workers <= 2


def test_joblib_workers_returns_int():
    workers = joblib_workers()
    assert isinstance(workers, int)


def test_discovery_uses_helper():
    """Verify discovery.py imports from joblib_backend and has no bare prefer='processes'."""
    from pathlib import Path

    content = (
        Path(__file__).resolve().parents[1] / "src" / "skill_manager" / "core" / "discovery.py"
    ).read_text(encoding="utf-8")
    assert "joblib_prefer" in content
    assert "joblib_workers" in content
    assert 'prefer="processes"' not in content
    assert "_JOBLIB_WORKERS" not in content


def test_quick_copy_uses_helper():
    """Verify quick_copy.py imports from joblib_backend and has no bare prefer='processes'."""
    from pathlib import Path

    content = (
        Path(__file__).resolve().parents[1] / "src" / "skill_manager" / "core" / "quick_copy.py"
    ).read_text(encoding="utf-8")
    assert "joblib_prefer" in content
    assert "joblib_workers" in content
    assert 'prefer="processes"' not in content
    assert "_JOBLIB_WORKERS" not in content
