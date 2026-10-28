from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.ui_controller import UIController


@pytest.fixture
def ui_controller(mock_app):
    mock_app._config.get.return_value = {}
    return UIController(mock_app)


def test_ui_controller_init(ui_controller):
    assert ui_controller.currentView == "Library"
    assert ui_controller.windowWidth == 1300
    assert ui_controller.windowHeight == 650
    assert ui_controller.inspectorWidth == 0


def test_ui_controller_init_normalization(mock_app):
    mock_app._config.get.return_value = {"current_view": "library"}
    ctrl = UIController(mock_app)
    assert ctrl.currentView == "Library"

    mock_app._config.get.return_value = {"current_view": "quick-copy"}
    ctrl = UIController(mock_app)
    assert ctrl.currentView == "QuickCopy"


def test_ui_controller_save_state(ui_controller, mock_app):
    ui_controller.currentView = "QuickCopy"
    ui_controller.windowWidth = 1400
    ui_controller.saveUiState()

    assert mock_app._config.set.call_count >= 1
    # Verify the last call contains our changes
    last_args = mock_app._config.set.call_args[0]
    assert last_args[0] == "ui_state"
    assert last_args[1]["current_view"] == "QuickCopy"
    assert last_args[1]["window_width"] == 1400
    assert "compact_list_rows" not in last_args[1]


def test_ui_controller_window_geometry_persistence(ui_controller, mock_app):
    """Test that window size (including compact dimensions >= 400x520) and position are stored and saved."""
    ui_controller.windowWidth = 500
    ui_controller.windowHeight = 550
    ui_controller.windowX = 250
    ui_controller.windowY = 300
    ui_controller.saveUiState()

    assert ui_controller.windowWidth == 500
    assert ui_controller.windowHeight == 550
    assert ui_controller.windowX == 250
    assert ui_controller.windowY == 300

    last_args = mock_app._config.set.call_args[0]
    assert last_args[0] == "ui_state"
    assert last_args[1]["window_width"] == 500
    assert last_args[1]["window_height"] == 550
    assert last_args[1]["window_x"] == 250
    assert last_args[1]["window_y"] == 300


@patch("PySide6.QtCore.QTimer.start")
def test_ui_controller_trigger_save(mock_timer_start, ui_controller):
    ui_controller.triggerSave()
    mock_timer_start.assert_called_with(1000)


def test_ui_controller_get_asset_uri_fallback(ui_controller):
    # Use a dummy base path to avoid relative path resolution issues during mock
    with (
        patch("pathlib.Path.exists", side_effect=[False, True]),
        patch("pathlib.Path.as_uri", return_value="file:///assets/brand/logo.png"),
    ):
        uri = ui_controller.getAssetUri("brand/missing.png")
        assert uri == "file:///assets/brand/logo.png"


def test_ui_controller_get_asset_uri_frozen(ui_controller):
    # Mock Path to return controlled objects
    mock_path = MagicMock()
    mock_path.__truediv__.return_value = mock_path
    mock_path.exists.return_value = True
    mock_path.as_uri.return_value = "file:///mock/meipass/assets/icons/icon.png"

    with (
        patch("sys.frozen", True, create=True),
        patch("sys._MEIPASS", "/mock/meipass", create=True),
        patch("skill_manager.controllers.ui_controller.Path", return_value=mock_path),
    ):
        uri = ui_controller.getAssetUri("icons/icon.png")
        assert uri == "file:///mock/meipass/assets/icons/icon.png"


def test_ui_controller_open_path_windows(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "win32"),
        patch("os.startfile", create=True) as mock_startfile,
    ):
        ui_controller.openPath("C:/test.txt")
        mock_startfile.assert_called_with("C:/test.txt")
        mock_app._set_status.assert_called_with("Opened: test.txt")


def test_ui_controller_open_path_failure(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "win32"),
        patch("os.startfile", side_effect=OSError("Access Denied"), create=True),
    ):
        ui_controller.openPath("C:/restricted.txt")
        mock_app._set_status.assert_any_call("Failed to open C:/restricted.txt: Access Denied")


