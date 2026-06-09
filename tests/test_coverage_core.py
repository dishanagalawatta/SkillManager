import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from skill_manager.core.config import (
    DEFAULT_SHORTCUTS,
    ConfigManager,
    get_app_data_dir,
    resolve_data_file,
)
from skill_manager.core.updater import update_projects


def test_update_projects_invalid_paths(caplog):
    # Test skipping non-existent paths
    update_projects(["missing_proj"], ["missing_src"])
    assert "Project path 'missing_proj' is not a directory" in caplog.text
    assert "Source path 'missing_src' is not a directory" in caplog.text
    assert "No valid project directories provided." in caplog.text


def test_update_projects_empty_sources(caplog):
    update_projects([], ["missing_src"])
    assert "No valid project directories provided." in caplog.text

    fresh_proj = MagicMock(spec=Path)
    fresh_proj.is_dir.return_value = True
    with (
        patch("skill_manager.core.updater.Path", return_value=fresh_proj),
        patch("skill_manager.core.updater.Path.resolve", return_value=fresh_proj),
    ):
        update_projects(["/valid_proj"], [])
        assert "No valid source directories provided." in caplog.text


def test_update_projects_with_progress_callback(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "item").mkdir()
    src = tmp_path / "src"
    src.mkdir()
    (src / "item").mkdir()

    calls = []

    def callback(current, total, msg):
        calls.append((current, total, msg))

    result = update_projects([str(proj)], [str(src)], progress_callback=callback)
    assert result == (1, 0)
    assert len(calls) >= 2


def test_update_projects_error_handling(tmp_path, caplog):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "item").mkdir()
    src = tmp_path / "src"
    src.mkdir()
    (src / "item").mkdir()

    # Trigger exception in copytree
    with patch("shutil.copytree", side_effect=RuntimeError("Copy failed")):
        update_projects([str(proj)], [str(src)])

    assert "Error updating 'item': Copy failed" in caplog.text


def test_get_app_data_dir_fallbacks(monkeypatch):
    monkeypatch.delenv("SKILL_MANAGER_DATA_DIR", raising=False)
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    # Use PurePath or just mock the entire return of Path.home()
    mock_home = MagicMock(spec=Path)
    # Mock the / operator behavior: mock_home / ".local" -> another mock
    mock_local = MagicMock(spec=Path)
    mock_share = MagicMock(spec=Path)
    mock_app = MagicMock(spec=Path)

    mock_home.__truediv__.return_value = mock_local
    mock_local.__truediv__.return_value = mock_share
    mock_share.__truediv__.return_value = mock_app

    with patch("pathlib.Path.home", return_value=mock_home):
        app_dir = get_app_data_dir()
        # It should have called home() / ".local" / "share" / APP_NAME
        assert app_dir == mock_app


def test_resolve_data_file_copy_error(tmp_path):
    data_dir = tmp_path / "data"
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "test.json").write_text("{}")

    # Mock copy2 to raise OSError
    with patch("shutil.copy2", side_effect=OSError("Copy failed")):
        # Should return legacy_path instead of target_path on failure
        res = resolve_data_file("test.json", data_dir, legacy_dir)
        assert res == legacy_dir / "test.json"


def test_config_manager_migration(tmp_path):
    # Create a separate directory for app data
    app_data_dir = tmp_path / "app_data"
    app_data_dir.mkdir()

    # Create a root config in a "current working directory"
    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()
    root_config = cwd_dir / "config.json"
    root_config.write_text('{"targets": ["a"]}')

    # Mock get_app_data_dir to return our temp app_data_dir
    with (
        patch("skill_manager.core.config.get_app_data_dir", return_value=app_data_dir),
        patch("pathlib.Path.cwd", return_value=cwd_dir),
    ):
        # Also need to make sure resolve_data_file sees the mock
        cm = ConfigManager("config.json")
        # Should have migrated targets to projects
        assert cm.get("projects") == ["a"]
        # New config should exist in app_data_dir
        assert (app_data_dir / "config.json").exists()


def test_config_manager_shortcut_merging(tmp_path):
    config_file = tmp_path / "config.json"
    # Partial shortcuts
    config_file.write_text('{"shortcuts": {"search": "Ctrl+Shift+F"}}')

    cm = ConfigManager(str(config_file))
    shortcuts = cm.get("shortcuts")
    assert shortcuts["search"] == "Ctrl+Shift+F"  # Preserved
    assert shortcuts["copy"] == DEFAULT_SHORTCUTS["copy"]  # Merged from default


def test_config_manager_save_error(tmp_path, caplog):
    config_file = tmp_path / "config.json"
    cm = ConfigManager(str(config_file))

    with patch("builtins.open", side_effect=OSError("Permission denied")):
        cm.save()

    assert "Error saving config: Permission denied" in caplog.text
