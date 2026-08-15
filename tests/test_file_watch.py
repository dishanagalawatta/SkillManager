from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from watchdog.events import FileModifiedEvent

from skill_manager.core.file_watch import SkillFolderEventHandler, SkillFolderWatcher


def test_skill_folder_event_handler():
    """Test that the handler coalesces events and triggers the callback for markdown files or directories."""
    mock_callback = Mock()
    # Use debounce_ms=0 to test filtering logic without debounce delay
    handler = SkillFolderEventHandler(mock_callback, debounce_ms=0)

    # Trigger with a markdown file
    md_event = FileModifiedEvent("test_skill.md")
    handler.on_any_event(md_event)
    mock_callback.assert_called_with(md_event.src_path)

    mock_callback.reset_mock()

    # Trigger with a directory (this is allowed by the logic)
    dir_event = FileModifiedEvent("some_dir")
    dir_event.is_directory = True
    handler.on_any_event(dir_event)
    mock_callback.assert_called_with(dir_event.src_path)

    mock_callback.reset_mock()

    # Trigger with a non-markdown file
    txt_event = FileModifiedEvent("test.txt")
    handler.on_any_event(txt_event)
    mock_callback.assert_not_called()


def test_skill_folder_watcher(tmp_path: Path):
    """Test that the watcher starts and stops correctly."""
    mock_callback = Mock()
    test_dir = tmp_path / "skills"
    test_dir.mkdir()

    mock_observer_instance = MagicMock()
    with patch("watchdog.observers.Observer", return_value=mock_observer_instance):
        watcher = SkillFolderWatcher([str(test_dir)], mock_callback)

        assert not watcher.started
        watcher.start()
        assert watcher.started
        assert mock_observer_instance.schedule.call_count == 1
        assert mock_observer_instance.start.call_count == 1

        # Start again should be a no-op
        watcher.start()
        assert watcher.started
        assert mock_observer_instance.start.call_count == 1

        watcher.stop()
        assert not watcher.started
        assert mock_observer_instance.stop.call_count == 1

        # Stop again should be a no-op
        watcher.stop()
        assert not watcher.started
        assert mock_observer_instance.stop.call_count == 1


def test_skill_folder_watcher_oserror_handled(tmp_path: Path):
    """Test that OS inotify limits are caught gracefully."""
    mock_callback = Mock()
    test_dir = tmp_path / "skills"
    test_dir.mkdir()

    mock_observer_instance = MagicMock()
    mock_observer_instance.start.side_effect = OSError(24, "inotify instance limit reached")

    with patch("watchdog.observers.Observer", return_value=mock_observer_instance):
        watcher = SkillFolderWatcher([str(test_dir)], mock_callback)
        watcher.start()
        assert not watcher.started