def test_ui_controller_launch_skill(ui_controller, mock_app):
    with (
        patch.object(ui_controller, "openPath") as mock_open,
        patch("skill_manager.controllers.ui_controller.capture_event") as mock_event,
    ):
        ui_controller.launchSkill("/path/to/skill")
        mock_app._set_status.assert_called_with("Launching skill: /path/to/skill")
        mock_event.assert_called_with("skill_launched")
        mock_open.assert_called_with("/path/to/skill")


def test_ui_controller_inspector_width_default(ui_controller):
    assert ui_controller.inspectorWidth == 0


def test_ui_controller_inspector_width_setter(ui_controller, mock_app):
    ui_controller.inspectorWidth = 500
    assert ui_controller.inspectorWidth == 500
    mock_app._config.set.assert_not_called()

    # triggerSave debounces — force save to verify
    ui_controller.saveUiState()
    mock_app._config.set.assert_called_once()
    args = mock_app._config.set.call_args[0]
    assert args[1]["inspector_width"] == 500


def test_ui_controller_inspector_width_rejects_negative(ui_controller):
    ui_controller.inspectorWidth = -100
    assert ui_controller.inspectorWidth == 0


def test_ui_controller_inspector_width_loads_from_config(mock_app):
    mock_app._config.get.return_value = {"inspector_width": 600}
    ctrl = UIController(mock_app)
    assert ctrl.inspectorWidth == 600


def test_ui_controller_inspector_width_reset(ui_controller):
    ui_controller.inspectorWidth = 500
    ui_controller.resetUiState()
    assert ui_controller.inspectorWidth == 0


def test_ui_controller_set_inspector_width_slot(ui_controller):
    ui_controller.setInspectorWidth(450)
    assert ui_controller.state.inspector_width == 450


# ── Persisted side-panel widths ─────────────────────────────────────
# Every side panel (task list, inspectors) remembers its own width so a
# resize survives a restart without a schema change per panel.


def test_get_panel_width_defaults_to_zero(ui_controller):
    assert ui_controller.getPanelWidth("quickcopy.tasks") == 0


def test_set_panel_width_persists_under_ui_state(ui_controller, mock_app):
    ui_controller.setPanelWidth("quickcopy.tasks", 420)

    assert ui_controller.getPanelWidth("quickcopy.tasks") == 420
    mock_app._config.set.assert_not_called()  # debounced

    ui_controller.saveUiState()
    payload = mock_app._config.set.call_args[0][1]
    assert payload["panel_widths"]["quickcopy.tasks"] == 420


def test_panel_widths_are_independent_per_key(ui_controller):
    ui_controller.setPanelWidth("quickcopy.tasks", 420)
    ui_controller.setPanelWidth("inspector.skill", 640)

    assert ui_controller.getPanelWidth("quickcopy.tasks") == 420
    assert ui_controller.getPanelWidth("inspector.skill") == 640


def test_set_panel_width_clamps_values(ui_controller):
    ui_controller.setPanelWidth("quickcopy.tasks", -50)
    assert ui_controller.getPanelWidth("quickcopy.tasks") == 0

    ui_controller.setPanelWidth("quickcopy.tasks", 99999)
    assert ui_controller.getPanelWidth("quickcopy.tasks") == 4096


def test_set_panel_width_ignores_empty_key(ui_controller):
    ui_controller.setPanelWidth("", 400)
    assert ui_controller.state.panel_widths == {}


def test_set_panel_width_zero_clears_the_override(ui_controller):
    """0 means "no override", so the key must not linger as a dead entry."""
    ui_controller.setPanelWidth("quickcopy.tasks", 400)
    ui_controller.setPanelWidth("quickcopy.tasks", 0)

    assert ui_controller.getPanelWidth("quickcopy.tasks") == 0
    assert "quickcopy.tasks" not in ui_controller.state.panel_widths


def test_set_panel_width_rejects_non_numeric(ui_controller):
    """A bad value from QML must log, not raise across the slot boundary."""
    ui_controller.setPanelWidth("quickcopy.tasks", "not-a-number")
    assert ui_controller.getPanelWidth("quickcopy.tasks") == 0


