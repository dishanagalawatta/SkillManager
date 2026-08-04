import sys
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


def test_config_controller_add_source(config_controller, mock_app, tmp_path):
    source_dir = tmp_path / "my_source"
    source_dir.mkdir()
    config_controller.addSource(str(source_dir))

    expected = str(source_dir.resolve())
    assert expected in mock_app._sources
    mock_app._config.set.assert_called_with("sources", mock_app._sources)
    mock_app.sourcesChanged.emit.assert_called_once()


def test_config_controller_remove_source(config_controller, mock_app):
    mock_app._sources = ["/path/1"]
    config_controller.removeSource("/path/1")
    assert "/path/1" not in mock_app._sources
    mock_app.sourcesChanged.emit.assert_called_once()


def test_config_controller_add_project(config_controller, mock_app, tmp_path):
    proj_dir = tmp_path / "my_project"
    proj_dir.mkdir()
    file_url = f"file://{proj_dir.as_posix()}"
    config_controller.addProject(file_url)
    assert any(str(proj_dir.name) in p for p in mock_app._projects)
    mock_app.projectsChanged.emit.assert_called_once()


def test_url_to_local_path_formatting():
    from skill_manager.core.copier import url_to_local_path

    # Posix absolute file URL
    posix_url = "file:///home/dikka/Documents/Project"
    posix_path = url_to_local_path(posix_url).replace("\\", "/")
    if sys.platform == "win32":
        # nturl2path maps /home -> \home (drive-less root-relative), then
        # Path.resolve() prefixes the current drive: only the suffix is
        # stable on Windows.
        assert posix_path.endswith("/home/dikka/Documents/Project")
    else:
        assert posix_path == "/home/dikka/Documents/Project"

    # Windows drive-letter file URL: urlparse puts the drive in netloc for
    # file://C:/..., so the drive must survive conversion on both platforms.
    drive_url = "file://C:/Users/runneradmin/Project"
    drive_path = url_to_local_path(drive_url).replace("\\", "/")
    if sys.platform == "win32":
        assert drive_path == "C:/Users/runneradmin/Project"
    else:
        assert drive_path.endswith("/C:/Users/runneradmin/Project")

    # Non-existent path rejection check
    assert url_to_local_path("") == ""


def test_config_controller_get_project_label(config_controller, mock_app):
    mock_app._project_aliases = {"C:\\project": "MyProj"}
    assert config_controller.getProjectLabel("C:\\project") == "MyProj"

    # Root path without alias: canonical project_label returns "name (.)"
    import sys

    if sys.platform == "win32":
        assert config_controller.getProjectLabel("C:\\other") == "other (.)"
    else:
        assert config_controller.getProjectLabel("/other") == "other (.)"


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


def test_config_controller_add_source_exception(config_controller, mock_app, tmp_path):
    source_dir = tmp_path / "valid_dir"
    source_dir.mkdir()
    with patch.object(config_controller.config, "set", side_effect=OSError("Access denied")):
        config_controller.addSource(str(source_dir))
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


# ── SDET contract (merged from test_config_sdet.py; duplicates pruned) ──


def test_scroll_speed_multiplier_validation(config_controller, mock_app):
    # Valid value
    config_controller.scrollSpeedMultiplier = 2.5
    mock_app._config.set.assert_called_with("scroll_speed_multiplier", 2.5)

    # Below minimum (0.1) -> should still be 0.1 or fallback (Pydantic will coerce)
    # In our schema, ge=0.1.
    mock_app._config.reset_mock()
    config_controller.scrollSpeedMultiplier = 0.05
    # If Pydantic validation fails in _set_config_value, it logs warning and returns False.
    # However, our _coerce_float returns 1.0 on ValueError/TypeError.
    # ge=0.1 is a validation error.
    mock_app._config.set.assert_not_called()

    # String coercion
    mock_app._config.reset_mock()
    config_controller.scrollSpeedMultiplier = "3.14"
    mock_app._config.set.assert_called_with("scroll_speed_multiplier", 3.14)


def test_update_mode_validation(config_controller, mock_app):
    # Valid
    config_controller.skillPackageAutoUpdateMode = "silent"
    mock_app._config.set.assert_called_with("skill_package_auto_update_mode", "silent")

    # Invalid -> fallback to "prompt" via validator
    mock_app._config.reset_mock()
    config_controller.skillPackageAutoUpdateMode = "invalid_mode"
    # Our validator returns "prompt" for unknown strings
    mock_app._config.set.assert_called_with("skill_package_auto_update_mode", "prompt")


def test_add_source_path_normalization(config_controller, mock_app):
    with patch("pathlib.Path.resolve") as mock_resolve:
        mock_resolve.return_value = "/absolute/path"
        config_controller.addSource("file:///relative/path")
        assert "/absolute/path" in mock_app._sources


def test_get_project_label_robustness(config_controller, mock_app):
    # Test standard folder (root path: canonical label includes "(.)")
    assert config_controller.getProjectLabel("/home/user/MyProj") == "MyProj (.)"

    # Test .agents/skills folder
    assert config_controller.getProjectLabel("/home/user/MyProj/.agents/skills") == "MyProj"

    # Test custom alias
    mock_app._project_aliases = {"/path/a": "CustomName"}
    assert config_controller.getProjectLabel("/path/a") == "CustomName"


def test_set_project_alias_updates_models(config_controller, mock_app):
    mock_app._library_model = MagicMock()
    mock_app._quick_copy_model = MagicMock()
    mock_app._library_model._all_skills = [
        {"name": "S1", "project_path": "/proj/1", "project_label": "Old"}
    ]

    config_controller.setProjectAlias("/proj/1", "New")

    assert mock_app._project_aliases["/proj/1"] == "New"
    assert mock_app._library_model._all_skills[0]["project_label"] == "New"
    mock_app._library_model._begin_batch.assert_called()
    mock_app._library_model._end_batch.assert_called()


def test_reset_shortcuts(config_controller, mock_app):
    mock_signal = MagicMock()
    config_controller.shortcutsChanged.connect(mock_signal)

    config_controller.resetShortcuts()
    mock_app._config.set.assert_called()
    # Verify it writes the defaults (DEFAULT_SHORTCUTS) under the
    # ``shortcuts`` key. ``resetShortcuts`` also writes
    # ``disabled_shortcuts`` afterwards, so we have to scan the
    # call list for the ``shortcuts`` write — not just look at the
    # last call (which would be the ``disabled_shortcuts`` write).
    shortcut_calls = [
        call_args
        for call_args in mock_app._config.set.call_args_list
        if call_args[0][0] == "shortcuts"
    ]
    assert shortcut_calls, "resetShortcuts did not write the 'shortcuts' key"
    args = shortcut_calls[0]
    assert "search" in args[0][1]
    mock_signal.assert_called_once()
