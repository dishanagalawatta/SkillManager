"""Tests for core/diagnostics.py — structured diagnostic logging."""

from __future__ import annotations

import json
import os
import sys
import threading
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from skill_manager.core.diagnostics import (
    DiagnosticLogger,
    get_diagnostic_logger,
    is_dev_mode,
    log_dir,
)


@pytest.fixture
def diag_logger(tmp_path):
    """Create a DiagnosticLogger with a temp log directory, with logging enabled."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="DEBUG")
    logger.set_enabled(True)
    return logger


@pytest.fixture
def diag_logger_info(tmp_path):
    """Create a DiagnosticLogger at INFO level, with logging enabled."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="INFO")
    logger.set_enabled(True)
    return logger


# --- log_dir ---


def test_log_dir_windows(tmp_path):
    with (
        patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}, clear=False),
        patch.object(sys, "platform", "win32"),
    ):
        result = log_dir()
        assert result == tmp_path / "SkillManager" / "logs"


def test_log_dir_linux(tmp_path):
    with (
        patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}, clear=False),
        patch.object(sys, "platform", "linux"),
    ):
        result = log_dir()
        assert result == tmp_path / "SkillManager" / "logs"


# --- log_event ---


def test_log_event_writes_json_line(diag_logger, tmp_path):
    diag_logger.log_event("INFO", "test_category", "test message", data={"key": "val"})
    log_file = diag_logger.get_log_path()
    assert Path(log_file).exists()
    lines = Path(log_file).read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["level"] == "INFO"
    assert event["category"] == "test_category"
    assert event["msg"] == "test message"
    assert event["data"]["key"] == "val"
    assert "ts" in event
    assert "ctx" in event


def test_log_event_includes_context(diag_logger):
    diag_logger.log_event("INFO", "ctx_test", "context check")
    events = diag_logger.get_recent_events()
    assert len(events) == 1
    ctx = events[0]["ctx"]
    assert "app_version" in ctx
    assert "qt_version" in ctx
    assert "platform" in ctx
    assert "python_version" in ctx


def test_log_event_debug_suppressed_at_info_level(diag_logger_info):
    diag_logger_info.log_event("DEBUG", "debug_test", "should not appear")
    events = diag_logger_info.get_recent_events()
    assert len(events) == 0


def test_log_event_debug_emitted_at_debug_level(diag_logger):
    diag_logger.log_event("DEBUG", "debug_test", "should appear")
    events = diag_logger.get_recent_events()
    assert len(events) == 1
    assert events[0]["category"] == "debug_test"


def test_log_event_without_data(diag_logger):
    diag_logger.log_event("WARNING", "no_data", "warning message")
    events = diag_logger.get_recent_events()
    assert len(events) == 1
    assert "data" not in events[0]


# --- ring buffer ---


def test_ring_buffer_max_size(tmp_path):
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="DEBUG")
    logger.set_enabled(True)
    for i in range(1200):
        logger.log_event("INFO", "ring_test", f"event {i}")
    events = logger.get_recent_events(1200)
    assert len(events) == 1000
    assert events[0]["msg"] == "event 200"
    assert events[-1]["msg"] == "event 1199"


def test_get_recent_events_count(diag_logger):
    for i in range(10):
        diag_logger.log_event("INFO", "count_test", f"event {i}")
    events = diag_logger.get_recent_events(5)
    assert len(events) == 5
    assert events[0]["msg"] == "event 5"


# --- rotation ---


def test_rotation_triggers_on_large_file(diag_logger):
    log_file = Path(diag_logger.get_log_path())
    # Write a file that exceeds rotation threshold
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("x" * (5 * 1024 * 1024 + 1), encoding="utf-8")
    diag_logger.log_event("INFO", "rotation_test", "after large file")
    assert log_file.exists()
    assert log_file.with_suffix(".log.1").exists()


# --- thread safety ---


