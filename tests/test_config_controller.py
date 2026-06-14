from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.config_controller import ConfigController


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._sources = []
    app._projects = []
    app._project_aliases = {}
    app._syncing_projects = []
    app._config = MagicMock()
    return app


@pytest.fixture
def config_controller(mock_app):
    return ConfigController(mock_app)


def test_config_controller_add_source(config_controller, mock_app):
    config_controller.addSource("/path/to/source")
    # abspath will normalize path based on platform, so we normalize for the test
    import os

    expected = os.path.abspath("/path/to/source")
    assert expected in mock_app._sources
    mock_app._config.set.assert_called_with("sources", mock_app._sources)
    mock_app.sourcesChanged.emit.assert_called_once()


def test_config_controller_remove_source(config_controller, mock_app):
    mock_app._sources = ["/path/1"]
    config_controller.removeSource("/path/1")
    assert "/path/1" not in mock_app._sources
    mock_app.sourcesChanged.emit.assert_called_once()


def test_config_controller_add_project(config_controller, mock_app):
    config_controller.addProject("file:///C:/project")
    assert "C:\\project" in mock_app._projects
    mock_app.projectsChanged.emit.assert_called_once()


def test_config_controller_get_project_label(config_controller, mock_app):
    mock_app._project_aliases = {"C:\\project": "MyProj"}
    assert config_controller.getProjectLabel("C:\\project") == "MyProj"
    import sys

    if sys.platform == "win32":
        assert config_controller.getProjectLabel("C:\\other") == "other"
    else:
        assert config_controller.getProjectLabel("C:\\other") == "C:\\other"


def test_config_controller_set_project_alias(config_controller, mock_app):
    mock_app._library_model = MagicMock()
    mock_app._quick_copy_model = MagicMock()
    config_controller.setProjectAlias("/path/p", "NewName")
    assert mock_app._project_aliases["/path/p"] == "NewName"
    mock_app.projectsChanged.emit.assert_called_once()
    mock_app._library_model._begin_batch.assert_called_once()
    mock_app._library_model._end_batch.assert_called_once()
    mock_app._quick_copy_model._begin_batch.assert_called_once()
    mock_app._quick_copy_model._end_batch.assert_called_once()


def test_config_controller_remove_project(config_controller, mock_app):
    mock_app._projects = ["/path/t"]
    mock_app._project_aliases = {"/path/t": "Alias"}
    mock_app._syncing_projects = ["/path/t"]

    config_controller.removeProject("/path/t")

    assert "/path/t" not in mock_app._projects
    assert "/path/t" not in mock_app._project_aliases
    assert "/path/t" not in mock_app._syncing_projects
    mock_app.projectsChanged.emit.assert_called_once()


def test_config_controller_add_source_invalid(config_controller, mock_app):
    config_controller.addSource("")
    mock_app.sourcesChanged.emit.assert_not_called()


def test_config_controller_add_project_invalid(config_controller, mock_app):
    config_controller.addProject("")
    mock_app.projectsChanged.emit.assert_not_called()


@patch("skill_manager.core.skill_packages.get_git_tag")
def test_config_controller_verify_git_fail(mock_tag, config_controller, mock_app):
    mock_tag.return_value = ""
    res = config_controller.verifyGitPackage("http://git.com")
    assert res == ""
    mock_app._set_status.assert_any_call("Verification failed for: http://git.com")


def test_config_controller_shortcuts(config_controller, mock_app):
    mock_app._config.get.return_value = {"search": "Ctrl+F"}

    assert config_controller.get_shortcut("search") == "Ctrl+F"
    assert config_controller.get_shortcut("nonexistent") == ""

    # Test setShortcut
    config_controller.setShortcut("search", "Ctrl+Shift+F")
    mock_app._config.set.assert_called_with("shortcuts", {"search": "Ctrl+Shift+F"})
    mock_app._set_status.assert_called_with("Shortcut for search set to: Ctrl+Shift+F")

    # Test resetShortcuts
    with patch("skill_manager.core.config.DEFAULT_SHORTCUTS", {"search": "Ctrl+F"}):
        config_controller.resetShortcuts()
        mock_app._config.set.assert_called_with("shortcuts", {"search": "Ctrl+F"})


def test_config_controller_custom_collections(config_controller, mock_app):
    mock_app._custom_collections = {}

    # Save collection
    config_controller.saveCustomCollection("MyColl", ["/path/1", "/path/2"])
    assert mock_app._custom_collections["MyColl"] == ["/path/1", "/path/2"]
    mock_app._config.set.assert_called_with("custom_collections", mock_app._custom_collections)

    # Delete collection
    config_controller.deleteCustomCollection("MyColl")
    assert "MyColl" not in mock_app._custom_collections

    # Apply selection
    mock_app._custom_collections = {"MyColl": ["/path/1"]}
    config_controller.applyCollectionSelection("MyColl")
    mock_app.skillModel.clearSelection.assert_called_once()
    mock_app.skillModel.selectByPaths.assert_called_with(["/path/1"])


def test_config_controller_properties_setters(config_controller, mock_app):
    config_controller.scrollSpeedMultiplier = 2.0
    mock_app._config.set.assert_any_call("scroll_speed_multiplier", 2.0)

    config_controller.showMenuIcons = False
    mock_app._config.set.assert_any_call("show_menu_icons", False)

    config_controller.compactMenu = True
    mock_app._config.set.assert_any_call("compact_menu", True)

    config_controller.autoCheckUpdates = False
    mock_app._config.set.assert_any_call("auto_check_updates", False)

    config_controller.autoDownloadUpdates = True
    mock_app._config.set.assert_any_call("auto_download_updates", True)

    config_controller.updateCheckIntervalHours = 48
    mock_app._config.set.assert_any_call("update_check_interval_hours", 48)

    config_controller.skillPackageAutoUpdate = False
    mock_app._config.set.assert_any_call("skill_package_auto_update", False)

    config_controller.skillPackageAutoUpdateMode = "auto"
    mock_app._config.set.assert_any_call("skill_package_auto_update_mode", "auto")

    config_controller.autoMinimizeOnScreenshot = True
    mock_app._config.set.assert_any_call("auto_minimize_on_screenshot", True)

    config_controller.autoMinimizeOnQuickCopy = True
    mock_app._config.set.assert_any_call("auto_minimize_on_quick_copy", True)

    config_controller.temporaryScreenshots = True
    mock_app._config.set.assert_any_call("temporary_screenshots", True)


def test_config_controller_is_recording_shortcut(config_controller, mock_app):
    mock_app._is_recording_shortcut = False
    config_controller.isRecordingShortcut = True
    assert mock_app._is_recording_shortcut is True


def test_config_controller_remove_source_by_index(config_controller, mock_app):
    mock_app._sources = ["/path/a", "/path/b"]
    config_controller.removeSourceByIndex(0)
    assert "/path/a" not in mock_app._sources

    config_controller.removeSourceByIndex(99)
    assert len(mock_app._sources) == 1


def test_config_controller_add_source_exception(config_controller, mock_app):
    with patch("os.path.abspath", side_effect=OSError("Access denied")):
        config_controller.addSource("/bad/path")
        mock_app._set_status.assert_called_with("Failed to add source: Access denied")


def test_config_controller_get_collection_paths_empty(config_controller, mock_app):
    mock_app._custom_collections = {"Coll1": ["/p1"]}
    assert config_controller.getCollectionPaths("Coll1") == ["/p1"]
    assert config_controller.getCollectionPaths("Missing") == []
