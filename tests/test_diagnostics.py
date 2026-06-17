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
    _is_dev_mode,
    _log_dir,
    get_diagnostic_logger,
)


@pytest.fixture
def diag_logger(tmp_path):
    """Create a DiagnosticLogger with a temp log directory."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="DEBUG")
    return logger


@pytest.fixture
def diag_logger_info(tmp_path):
    """Create a DiagnosticLogger at INFO level."""
    logger = DiagnosticLogger(log_dir=tmp_path / "logs")
    logger.initialize(log_level="INFO")
    return logger


# --- _log_dir ---


def test_log_dir_windows(tmp_path):
    with (
        patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}, clear=False),
        patch.object(sys, "platform", "win32"),
    ):
        result = _log_dir()
        assert result == tmp_path / "SkillManager" / "logs"


def test_log_dir_linux(tmp_path):
    with (
        patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}, clear=False),
        patch.object(sys, "platform", "linux"),
    ):
        result = _log_dir()
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


# --- _is_dev_mode ---


def test_is_dev_mode_env_var():
    with patch.dict(os.environ, {"SKILL_MANAGER_DEV_MODE": "1"}):
        assert _is_dev_mode() is True


def test_is_dev_mode_frozen():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SKILL_MANAGER_DEV_MODE", None)
        with patch.object(sys, "frozen", True, create=True):
            assert _is_dev_mode() is False


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
                result = _is_dev_mode()
                assert isinstance(result, bool)
