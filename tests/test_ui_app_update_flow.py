from unittest.mock import patch

import pytest


@pytest.mark.usefixtures("setup_qml_style")
class TestUIAppUpdateFlow:
    def test_manual_update_check_flow(self, qml_engine, app_controller, qtbot):
        """Verify the UI flow for a manual update check."""
        controller = app_controller.app_updater

        # Mock service check
        with patch.object(controller._service, "check_for_updates", return_value=("1.6.0", None)), \
             patch.object(app_controller.task_runner, "submit") as mock_submit, \
             patch.object(app_controller, "_set_status") as mock_status:

            # Simulate task runner calling back immediately
            mock_submit.side_effect = lambda fn, cb: cb(fn())

            # 1. Setup signal spies
            with qtbot.waitSignal(controller.updateAvailableChanged, timeout=2000):
                # 2. Trigger check
                controller.checkForUpdates(manual=True)

            # 3. Verify final state
            assert controller.updateAvailable is True
            assert controller.latestVersion == "1.6.0"
            mock_status.assert_any_call("Update available: v1.6.0")

    def test_apply_update_flow(self, qml_engine, app_controller, qtbot):
        """Verify the UI flow for applying an update."""
        controller = app_controller.app_updater
        controller._state.update_available = True

        # Mock service apply
        with patch.object(controller._service, "apply_update", return_value=True), \
             patch.object(app_controller.task_runner, "run") as mock_run, \
             patch.object(app_controller, "_set_status") as mock_status:

            # Simulate task runner running immediately
            mock_run.side_effect = lambda fn: fn()

            # 1. Setup signal spies
            with qtbot.waitSignal(controller.isUpdatingChanged, timeout=2000):
                # 2. Trigger apply
                controller.downloadAndApplyUpdate()

            # 3. Verify state reset
            assert controller.isUpdating is False
            mock_status.assert_any_call("Update applied. Please restart SkillManager.")

    def test_check_error_ui_feedback(self, qml_engine, app_controller, qtbot):
        """Verify that update check errors are shown in the UI status."""
        controller = app_controller.app_updater

        with patch.object(controller._service, "check_for_updates", return_value=(None, "Connection timeout")), \
             patch.object(app_controller.task_runner, "submit") as mock_submit, \
             patch.object(app_controller, "_set_status") as mock_status:

            mock_submit.side_effect = lambda fn, cb: cb(fn())

            with qtbot.waitSignal(controller.updateStateChanged, timeout=2000):
                controller.checkForUpdates(manual=True)

            mock_status.assert_any_call("Update check failed: Connection timeout")