def test_set_panel_width_is_idempotent(ui_controller, mock_app):
    ui_controller.setPanelWidth("quickcopy.tasks", 400)
    ui_controller.setPanelWidth("quickcopy.tasks", 400)

    assert ui_controller.getPanelWidth("quickcopy.tasks") == 400
    mock_app._config.set.assert_not_called()


def test_panel_widths_load_from_config(mock_app):
    mock_app._config.get.return_value = {
        "panel_widths": {"quickcopy.tasks": 360, "inspector.skill": 700}
    }
    ctrl = UIController(mock_app)

    assert ctrl.getPanelWidth("quickcopy.tasks") == 360
    assert ctrl.getPanelWidth("inspector.skill") == 700
    assert ctrl.getPanelWidth("unknown.panel") == 0


def test_reset_ui_state_clears_panel_widths(ui_controller):
    ui_controller.setPanelWidth("quickcopy.tasks", 400)
    ui_controller.resetUiState()

    assert ui_controller.getPanelWidth("quickcopy.tasks") == 0


def test_ui_controller_window_geometry_properties(ui_controller):
    # Width (constraint: ge=400)
    ui_controller.windowWidth = 1100
    assert ui_controller.windowWidth == 1100
    ui_controller.windowWidth = 800  # Valid compact width
    assert ui_controller.windowWidth == 800
    ui_controller.windowWidth = 350  # Below constraint (< 400)
    assert ui_controller.windowWidth == 800

    # Height (constraint: ge=520)
    ui_controller.windowHeight = 700
    assert ui_controller.windowHeight == 700
    ui_controller.windowHeight = 600  # Valid compact height
    assert ui_controller.windowHeight == 600
    ui_controller.windowHeight = 450  # Below constraint (< 520)
    assert ui_controller.windowHeight == 600

    # X and Y
    ui_controller.windowX = 200
    ui_controller.windowY = 300
    assert ui_controller.windowX == 200
    assert ui_controller.windowY == 300


def test_ui_controller_preference_toggles(ui_controller):
    # Dark Mode
    ui_controller.darkMode = True
    assert ui_controller.darkMode is True

    # Reduced Motion
    ui_controller.reducedMotion = True
    assert ui_controller.reducedMotion is True

    # Remember Filters
    ui_controller.rememberFilters = False
    assert ui_controller.rememberFilters is False


def test_telemetry_toggle_persists_and_applies_immediately(ui_controller, monkeypatch):
    """The Settings toggle must persist the choice and take effect at once."""
    applied: list[bool] = []
    monkeypatch.setattr(
        "skill_manager.controllers.ui_controller.set_telemetry_enabled",
        lambda enabled: applied.append(enabled),
    )

    # Default stays telemetry-on; credentials remain the other gate.
    assert ui_controller.telemetryEnabled is True

    ui_controller.setTelemetryEnabled(False)

    assert ui_controller.telemetryEnabled is False
    assert ui_controller.state.telemetry_enabled is False
    # Applied live (no restart) and queued for persistence.
    assert applied == [False]
    assert ui_controller._save_timer.isActive() is True

    # A repeated value is a no-op: no second apply, no second save arm.
    ui_controller.setTelemetryEnabled(False)
    assert applied == [False]


def test_dark_mode_changed_signal_count(ui_controller):
    """darkModeChanged must fire exactly once per value change and zero times on no-op."""
    spy = MagicMock()
    ui_controller.darkModeChanged.connect(spy)

    # Change from default (False) to True — signal fires once
    ui_controller.darkMode = True
    assert spy.call_count == 1

    # No-op: set to True again — signal must not fire
    ui_controller.darkMode = True
    assert spy.call_count == 1

    # Change back to False — signal fires again
    ui_controller.darkMode = False
    assert spy.call_count == 2


def test_ui_controller_set_view_filter(ui_controller, mock_app):
    model = mock_app.skillModel
    ui_controller.setViewFilter("category", "Dev")
    assert model.categoryFilter == "Dev"
    mock_app._set_status.assert_called_with("Filter applied: category = Dev")

    ui_controller.setViewFilter("collection", "true")
    assert model.collectionFilter is True

    ui_controller.setViewFilter("clear", "")
    assert model.categoryFilter == ""
    assert model.collectionFilter is False


