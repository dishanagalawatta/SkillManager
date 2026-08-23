from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from watchdog.events import FileModifiedEvent

from skill_manager.core.file_watch import SkillFolderEventHandler, SkillFolderWatcher


def test_skill_folder_event_handler():
    """Handler only fires for `.agents` relative paths and .md files/directories."""
    mock_callback = Mock()
    handler = SkillFolderEventHandler(mock_callback, debounce_ms=0)

    md_event = FileModifiedEvent("/tmp/proj/.agents/skills/my-skill/SKILL.md")
    handler.on_any_event(md_event)
    mock_callback.assert_called_with(md_event.src_path)

    mock_callback.reset_mock()

    dir_event = FileModifiedEvent("/tmp/proj/.agents/skills/new-skill")
    dir_event.is_directory = True
    handler.on_any_event(dir_event)
    mock_callback.assert_called_with(dir_event.src_path)

    mock_callback.reset_mock()

    txt_event = FileModifiedEvent("/tmp/proj/.agents/skills/test.txt")
    handler.on_any_event(txt_event)
    mock_callback.assert_not_called()

    # Irrelevant paths (frontend, tests, etc.) must be ignored even if .md
    mock_callback.reset_mock()
    irrelevant_md = FileModifiedEvent("/tmp/proj/frontend/README.md")
    handler.on_any_event(irrelevant_md)
    mock_callback.assert_not_called()

    irrelevant_dir = FileModifiedEvent("/tmp/proj/frontend")
    irrelevant_dir.is_directory = True
    handler.on_any_event(irrelevant_dir)
    mock_callback.assert_not_called()


def test_skill_folder_event_handler_deleted_and_moved_filtering():
    mock_callback = Mock()
    handler = SkillFolderEventHandler(mock_callback, debounce_ms=0)

    deleted = FileModifiedEvent("/tmp/proj/.agents/skills/old-skill")
    deleted.is_directory = True
    handler.on_deleted(deleted)
    mock_callback.assert_called_with(deleted.src_path)

    mock_callback.reset_mock()
    deleted_outside = FileModifiedEvent("/tmp/proj/frontend")
    deleted_outside.is_directory = True
    handler.on_deleted(deleted_outside)
    mock_callback.assert_not_called()

    mock_callback.reset_mock()
    moved = FileModifiedEvent("/tmp/proj/.agents/skills/a")
    moved.is_directory = True
    moved.dest_path = "/tmp/proj/.agents/skills/b"
    handler.on_moved(moved)
    mock_callback.assert_called()

    mock_callback.reset_mock()
    moved_outside = FileModifiedEvent("/tmp/proj/frontend")
    moved_outside.dest_path = "/tmp/proj/backend"
    handler.on_moved(moved_outside)
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
