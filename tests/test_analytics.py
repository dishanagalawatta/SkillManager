import contextlib
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core import analytics

# ---------------------------------------------------------------------------
# Module-state hygiene (xdist determinism)
# ---------------------------------------------------------------------------
# The MCP profiling tools (skill_manager.mcp.tools.monitor._handle_profile)
# permanently replace analytics.capture_event / capture_exception / capture
# with no-op lambdas to suppress telemetry while profiling — and never
# restore them.  Under pytest-xdist a worker that previously ran such a tool
# (e.g. test_mcp_tools.py) would hand this file a module whose capture
# functions are inert lambdas, making every ``assert_called_once_with`` fail
# with "Called 0 times".  Snapshot the canonical module state at import time
# (collection, before any test executes) and restore it around every test so
# this file is deterministic regardless of what ran earlier in the worker.
_ORIGINAL_ANALYTICS_STATE = {
    "capture_event": analytics.capture_event,
    "capture_exception": analytics.capture_exception,
    "_posthog": analytics._posthog,
    "_device_id": analytics._device_id,
}
# monitor.py also creates a stray ``capture`` attribute via setattr; it is
# not part of the analytics API and must be removed when present.
_STRAY_ANALYTICS_NAMES = ("capture",)


def _restore_analytics_module_state() -> None:
    for _name, _value in _ORIGINAL_ANALYTICS_STATE.items():
        setattr(analytics, _name, _value)
    for _name in _STRAY_ANALYTICS_NAMES:
        with contextlib.suppress(AttributeError):
            delattr(analytics, _name)


@pytest.fixture(autouse=True)
def restore_analytics_module_state():
    """Restore analytics module singletons before and after every test."""
    _restore_analytics_module_state()
    yield
    _restore_analytics_module_state()


@pytest.fixture
def mock_posthog():
    with patch("posthog.Posthog") as mock:
        yield mock


@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("skill_manager.core.config.DATA_DIR", tmp_path)
    return tmp_path


def test_get_or_create_device_id(temp_data_dir):
    # Test creation
    device_id = analytics.get_or_create_device_id()
    assert device_id.startswith("device_")

    device_file = temp_data_dir / "device_id.json"
    assert device_file.exists()

    # Test persistence
    second_id = analytics.get_or_create_device_id()
    assert second_id == device_id


def test_capture_event_no_config():
    # Ensure it doesn't crash when _posthog is None
    with patch("skill_manager.core.analytics._posthog", None):
        analytics.capture_event("test_event")


def test_capture_event_with_config(mock_posthog):
    mock_client = MagicMock()
    with (
        patch("skill_manager.core.analytics._posthog", mock_client),
        patch("skill_manager.core.analytics.get_device_id", return_value="test_dev"),
    ):
        analytics.capture_event("test_event", {"prop": 1})
        mock_client.capture.assert_called_once_with(
            distinct_id="test_dev",
            event="test_event",
            properties={"prop": 1},
        )


def test_capture_exception(mock_posthog):
    mock_client = MagicMock()
    with (
        patch("skill_manager.core.analytics._posthog", mock_client),
        patch("skill_manager.core.analytics.get_device_id", return_value="test_dev"),
    ):
        exc = ValueError("test")
        analytics.capture_exception(exc)
        mock_client.capture_exception.assert_called_once_with(
            exc,
            distinct_id="test_dev",
        )


def test_get_or_create_device_id_corrupted(temp_data_dir):
    device_file = temp_data_dir / "device_id.json"
    device_file.write_text("invalid json")

    device_id = analytics.get_or_create_device_id()
    assert device_id.startswith("device_")
    assert "device_id" in json.loads(device_file.read_text())


def test_init_posthog_missing_env():
    with patch.dict(
        os.environ,
        {
            "POSTHOG_PROJECT_TOKEN": "",
            "POSTHOG_HOST": "",
            "SKILL_MANAGER_TESTING": "0",
            "PYTEST_CURRENT_TEST": "",
        },
    ):
        assert analytics.init_posthog() is None


def test_init_posthog_success(mock_posthog):
    with patch.dict(
        os.environ,
        {
            "POSTHOG_PROJECT_TOKEN": "tok",
            "POSTHOG_HOST": "host",
            "SKILL_MANAGER_TESTING": "0",
            "PYTEST_CURRENT_TEST": "",
        },
    ):
        client = analytics.init_posthog()
        assert client is not None
        mock_posthog.assert_called_once()
