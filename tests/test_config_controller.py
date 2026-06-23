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
    assert any("C:\project" in p for p in mock_app._projects)
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
        # ``resetShortcuts`` writes both ``shortcuts`` and
        # ``disabled_shortcuts`` (in that order). The original test
        # used ``assert_called_with`` which only inspects the *last*
        # call — that pattern was broken when the
        # ``disabled_shortcuts`` write was added. Use
        # ``assert_any_call`` so we verify the desired write happened
        # at any point during ``resetShortcuts``.
        mock_app._config.set.assert_any_call("shortcuts", {"search": "Ctrl+F"})


def test_config_controller_shortcut_enabled(config_controller, mock_app):
    """Test isShortcutEnabled returns True when action is not disabled."""
    mock_app._config.get.side_effect = lambda key, default=None: {"disabled_shortcuts": []}.get(
        key, default
    )
    assert config_controller.isShortcutEnabled("search") is True

    mock_app._config.get.side_effect = lambda key, default=None: {
        "disabled_shortcuts": ["search", "copy"]
    }.get(key, default)
    assert config_controller.isShortcutEnabled("search") is False
    assert config_controller.isShortcutEnabled("archive") is True

    # Missing key defaults to empty list
    mock_app._config.get.side_effect = lambda key, default=None: default
    assert config_controller.isShortcutEnabled("anything") is True


def test_config_controller_set_shortcut_enabled(config_controller, mock_app):
    """Test setShortcutEnabled toggles disabled_shortcuts list."""
    mock_app._config.get.side_effect = lambda key, default=None: {"disabled_shortcuts": []}.get(
        key, default
    )

    # Disable an action
    config_controller.setShortcutEnabled("search", False)
    mock_app._config.set.assert_called_with("disabled_shortcuts", ["search"])

    # Enable it again
    mock_app._config.get.side_effect = lambda key, default=None: {
        "disabled_shortcuts": ["search"]
    }.get(key, default)
    config_controller.setShortcutEnabled("search", True)
    mock_app._config.set.assert_called_with("disabled_shortcuts", [])


def test_config_controller_set_shortcut_enabled_noop(config_controller, mock_app):
    """setShortcutEnabled is a no-op when state is already correct."""
    mock_app._config.get.side_effect = lambda key, default=None: {"disabled_shortcuts": []}.get(
        key, default
    )

    # Enable when already enabled → no set call
    mock_app._config.set.reset_mock()
    config_controller.setShortcutEnabled("search", True)
    mock_app._config.set.assert_not_called()

    # Disable when already disabled → no set call
    mock_app._config.get.side_effect = lambda key, default=None: {
        "disabled_shortcuts": ["search"]
    }.get(key, default)
    mock_app._config.set.reset_mock()
    config_controller.setShortcutEnabled("search", False)
    mock_app._config.set.assert_not_called()


def test_config_controller_reset_shortcuts_clears_disabled(config_controller, mock_app):
    """resetShortcuts should also clear disabled_shortcuts."""
    with (
        patch("skill_manager.core.config.DEFAULT_SHORTCUTS", {"search": "Ctrl+F"}),
        patch("skill_manager.core.config.DEFAULT_DISABLED_SHORTCUTS", []),
    ):
        config_controller.resetShortcuts()
        mock_app._config.set.assert_any_call("disabled_shortcuts", [])


def test_config_controller_custom_collections(config_controller, mock_app):
    mock_app._custom_collections = {}

    # Save collection
    config_controller.saveCustomCollection("MyColl", ["/path/1", "/path/2"], ["ProjectA"])
    assert mock_app._custom_collections["MyColl"] == {
        "paths": ["/path/1", "/path/2"],
        "projects": ["ProjectA"],
        "shortcut": "",
        "shortcut_enabled": True,
    }
    mock_app._config.set.assert_called_with("custom_collections", mock_app._custom_collections)

    # Delete collection
    config_controller.deleteCustomCollection("MyColl")
    assert "MyColl" not in mock_app._custom_collections

    # Apply selection
    mock_app._custom_collections = {"MyColl": {"paths": ["/path/1"], "projects": []}}
    config_controller.applyCollectionSelection("MyColl")
    mock_app.skillModel.clearSelection.assert_called_once()
    mock_app.skillModel.selectByPaths.assert_called_with(["/path/1"])


def test_config_controller_properties_setters(config_controller, mock_app):
    config_controller.scrollSpeedMultiplier = 2.0
    mock_app._config.set.assert_any_call("scroll_speed_multiplier", 2.0)

    config_controller.skillPackageAutoUpdateMode = "silent"
    mock_app._config.set.assert_any_call("skill_package_auto_update_mode", "silent")

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
    with patch.object(config_controller.config, "set", side_effect=OSError("Access denied")):
        config_controller.addSource("/bad/path")
        mock_app._set_status.assert_called_with("Failed to add source: Access denied")