def test_ui_controller_clear_view_filters(ui_controller, mock_app):
    model = mock_app.skillModel
    model.filterText = "abc"
    ui_controller.clearViewFilters()
    assert model.filterText == ""
    mock_app._set_status.assert_called_with("Filters cleared")


def test_ui_controller_selection_proxies(ui_controller, mock_app):
    model = mock_app.skillModel
    model.selectedCount = 5

    ui_controller.selectAllVisibleSkills()
    model.selectAll.assert_called_once()

    ui_controller.clearVisibleSelection()
    model.clearSelection.assert_called_once()

    ui_controller.toggleAllVisibleCategories()
    model.toggleAll.assert_called_once()


def test_ui_controller_model_for_view(ui_controller, mock_app):
    assert ui_controller._modelForView("Library") == mock_app._library_model
    assert ui_controller._modelForView("QuickCopy") == mock_app._quick_copy_model
    assert ui_controller._modelForView("Unknown") == mock_app._library_model  # Default fallback


def test_ui_controller_reset_state_complex(ui_controller, mock_app):
    ui_controller.windowWidth = 1500
    ui_controller.darkMode = True
    ui_controller.resetUiState()

    assert ui_controller.windowWidth == 1300
    assert ui_controller.darkMode is False
    assert ui_controller.currentView == "Library"


def test_ui_controller_is_monochrome_logo(ui_controller):
    assert ui_controller.isMonochromeLogo("OpenCode") is True
    assert ui_controller.isMonochromeLogo("opencode") is True
    assert ui_controller.isMonochromeLogo("Plain Text") is True
    assert ui_controller.isMonochromeLogo("plaintext") is True
    assert ui_controller.isMonochromeLogo("Antigravity") is False
    assert ui_controller.isMonochromeLogo("Gemini CLI") is False
    assert ui_controller.isMonochromeLogo("Codex") is False
    assert ui_controller.isMonochromeLogo(None) is False


def test_disable_state_persistence_blocks_all_ui_state_writes(ui_controller, mock_app):
    """Headless observers must never persist the user's UI state."""
    mock_app._config.set.reset_mock()
    ui_controller.disable_state_persistence()

    ui_controller.currentView = "QuickCopy"
    ui_controller.windowWidth = 1400
    ui_controller.saveUiState()
    ui_controller.triggerSave()

    assert mock_app._config.set.call_count == 0


def test_disable_state_persistence_stops_pending_save(ui_controller, mock_app):
    """A debounced save armed before disabling does not fire afterwards."""
    ui_controller.triggerSave()
    assert ui_controller._save_timer.isActive() is True

    ui_controller.disable_state_persistence()

    assert ui_controller._save_timer.isActive() is False


def test_legacy_compact_list_rows_config_is_ignored_silently(mock_app):
    """A pre-existing user config may still carry ``compact_list_rows``.

    The compact-row toggle was removed, so the legacy key must be dropped
    quietly instead of raising a validation error and resetting the whole
    UI state (which would silently discard the user's window geometry).
    """
    mock_app._config.get.side_effect = lambda key, default=None: (
        {
            "window_width": 1440,
            "window_height": 900,
            "dark_mode": True,
            "compact_list_rows": True,
        }
        if key == "ui_state"
        else default
    )

    ui_controller = UIController(mock_app)

    # The legacy key is ignored, the rest of the state survives.
    assert not hasattr(ui_controller, "compactListRows")
    assert ui_controller.windowWidth == 1440
    assert ui_controller.windowHeight == 900
    assert ui_controller.darkMode is True


def test_legacy_top_level_compact_list_rows_config_is_ignored_silently(mock_app):
    """The legacy key may also sit at the top level of ``config.json``."""
    mock_app._config.get.side_effect = lambda key, default=None: (
        False if key == "compact_list_rows" else default
    )

    ui_controller = UIController(mock_app)

    assert ui_controller.currentView == "Library"
