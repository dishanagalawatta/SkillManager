from pathlib import Path
from unittest.mock import Mock

from watchdog.events import FileModifiedEvent

from skill_manager.core.file_watch import SkillFolderEventHandler, SkillFolderWatcher


def test_skill_folder_event_handler():
    """Test that the handler coalesces events and triggers the callback for markdown files or directories."""
    mock_callback = Mock()
    handler = SkillFolderEventHandler(mock_callback)

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

    watcher = SkillFolderWatcher([str(test_dir)], mock_callback)
    
    assert not watcher._started
    watcher.start()
    assert watcher._started
    
    # Start again should be a no-op
    watcher.start()
    assert watcher._started

    watcher.stop()
    assert not watcher._started
    
    # Stop again should be a no-op
    watcher.stop()
    assert not watcher._started
