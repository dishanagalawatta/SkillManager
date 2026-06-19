"""Tests for the rewritten AppUpdateController (GitHub Releases API check)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController
from skill_manager.core.release_check_service import RELEASES_PAGE
from skill_manager.utils.task_runner import SynchronousTaskRunner


@pytest.fixture
def mock_app_mock_runner():
    """Mock app with a MagicMock task_runner — submit does NOT invoke callback."""
    app = MagicMock()
    app.task_runner = MagicMock()
    app._set_status = MagicMock()
    return app


@pytest.fixture
def mock_app_sync_runner():
    """Mock app with a real SynchronousTaskRunner — submit invokes callback."""
    app = MagicMock()
    app.task_runner = SynchronousTaskRunner()
    app._set_status = MagicMock()
    return app


@pytest.fixture
def mock_app_no_runner():
    """Mock app without a task_runner attribute."""
    app = MagicMock()
    del app.task_runner
    app._set_status = MagicMock()
    return app


@pytest.fixture
def controller(mock_app_mock_runner):
    return AppUpdateController(mock_app_mock_runner)


# --- Properties ---


class TestProperties:
    def test_initial_state(self, controller):
        assert controller.updateAvailable is False
        assert controller.hasCheckedForUpdates is False
        assert controller.isCheckingForUpdates is False

    def test_release_url(self, controller):
        assert controller.releaseUrl == RELEASES_PAGE

    def test_current_version_is_set(self, controller):
        import skill_manager

        assert controller.currentVersion == skill_manager.__version__

    def test_latest_version_initial(self, controller):
        import skill_manager

        assert controller.latestVersion == skill_manager.__version__


# --- checkForUpdates ---


class TestCheckForUpdates:
    def test_manual_check_submits_to_task_runner(self, mock_app_mock_runner):
        """Manual check submits check_latest_release to the task runner."""
        controller = AppUpdateController(mock_app_mock_runner)
        with patch(
            "skill_manager.controllers.app_update_controller.check_latest_release"
        ) as mock_check:
            mock_check.return_value = ("1.6.0", None)
            controller.checkForUpdates(manual=True)
            mock_app_mock_runner.task_runner.submit.assert_called_once()

    def test_manual_check_sets_status_message(self, mock_app_mock_runner):
        """Manual check calls _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        with patch("skill_manager.controllers.app_update_controller.check_latest_release"):
            controller.checkForUpdates(manual=True)
            mock_app_mock_runner._set_status.assert_called_with("Checking for app updates...")

    def test_auto_check_skipped_in_dev_mode(self, mock_app_mock_runner):
        """Non-frozen + non-manual check short-circuits immediately."""
        controller = AppUpdateController(mock_app_mock_runner)
        assert not getattr(sys, "frozen", False)
        controller.checkForUpdates(manual=False)
        mock_app_mock_runner.task_runner.submit.assert_not_called()
        assert controller.hasCheckedForUpdates is True
        assert controller.isCheckingForUpdates is False

    def test_already_checking_returns_early(self, mock_app_mock_runner):
        """If is_checking is True, a second call is a no-op."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller._state.is_checking = True
        controller.checkForUpdates(manual=True)
        mock_app_mock_runner.task_runner.submit.assert_not_called()

    def test_frozen_mode_always_checks(self, mock_app_mock_runner):
        """When sys.frozen is True, auto-check still submits."""
        with patch.object(sys, "frozen", True, create=True):
            controller = AppUpdateController(mock_app_mock_runner)
            with patch("skill_manager.controllers.app_update_controller.check_latest_release"):
                controller.checkForUpdates(manual=False)
                mock_app_mock_runner.task_runner.submit.assert_called_once()

    def test_no_task_runner_fallback(self, mock_app_no_runner):
        """Without task_runner, is_checking resets to False without crash."""
        controller = AppUpdateController(mock_app_no_runner)
        controller.checkForUpdates(manual=True)
        assert controller.isCheckingForUpdates is False

    def test_full_flow_with_sync_runner(self, mock_app_sync_runner):
        """Full flow: real runner invokes callback, covers on_checked lines 110-111."""
        controller = AppUpdateController(mock_app_sync_runner)
        with patch(
            "skill_manager.controllers.app_update_controller.check_latest_release",
            return_value=("1.7.0", None),
        ):
            controller.checkForUpdates(manual=True)

        assert controller.updateAvailable is True
        assert controller.latestVersion == "1.7.0"
        assert controller.hasCheckedForUpdates is True
        mock_app_sync_runner._set_status.assert_any_call("Checking for app updates...")
        mock_app_sync_runner._set_status.assert_any_call("Update available: v1.7.0")


# --- _on_updates_checked callback branches ---


class TestOnUpdatesChecked:
    def test_error_sets_state(self, mock_app_mock_runner):
        """Error branch: sets update_available=False, has_checked=True, error stored."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller._on_updates_checked(new_version=None, manual=True, error="timeout")

        assert controller.hasCheckedForUpdates is True
        assert controller.isCheckingForUpdates is False
        assert controller.updateAvailable is False
        assert controller._state.error == "timeout"
        mock_app_mock_runner._set_status.assert_called_with("Update check failed: timeout")

    def test_error_non_manual_no_status(self, mock_app_mock_runner):
        """Error branch (non-manual): does not call _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller._on_updates_checked(new_version=None, manual=False, error="timeout")
        mock_app_mock_runner._set_status.assert_not_called()

    def test_update_available_sets_version(self, mock_app_mock_runner):
        """Update available branch: sets latest_version and update_available=True."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller._on_updates_checked(new_version="1.7.0", manual=True, error=None)

        assert controller.updateAvailable is True
        assert controller.latestVersion == "1.7.0"
        assert controller.hasCheckedForUpdates is True
        assert controller._state.error is None
        mock_app_mock_runner._set_status.assert_called_with("Update available: v1.7.0")

    def test_update_available_non_manual_no_status(self, mock_app_mock_runner):
        """Update available branch (non-manual): does not call _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller._on_updates_checked(new_version="1.7.0", manual=False, error=None)
        mock_app_mock_runner._set_status.assert_not_called()

    def test_up_to_date(self, mock_app_mock_runner):
        """No update: update_available=False."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller._on_updates_checked(new_version=None, manual=True, error=None)

        assert controller.updateAvailable is False
        assert controller.hasCheckedForUpdates is True
        mock_app_mock_runner._set_status.assert_called_with("SkillManager is up to date.")

    def test_up_to_date_non_manual_no_status(self, mock_app_mock_runner):
        """No update (non-manual): does not call _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller._on_updates_checked(new_version=None, manual=False, error=None)
        mock_app_mock_runner._set_status.assert_not_called()


# --- openReleasesPage ---


class TestOpenReleasesPage:
    def test_opens_releases_page(self, controller):
        with patch(
            "skill_manager.controllers.app_update_controller.QDesktopServices"
        ) as mock_desktop:
            controller.openReleasesPage()
            mock_desktop.openUrl.assert_called_once()
            url_arg = mock_desktop.openUrl.call_args[0][0]
            assert str(url_arg.toString()) == RELEASES_PAGE