def test_config_controller_get_collection_paths_empty(config_controller, mock_app):
    mock_app._custom_collections = {"Coll1": ["/p1"]}
    assert config_controller.getCollectionPaths("Coll1") == ["/p1"]
    assert config_controller.getCollectionPaths("Missing") == []


def test_config_controller_reorder_projects(config_controller, mock_app):
    mock_app._projects = ["/path/a", "/path/b", "/path/c"]
    config_controller.reorderProjects(0, 2)
    assert mock_app._projects == ["/path/b", "/path/c", "/path/a"]
    mock_app.projectsChanged.emit.assert_called_once()
    mock_app._config.set.assert_called_with("projects", mock_app._projects)


def test_config_controller_reorder_projects_move_down(config_controller, mock_app):
    mock_app._projects = ["/path/a", "/path/b", "/path/c"]
    config_controller.reorderProjects(2, 0)
    assert mock_app._projects == ["/path/c", "/path/a", "/path/b"]
    mock_app.projectsChanged.emit.assert_called_once()


def test_config_controller_reorder_projects_adjacent(config_controller, mock_app):
    mock_app._projects = ["/path/a", "/path/b", "/path/c"]
    config_controller.reorderProjects(0, 1)
    assert mock_app._projects == ["/path/b", "/path/a", "/path/c"]
    mock_app.projectsChanged.emit.assert_called_once()


def test_config_controller_reorder_projects_same_index(config_controller, mock_app):
    mock_app._projects = ["/path/a", "/path/b"]
    config_controller.reorderProjects(1, 1)
    assert mock_app._projects == ["/path/a", "/path/b"]
    mock_app.projectsChanged.emit.assert_not_called()


def test_config_controller_reorder_projects_out_of_bounds(config_controller, mock_app):
    mock_app._projects = ["/path/a", "/path/b"]
    config_controller.reorderProjects(0, 99)
    assert mock_app._projects == ["/path/a", "/path/b"]
    mock_app.projectsChanged.emit.assert_not_called()

    config_controller.reorderProjects(-1, 1)
    assert mock_app._projects == ["/path/a", "/path/b"]
    mock_app.projectsChanged.emit.assert_not_called()


def test_config_controller_reorder_projects_empty(config_controller, mock_app):
    mock_app._projects = []
    config_controller.reorderProjects(0, 0)
    mock_app.projectsChanged.emit.assert_not_called()


def test_set_config_value_emits_signal_instance(config_controller, mock_app):
    """``_set_config_value`` must emit the supplied ``SignalInstance`` when value changes.

    Regression for the LSP errors that the PySide6 ``Signal`` stub
    produced when ``_set_config_value`` was annotated with the
    ``Signal`` factory class instead of the runtime ``SignalInstance``.
    The runtime argument is always a ``SignalInstance`` (from the
    controller's ``*Changed`` class attribute), so the parameter type
    must match.
    """
    mock_app._config.get.return_value = "old_value"
    signal = MagicMock()
    result = config_controller._set_config_value("scroll_speed_multiplier", 2.5, signal)
    assert result is True
    signal.emit.assert_called_once()


def test_set_config_value_no_emit_when_unchanged(config_controller, mock_app):
    """``_set_config_value`` must not emit when the validated value is unchanged.

    Guards the ``if self.config.get(key) != final_value`` dedupe branch
    in ``_set_config_value`` and the ``if signal: signal.emit()`` guard.
    """
    # Use 1.0 because ``scroll_speed_multiplier``'s before-validator
    # coerces strings via ``float(value)`` and falls back to ``1.0`` on
    # failure — so to compare apples-to-apples we set both sides to the
    # same float value.
    mock_app._config.get.return_value = 1.0
    signal = MagicMock()
    result = config_controller._set_config_value("scroll_speed_multiplier", 1.0, signal)
    assert result is False
    signal.emit.assert_not_called()


def test_set_config_value_no_emit_when_signal_is_none(config_controller, mock_app):
    """``_set_config_value`` must accept ``None`` for the signal parameter.

    The default-value ``None`` branch must not raise — verified by
    actually invoking the helper with a changed value and a ``None``
    signal. This regression test guards the ``if signal: signal.emit()``
    short-circuit in ``_set_config_value``.
    """
    mock_app._config.get.return_value = "old"
    result = config_controller._set_config_value("scroll_speed_multiplier", "new", None)
    assert result is True
    mock_app._config.set.assert_called_once()


# --- Per-collection shortcut tests ---


