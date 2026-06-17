from unittest.mock import patch

import pytest


@pytest.mark.usefixtures("setup_qml_style")
class TestUIUpdateFlow:
    def test_add_and_run_update_flow(self, qml_engine, app_controller, qtbot):
        # 1. Add a package via the controller
        # This simulates a user typing a name and clicking "Add"
        app_controller.updates.addUpdatePackage("test-flow-package")

        # Verify it appears in the model
        assert any(p["name"] == "test-flow-package" for p in app_controller.updatePackages)

        # 2. Trigger an update for that package
        # We find the index
        _idx = next(
            i
            for i, p in enumerate(app_controller.updatePackages)
            if p["name"] == "test-flow-package"
        )

        # Mock the service and background task to avoid real network/git calls
        with patch(
            "skill_manager.controllers.update_controller.UpdateService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value

            # Mock successful update behavior
            def mock_run_global(status_callback, source_progress_callback, completion_callback):
                completion_callback({"merged": 1, "failed": 0}, [])

            mock_service.run_global_update.side_effect = mock_run_global

            # This simulates clicking the "Update All" or "Sync" button
            app_controller.updates.updateNow()

            # Verify status message updated (wait for it as it happens on UI thread via QTimer)
            qtbot.waitUntil(
                lambda: "Global update complete" in app_controller.statusMessage, timeout=2000
            )

    def test_package_removal_flow(self, qml_engine, app_controller, qtbot):
        # 1. Add package
        app_controller.updates.addUpdatePackage("to-remove")
        assert any(p["name"] == "to-remove" for p in app_controller.updatePackages)

        # 2. Remove it
        idx = next(
            i for i, p in enumerate(app_controller.updatePackages) if p["name"] == "to-remove"
        )

        with qtbot.waitSignal(app_controller.updatePackagesChanged, timeout=1000):
            app_controller.updates.removeUpdatePackage(idx)

        # 3. Verify removal
        assert not any(p["name"] == "to-remove" for p in app_controller.updatePackages)
        assert "Removed update package" in app_controller.statusMessage
