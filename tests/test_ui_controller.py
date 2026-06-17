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
    assert ui_controller.compactListRows is False
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
    assert last_args[1]["compact_list_rows"] is False


@patch("PySide6.QtCore.QTimer.start")
def test_ui_controller_trigger_save(mock_timer_start, ui_controller):
    ui_controller.triggerSave()
    mock_timer_start.assert_called_with(2000)


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


def test_ui_controller_open_path_linux(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "linux"),
        patch("subprocess.run") as mock_run,
    ):
        ui_controller.openPath("/path/to/file")
        mock_run.assert_called_with(["xdg-open", "/path/to/file"])

        # Test path starting with '-'
        ui_controller.openPath("-test")
        mock_run.assert_called_with(["xdg-open", "./-test"])


def test_ui_controller_open_path_darwin(ui_controller, mock_app):
    with (
        patch("skill_manager.controllers.ui_controller.sys.platform", "darwin"),
        patch("subprocess.run") as mock_run,
    ):
        ui_controller.openPath("/path/to/file")
        mock_run.assert_called_with(["open", "--", "/path/to/file"])


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
    assert ui_controller._state.inspector_width == 450


def test_ui_controller_window_geometry_properties(ui_controller):
    # Width (constraint: ge=1050)
    ui_controller.windowWidth = 1100
    assert ui_controller.windowWidth == 1100
    ui_controller.windowWidth = 800  # Below constraint
    assert ui_controller.windowWidth == 1100

    # Height (constraint: ge=650)
    ui_controller.windowHeight = 700
    assert ui_controller.windowHeight == 700
    ui_controller.windowHeight = 500  # Below constraint
    assert ui_controller.windowHeight == 700

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

    # Compact Rows
    ui_controller.compactListRows = True
    assert ui_controller.compactListRows is True

    # Remember Filters
    ui_controller.rememberFilters = False
    assert ui_controller.rememberFilters is False


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