def test_set_collection_shortcut_saves(config_controller, mock_app):
    """Setting a shortcut persists it on the collection entry."""
    mock_app._custom_collections = {
        "MyColl": {"paths": ["/p1"], "projects": [], "shortcut": "", "shortcut_enabled": True}
    }
    mock_app._config.get.return_value = {"search": "Ctrl+F"}

    config_controller.setCollectionShortcut("MyColl", "Ctrl+Shift+K")
    assert mock_app._custom_collections["MyColl"]["shortcut"] == "Ctrl+Shift+K"
    mock_app._config.set.assert_any_call("custom_collections", mock_app._custom_collections)
    mock_app._set_status.assert_called_once()


def test_set_collection_shortcut_auto_claims_built_in(config_controller, mock_app):
    """Assigning a sequence already used by a built-in action frees it."""
    mock_app._custom_collections = {
        "Snippets": {"paths": ["/p1"], "projects": [], "shortcut": "", "shortcut_enabled": True}
    }
    shortcuts = {"search": "Ctrl+F", "copy": "Ctrl+C"}
    mock_app._config.get.return_value = shortcuts

    config_controller.setCollectionShortcut("Snippets", "Ctrl+C")
    # Built-in 'copy' should be cleared
    mock_app._config.set.assert_any_call("shortcuts", {"search": "Ctrl+F", "copy": ""})
    # Collection should have the sequence
    assert mock_app._custom_collections["Snippets"]["shortcut"] == "Ctrl+C"


def test_set_collection_shortcut_auto_claims_other_collection(config_controller, mock_app):
    """Assigning a sequence used by another collection frees it."""
    mock_app._custom_collections = {
        "CollA": {
            "paths": ["/a"],
            "projects": [],
            "shortcut": "Ctrl+Shift+Z",
            "shortcut_enabled": True,
        },
        "CollB": {"paths": ["/b"], "projects": [], "shortcut": "", "shortcut_enabled": True},
    }
    mock_app._config.get.return_value = {}

    config_controller.setCollectionShortcut("CollB", "Ctrl+Shift+Z")
    assert mock_app._custom_collections["CollA"]["shortcut"] == ""
    assert mock_app._custom_collections["CollB"]["shortcut"] == "Ctrl+Shift+Z"


def test_set_collection_shortcut_noop_when_unchanged(config_controller, mock_app):
    """No-op when the sequence is the same as what's already stored."""
    mock_app._custom_collections = {
        "MyColl": {"paths": ["/p1"], "projects": [], "shortcut": "Ctrl+K", "shortcut_enabled": True}
    }
    mock_app._config.get.return_value = {}
    mock_app._config.set.reset_mock()

    config_controller.setCollectionShortcut("MyColl", "Ctrl+K")
    mock_app._config.set.assert_not_called()


def test_set_collection_shortcut_enabled_toggles_flag(config_controller, mock_app):
    """Toggling enabled flips the flag and persists."""
    mock_app._custom_collections = {
        "MyColl": {"paths": ["/p1"], "projects": [], "shortcut": "Ctrl+K", "shortcut_enabled": True}
    }

    config_controller.setCollectionShortcutEnabled("MyColl", False)
    assert mock_app._custom_collections["MyColl"]["shortcut_enabled"] is False
    mock_app._config.set.assert_called_with("custom_collections", mock_app._custom_collections)

    mock_app._config.set.reset_mock()
    config_controller.setCollectionShortcutEnabled("MyColl", True)
    assert mock_app._custom_collections["MyColl"]["shortcut_enabled"] is True


def test_reset_shortcuts_clears_collection_shortcuts(config_controller, mock_app):
    """resetShortcuts must clear all collection shortcuts."""
    mock_app._custom_collections = {
        "CollA": {"paths": ["/a"], "projects": [], "shortcut": "Ctrl+K", "shortcut_enabled": True},
        "CollB": {
            "paths": ["/b"],
            "projects": [],
            "shortcut": "Ctrl+Shift+L",
            "shortcut_enabled": False,
        },
    }
    mock_app._config.get.return_value = {"disabled_shortcuts": []}

    with (
        patch("skill_manager.core.config.DEFAULT_SHORTCUTS", {"search": "Ctrl+F"}),
        patch("skill_manager.core.config.DEFAULT_DISABLED_SHORTCUTS", []),
    ):
        config_controller.resetShortcuts()

    assert mock_app._custom_collections["CollA"]["shortcut"] == ""
    assert mock_app._custom_collections["CollA"]["shortcut_enabled"] is True
    assert mock_app._custom_collections["CollB"]["shortcut"] == ""
    assert mock_app._custom_collections["CollB"]["shortcut_enabled"] is True
