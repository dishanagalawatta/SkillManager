from unittest.mock import patch

from skill_manager.core.analytics import (
    _get_or_create_device_id,
    capture_event,
    capture_exception,
    get_device_id,
    shutdown,
)
from skill_manager.core.parsing.command import parse_command_md


def test_get_or_create_device_id_handles_errors(tmp_path):
    # Mock DATA_DIR
    with patch("skill_manager.core.config.DATA_DIR", tmp_path):
        device_id_file = tmp_path / "device_id.json"

        # Test case: corrupt JSON
        device_id_file.write_text("corrupt{", encoding="utf-8")
        id1 = _get_or_create_device_id()
        assert id1.startswith("device_")

        # Test case: file write error (should still return a new ID)
        with patch.object(device_id_file.__class__, "write_text", side_effect=OSError("Disk full")):
            id2 = _get_or_create_device_id()
            assert id2.startswith("device_")

def test_analytics_calls_with_no_client():
    # _posthog is None in tests because of the safeguard
    capture_event("test") # Should not raise
    capture_exception(Exception("test")) # Should not raise
    shutdown() # Should not raise

def test_get_device_id_lazy_init():
    with (
        patch("skill_manager.core.analytics._get_or_create_device_id", return_value="mock_id"),
        patch("skill_manager.core.analytics._device_id", None),
    ):
        assert get_device_id() == "mock_id"

def test_parse_command_md_skips_common_files(tmp_path):
    f = tmp_path / "security.md"
    f.write_text("content")
    assert parse_command_md(str(f)) is None

def test_parse_command_md_client_from_formats(tmp_path):
    # Stem 'cursor' is likely in CLIENT_FORMATS
    f = tmp_path / "cursor.md"
    f.write_text("# Command Name\nDescription")

    # Mock CLIENT_FORMATS to ensure 'cursor' is there
    with patch("skill_manager.core.quick_copy.CLIENT_FORMATS", {"cursor": {}}):
        data = parse_command_md(str(f))
        assert data["client"] == "cursor"

def test_parse_command_md_exception_handling(tmp_path):
    f = tmp_path / "bad.md"
    # Trigger exception by mocking open
    with patch("builtins.open", side_effect=RuntimeError("Read error")):
        assert parse_command_md(str(f)) is None
