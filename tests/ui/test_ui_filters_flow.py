import pytest


@pytest.mark.usefixtures("setup_qml_style")
class TestUIFiltersFlow:
    def test_apply_and_clear_filters_flow(self, qml_engine, app_controller, qtbot):
        # 1. Initial State
        ui = app_controller.ui
        model = app_controller.skillModel

        # Ensure filters are clean
        ui.clearViewFilters()
        assert model.categoryFilter == ""
        assert model.filterText == ""

        # 2. Apply Category Filter
        ui.setViewFilter("category", "Automation")
        assert model.categoryFilter == "Automation"

        # 3. Apply Text Filter (usually via property binding, but we test the Slot logic if any)
        # Note: UIController doesn't have a direct slot for text filter, it's usually bound to the search bar.
        # But we can verify that clearViewFilters clears it.
        model.filterText = "findme"
        assert model.filterText == "findme"

        # 4. Clear Filters
        ui.clearViewFilters()
        assert model.categoryFilter == ""
        assert model.filterText == ""

    def test_ui_state_persistence_flow(self, qml_engine, app_controller, qtbot):
        ui = app_controller.ui

        # Change a preference
        ui.darkMode = True
        ui.compactListRows = True

        # Trigger an immediate save (bypassing debounce for the test)
        ui.saveUiState()

        # Verify it went to the config manager
        stored_state = app_controller._config.get("ui_state")
        assert stored_state["dark_mode"] is True
        assert stored_state["compact_list_rows"] is True

        # Reset and verify persistence
        ui.resetUiState()
        ui.saveUiState()
        stored_state = app_controller._config.get("ui_state")
        assert stored_state["dark_mode"] is False
        assert stored_state["compact_list_rows"] is False

    def test_view_switching_flow(self, qml_engine, app_controller, qtbot):
        ui = app_controller.ui

        # Switch to QuickCopy
        ui.currentView = "QuickCopy"
        assert ui.currentView == "QuickCopy"
        assert app_controller.skillModel == app_controller._quick_copy_model

        # Switch to Library
        ui.currentView = "Library"
        assert ui.currentView == "Library"
        assert app_controller.skillModel == app_controller._library_model