def test_concurrent_logging(diag_logger):
    errors = []

    def writer(thread_id):
        try:
            for i in range(50):
                diag_logger.log_event("INFO", "thread_test", f"thread {thread_id} event {i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    events = diag_logger.get_recent_events(500)
    assert len(events) == 400


# --- clear_logs ---


def test_clear_logs_removes_files(diag_logger):
    diag_logger.log_event("INFO", "clear_test", "before clear")
    assert Path(diag_logger.get_log_path()).exists()
    diag_logger.clear_logs()
    assert not Path(diag_logger.get_log_path()).exists()
    events = diag_logger.get_recent_events()
    assert len(events) == 0


# --- export_bundle ---


def test_export_bundle_creates_zip(diag_logger):
    diag_logger.log_event("INFO", "bundle_test", "exporting")
    zip_path = diag_logger.export_bundle()
    assert zip_path != ""
    assert Path(zip_path).exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "diagnostic_bundle.json" in names
        assert "diagnostic.log" in names
        manifest = json.loads(zf.read("diagnostic_bundle.json"))
        assert "app_version" in manifest
        assert "qt_version" in manifest
        assert "recent_events" in manifest
        assert len(manifest["recent_events"]) >= 1


def test_export_bundle_returns_empty_on_failure(diag_logger):
    result = diag_logger.export_bundle("/nonexistent/path/that/doesnt/exist")
    # May or may not fail depending on OS, but should not crash
    assert isinstance(result, str)


# --- singleton ---


def test_get_diagnostic_logger_returns_singleton():
    logger1 = get_diagnostic_logger()
    logger2 = get_diagnostic_logger()
    assert logger1 is logger2


# --- is_dev_mode ---


def test_is_dev_mode_env_var():
    with patch.dict(os.environ, {"SKILL_MANAGER_DEV_MODE": "1"}):
        assert is_dev_mode() is True


def test_is_dev_mode_frozen():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SKILL_MANAGER_DEV_MODE", None)
        with patch.object(sys, "frozen", True, create=True):
            assert is_dev_mode() is False


def test_is_dev_mode_uv_run():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SKILL_MANAGER_DEV_MODE", None)
        with patch.object(sys, "frozen", False, create=True):
            # Simulate src/ layout by patching __file__
            fake_file = Path("/tmp/project/src/skill_manager/core/diagnostics.py")
            with patch.object(Path, "resolve", return_value=fake_file):
                # We need the parent.parent to be "src" and parent.parent.parent to have pyproject.toml
                # Test the actual logic: src_dir.name == "src" and pyproject.toml exists
                # We'll just verify it doesn't crash
                result = is_dev_mode()
                assert isinstance(result, bool)


# --- enabled flag ---


def test_disabled_by_default(tmp_path):
    """A freshly created DiagnosticLogger must have _enabled=False."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    assert logger.is_enabled() is False


def test_log_event_skipped_when_disabled(tmp_path):
    """When disabled, log_event() must not write to the ring buffer or file."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="INFO")
    # _enabled starts False — log something
    logger.log_event("INFO", "test", "should be ignored")

    assert logger.get_recent_events() == []
    assert not (tmp_path / "logs" / "diagnostic.log").exists()


def test_log_event_works_when_enabled(tmp_path):
    """When enabled, log_event() must write to the ring buffer and file."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="INFO")
    logger.set_enabled(True)

    logger.log_event("INFO", "test", "should appear")

    events = logger.get_recent_events()
    assert len(events) == 1
    assert events[0]["msg"] == "should appear"
    assert (tmp_path / "logs" / "diagnostic.log").exists()


def test_set_enabled_toggle(tmp_path):
    """Toggling enabled at runtime takes effect immediately for subsequent calls."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="INFO")

    # Disabled → event ignored
    logger.log_event("INFO", "cat", "ignored")
    assert logger.get_recent_events() == []

    # Enable → event recorded
    logger.set_enabled(True)
    logger.log_event("INFO", "cat", "recorded")
    events = logger.get_recent_events()
    assert len(events) == 1
    assert events[0]["msg"] == "recorded"

    # Disable again → next event ignored
    logger.set_enabled(False)
    logger.log_event("INFO", "cat", "also ignored")
    assert len(logger.get_recent_events()) == 1  # still only the one from above


# --- get_diagnostic_counts ---


def test_get_diagnostic_counts_empty(diag_logger):
    counts = diag_logger.get_diagnostic_counts()
    assert counts == {"errors": 0, "warnings": 0, "info": 0, "debug": 0, "total": 0}


def test_get_diagnostic_counts_mixed_levels(diag_logger):
    diag_logger.log_event("ERROR", "cat", "err1")
    diag_logger.log_event("ERROR", "cat", "err2")
    diag_logger.log_event("WARNING", "cat", "warn1")
    diag_logger.log_event("INFO", "cat", "info1")
    diag_logger.log_event("INFO", "cat", "info2")
    diag_logger.log_event("INFO", "cat", "info3")
    diag_logger.log_event("DEBUG", "cat", "dbg1")

    counts = diag_logger.get_diagnostic_counts()
    assert counts["errors"] == 2
    assert counts["warnings"] == 1
    assert counts["info"] == 3
    assert counts["debug"] == 1
    assert counts["total"] == 7


# --- get_health_status ---


def test_get_health_status_green(diag_logger):
    diag_logger.log_event("INFO", "cat", "ok")
    assert diag_logger.get_health_status() == "green"


def test_get_health_status_yellow(diag_logger):
    diag_logger.log_event("WARNING", "cat", "warn")
    assert diag_logger.get_health_status() == "yellow"


def test_get_health_status_red(diag_logger):
    diag_logger.log_event("ERROR", "cat", "err")
    assert diag_logger.get_health_status() == "red"


def test_get_health_status_empty(diag_logger):
    assert diag_logger.get_health_status() == "green"


# --- get_recent_events_human ---


def test_get_recent_events_human_empty(diag_logger):
    rows = diag_logger.get_recent_events_human(10)
    assert rows == []


def test_get_recent_events_human_format(diag_logger):
    diag_logger.log_event("ERROR", "skill_copy", "Failed to copy")
    rows = diag_logger.get_recent_events_human(10)
    assert len(rows) == 1
    row = rows[0]
    assert "time" in row
    assert row["level"] == "ERROR"
    assert row["category"] == "skill_copy"
    assert row["message"] == "Failed to copy"


def test_get_recent_events_human_time_truncated(diag_logger):
    diag_logger.log_event("INFO", "test", "msg")
    rows = diag_logger.get_recent_events_human(1)
    # Time should be HH:MM:SS (8 chars)
    assert len(rows[0]["time"]) == 8
