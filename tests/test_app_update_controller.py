from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.task_runner = MagicMock()
    app._set_status = MagicMock()
    return app


@pytest.fixture
def controller(mock_app):
    return AppUpdateController(mock_app)


class TestAppUpdateControllerProperties:
    def test_initial_state(self, controller):
        assert controller.isUpdating is False
        assert controller.updateProgress == 0.0
        assert controller.isCheckingForUpdates is False
        assert controller.hasCheckedForUpdates is False

    def test_download_url(self, controller):
        assert (
            controller.downloadUrl
            == "https://github.com/dishanagalawatta/SkillManager/releases/latest"
        )

    def test_current_version(self, controller):
        import skill_manager
        assert controller.currentVersion == skill_manager.__version__


class TestCheckForUpdates:
    def test_check_for_updates_skip_in_dev_mode(self, controller, mock_app):
        with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
            mock_sys.frozen = False
            controller.checkForUpdates()
        assert controller.hasCheckedForUpdates is True

    def test_check_for_updates_production_mode(self, controller, mock_app):
        with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
            mock_sys.frozen = True
            controller.checkForUpdates()
        assert controller.isCheckingForUpdates is True
        mock_app.task_runner.submit.assert_called_once()

    def test_check_for_updates_manual_skips_dev_check(self, controller, mock_app):
        with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
            mock_sys.frozen = False
            controller.checkForUpdates(manual=True)
        mock_app._set_status.assert_any_call("Checking for app updates...")
        assert controller.isCheckingForUpdates is True

    def test_check_for_updates_early_return_when_updating(self, controller):
        controller._state.is_updating = True
        controller.checkForUpdates()
        assert controller.isCheckingForUpdates is False

    def test_check_for_updates_early_return_when_checking(self, controller):
        controller._state.is_checking = True
        controller.checkForUpdates()
        assert controller.isCheckingForUpdates is True


class TestOnUpdatesChecked:
    def test_on_updates_checked_with_new_version(self, controller, mock_app):
        controller._on_updates_checked("2.0.0", manual=True)
        assert controller.updateAvailable is True
        assert controller.latestVersion == "2.0.0"
        assert controller.isCheckingForUpdates is False
        mock_app._set_status.assert_called_with("Update available: v2.0.0")

    def test_on_updates_checked_no_update(self, controller, mock_app):
        controller._on_updates_checked(None, manual=True)
        assert controller.updateAvailable is False
        assert controller.isCheckingForUpdates is False
        mock_app._set_status.assert_called_with("SkillManager is up to date.")

    def test_on_updates_checked_with_error(self, controller, mock_app):
        controller._on_updates_checked(None, manual=True, error="Network failure")
        assert controller.updateAvailable is False
        assert controller.isCheckingForUpdates is False
        mock_app._set_status.assert_called_with("Update check failed: Network failure")

    def test_on_updates_checked_non_manual(self, controller, mock_app):
        controller._on_updates_checked("2.0.0", manual=False)
        assert controller.updateAvailable is True
        mock_app._set_status.assert_not_called()


class TestDownloadAndApplyUpdate:
    def test_download_early_return_when_updating(self, controller):
        controller._state.is_updating = True
        controller.downloadAndApplyUpdate()
        assert controller.isUpdating is True

    def test_download_early_return_when_not_available(self, controller):
        controller._state.update_available = False
        controller.downloadAndApplyUpdate()
        assert controller.isUpdating is False

    def test_download_success(self, controller, mock_app):
        controller._state.update_available = True
        controller.downloadAndApplyUpdate()
        assert controller.isUpdating is True
        mock_app.task_runner.run.assert_called_once()

    def test_download_no_task_runner(self, controller):
        controller._state.update_available = True
        del controller.app.task_runner
        controller.downloadAndApplyUpdate()
        assert controller.isUpdating is False


class TestApplyUpdateSync:
    def test_apply_success(self, controller, mock_app):
        controller._service.apply_update = MagicMock(return_value=True)
        controller._apply_update_sync()
        mock_app._set_status.assert_called_with("Update applied. Please restart SkillManager.")
        assert controller.isUpdating is False

    def test_apply_failure(self, controller, mock_app):
        controller._service.apply_update = MagicMock(return_value=False)
        controller._apply_update_sync()
        mock_app._set_status.assert_called_with("Update failed.")
        assert controller.isUpdating is False

    def test_apply_exception(self, controller, mock_app):
        controller._service.apply_update = MagicMock(side_effect=Exception("Download error"))
        controller._apply_update_sync()
        mock_app._set_status.assert_called_with("Update error: Download error")
        assert controller.isUpdating is False

    def test_apply_progress_callback(self, controller, mock_app):
        def fake_apply(progress_callback=None, **kwargs):
            if progress_callback:
                progress_callback(0.5)
            return True

        controller._service.apply_update = MagicMock(side_effect=fake_apply)
        controller._apply_update_sync()
        assert controller.updateProgress == 0.5


class TestStateTransitions:
    def test_is_checking_for_updates_state_transitions(self, controller, mock_app):
        assert controller.isCheckingForUpdates is False

        with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
            mock_sys.frozen = True
            controller.checkForUpdates()
        assert controller.isCheckingForUpdates is True

        controller._on_updates_checked(None)
        assert controller.isCheckingForUpdates is False
        assert controller.hasCheckedForUpdates is True

    def test_has_checked_for_updates_property(self, controller):
        assert controller.hasCheckedForUpdates is False
        controller._state.has_checked = True
        assert controller.hasCheckedForUpdates is True
