import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController
from skill_manager.core.release_check_service import RELEASES_PAGE, ReleaseInfo
from skill_manager.utils.task_runner import SynchronousTaskRunner


def _release(version: str) -> ReleaseInfo:
    return ReleaseInfo(
        version=version,
        tag_name=f"v{version}",
        page_url=f"{RELEASES_PAGE}/tag/v{version}",
    )


@pytest.mark.usefixtures("setup_qml_style")
class TestUIUpdateFlow:
    @pytest.fixture(autouse=True)
    def _stub_real_package_install(self):
        """Stop the delayed real install scheduled by ``addUpdatePackage``.

        Adding a package queues ``runPackageUpdate`` 500 ms later. Under
        parallel load that probe outlives the test, hits the npm registry
        for a fake package, and can overwrite the status message the test
        waits on, so stub it for the whole class.
        """
        with patch("skill_manager.controllers.update_controller.UpdateController.runPackageUpdate"):
            yield

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


# ── AppUpdateController (GitHub Releases check; merged from test_ui_app_update_flow.py) ──


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
            "skill_manager.controllers.app_update_controller.fetch_latest_release"
        ) as mock_check:
            mock_check.return_value = (_release("1.6.0"), None)
            controller.checkForUpdates(manual=True)
            mock_app_mock_runner.task_runner.submit.assert_called_once()

    def test_manual_check_sets_status_message(self, mock_app_mock_runner):
        """Manual check calls _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        with patch("skill_manager.controllers.app_update_controller.fetch_latest_release"):
            controller.checkForUpdates(manual=True)
            mock_app_mock_runner._set_status.assert_called_with("Checking for app updates...")

    def test_auto_check_skipped_in_dev_mode(self, mock_app_mock_runner):
        """Non-frozen + non-manual check short-circuits immediately."""
        controller = AppUpdateController(mock_app_mock_runner)
        assert not getattr(sys, "frozen", False)
        controller.checkForUpdates(manual=False)
        mock_app_mock_runner.task_runner.submit.assert_not_called()
        # A skipped check must not claim "up to date": Settings renders
        # has_checked as the Up to Date label.
        assert controller.hasCheckedForUpdates is False
        assert controller.isCheckingForUpdates is False

    def test_already_checking_returns_early(self, mock_app_mock_runner):
        """If is_checking is True, a second call is a no-op."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller.state.is_checking = True
        controller.checkForUpdates(manual=True)
        mock_app_mock_runner.task_runner.submit.assert_not_called()

    def test_frozen_mode_always_checks(self, mock_app_mock_runner):
        """When sys.frozen is True, auto-check still submits."""
        with patch.object(sys, "frozen", True, create=True):
            controller = AppUpdateController(mock_app_mock_runner)
            with patch("skill_manager.controllers.app_update_controller.fetch_latest_release"):
                controller.checkForUpdates(manual=False)
                mock_app_mock_runner.task_runner.submit.assert_called_once()

    def test_no_task_runner_fallback(self, mock_app_no_runner):
        """Without task_runner, is_checking resets to False without crash."""
        controller = AppUpdateController(mock_app_no_runner)
        controller.checkForUpdates(manual=True)
        assert controller.isCheckingForUpdates is False

    def test_start_auto_check_schedules_first_check_and_daily_timer(self, mock_app_mock_runner):
        """startAutoCheck arms the periodic timer and one delayed check."""
        controller = AppUpdateController(mock_app_mock_runner)
        with patch(
            "skill_manager.controllers.app_update_controller.QTimer.singleShot"
        ) as single_shot:
            controller.startAutoCheck()

        single_shot.assert_called_once()
        assert controller._auto_check_timer is not None
        assert controller._auto_check_timer.isActive()

        # Idempotent: repeat calls must not stack timers.
        with patch(
            "skill_manager.controllers.app_update_controller.QTimer.singleShot"
        ) as single_shot_again:
            controller.startAutoCheck()
        single_shot_again.assert_not_called()
        controller._auto_check_timer.stop()

    def test_newer_release_emits_app_update_signal(self, mock_app_mock_runner, qtbot):
        """A detected release reaches Main.qml so the toast can be shown."""
        controller = AppUpdateController(mock_app_mock_runner)
        with qtbot.waitSignal(controller.appUpdateAvailable, timeout=1000) as blocker:
            controller.on_updates_checked("99.0.0", manual=False, error=None)

        assert blocker.args == ["99.0.0"]
        assert controller.updateAvailable is True

    def test_up_to_date_emits_no_app_update_signal(self, mock_app_mock_runner):
        controller = AppUpdateController(mock_app_mock_runner)
        emitted = []
        controller.appUpdateAvailable.connect(emitted.append)

        controller.on_updates_checked(controller.currentVersion, manual=False, error=None)

        assert emitted == []

    def test_full_flow_with_sync_runner(self, mock_app_sync_runner):
        """Full flow: real runner invokes callback, covers on_checked lines 110-111."""
        controller = AppUpdateController(mock_app_sync_runner)
        with patch(
            "skill_manager.controllers.app_update_controller.fetch_latest_release",
            return_value=(_release("9.9.9"), None),
        ):
            controller.checkForUpdates(manual=True)

        assert controller.updateAvailable is True
        assert controller.latestVersion == "9.9.9"
        assert controller.hasCheckedForUpdates is True
        mock_app_sync_runner._set_status.assert_any_call("Checking for app updates...")
        mock_app_sync_runner._set_status.assert_any_call("Update available: v9.9.9")


# --- on_updates_checked callback branches ---


class TestOnUpdatesChecked:
    def test_error_sets_state(self, mock_app_mock_runner):
        """Error branch: no update, error stored, and the check is not cached.

        has_checked stays False so the Settings button keeps reading "Check for
        Updates" and stays clickable instead of claiming "Up to Date".
        """
        controller = AppUpdateController(mock_app_mock_runner)
        controller.on_updates_checked(new_version=None, manual=True, error="timeout")

        assert controller.hasCheckedForUpdates is False
        assert controller.isCheckingForUpdates is False
        assert controller.updateAvailable is False
        assert controller.state.error == "timeout"
        mock_app_mock_runner._set_status.assert_called_with("Update check failed: timeout")

    def test_error_non_manual_no_status(self, mock_app_mock_runner):
        """Error branch (non-manual): does not call _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller.on_updates_checked(new_version=None, manual=False, error="timeout")
        mock_app_mock_runner._set_status.assert_not_called()

    def test_update_available_sets_version(self, mock_app_mock_runner):
        """Update available branch: sets latest_version and update_available=True."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller.on_updates_checked(new_version="9.9.9", manual=True, error=None)

        assert controller.updateAvailable is True
        assert controller.latestVersion == "9.9.9"
        assert controller.hasCheckedForUpdates is True
        assert controller.state.error is None
        mock_app_mock_runner._set_status.assert_called_with("Update available: v9.9.9")

    def test_update_available_non_manual_no_status(self, mock_app_mock_runner):
        """Update available branch (non-manual): does not call _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller.on_updates_checked(new_version="1.7.0", manual=False, error=None)
        mock_app_mock_runner._set_status.assert_not_called()

    def test_up_to_date(self, mock_app_mock_runner):
        """No update: update_available=False."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller.on_updates_checked(new_version=None, manual=True, error=None)

        assert controller.updateAvailable is False
        assert controller.hasCheckedForUpdates is True
        mock_app_mock_runner._set_status.assert_called_with("SkillManager is up to date.")

    def test_up_to_date_non_manual_no_status(self, mock_app_mock_runner):
        """No update (non-manual): does not call _set_status."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller.on_updates_checked(new_version=None, manual=False, error=None)
        mock_app_mock_runner._set_status.assert_not_called()

    def test_same_version_not_an_update(self, mock_app_mock_runner):
        """GitHub returning the same version as current must NOT set updateAvailable."""
        import skill_manager

        controller = AppUpdateController(mock_app_mock_runner)
        same_version = skill_manager.__version__
        controller.on_updates_checked(new_version=same_version, manual=True, error=None)

        assert controller.updateAvailable is False
        assert controller.latestVersion == same_version
        assert controller.hasCheckedForUpdates is True
        mock_app_mock_runner._set_status.assert_called_with("SkillManager is up to date.")

    def test_older_version_not_an_update(self, mock_app_mock_runner):
        """GitHub returning a version older than current must NOT set updateAvailable."""
        controller = AppUpdateController(mock_app_mock_runner)
        # Force current_version to something higher so we can craft an older remote
        controller.state.current_version = "2.0.0"
        controller.on_updates_checked(new_version="1.0.0", manual=True, error=None)

        assert controller.updateAvailable is False
        assert controller.latestVersion == "1.0.0"
        mock_app_mock_runner._set_status.assert_called_with("SkillManager is up to date.")

    def test_invalid_version_string_not_an_update(self, mock_app_mock_runner):
        """An unparseable version string from GitHub must not crash or show update."""
        controller = AppUpdateController(mock_app_mock_runner)
        controller.on_updates_checked(new_version="not-a-version", manual=True, error=None)

        assert controller.updateAvailable is False


# --- openReleasesPage ---


class TestOpenReleasesPage:
    def test_opens_releases_page(self, controller):
        with patch(
            "skill_manager.controllers.app_update_controller.open_external_url",
            return_value=(True, ""),
        ) as mock_open:
            assert controller.openReleasesPage() is True
            mock_open.assert_called_once_with(RELEASES_PAGE)

    def test_falls_back_to_qt_when_host_opener_fails(self, controller):
        with (
            patch(
                "skill_manager.controllers.app_update_controller.open_external_url",
                return_value=(False, "no opener"),
            ),
            patch(
                "skill_manager.controllers.app_update_controller.QDesktopServices"
            ) as mock_desktop,
        ):
            mock_desktop.openUrl.return_value = True
            assert controller.openReleasesPage() is True
            url_arg = mock_desktop.openUrl.call_args[0][0]
            assert str(url_arg.toString()) == RELEASES_PAGE

    def test_reports_failure_when_every_opener_fails(self, controller):
        with (
            patch(
                "skill_manager.controllers.app_update_controller.open_external_url",
                return_value=(False, "no opener"),
            ),
            patch(
                "skill_manager.controllers.app_update_controller.QDesktopServices"
            ) as mock_desktop,
        ):
            mock_desktop.openUrl.return_value = False
            assert controller.openReleasesPage() is False
        controller.app._set_status.assert_called_with("Could not open the release page: no opener")


# --- download & install orchestration ---


class TestDownloadAndInstall:
    @staticmethod
    def _arm(controller, *, supported=True, kind="appimage", available=True):
        from skill_manager.core.app_update_service import InstallContext, InstallKind

        install_kind = InstallKind(kind)
        controller._context = InstallContext(
            install_kind,
            target=Path("/tmp/SkillManager.AppImage"),
            executable=Path("/tmp/SkillManager.AppImage"),
            supported=supported,
            reason="" if supported else "no pkexec",
        )
        controller.state.update_available = available
        controller.state.latest_version = "9.9.9"
        controller._release = _release("9.9.9")

    def test_unsupported_build_reports_reason_and_never_submits(self, mock_app_mock_runner):
        controller = AppUpdateController(mock_app_mock_runner)
        self._arm(controller, supported=False, kind="source")

        controller.downloadAndInstallUpdate()

        assert controller.installError == "no pkexec"
        mock_app_mock_runner.task_runner.submit.assert_not_called()
        mock_app_mock_runner._set_status.assert_called_with("Update failed: no pkexec")

    def test_no_update_available_is_reported(self, mock_app_mock_runner):
        controller = AppUpdateController(mock_app_mock_runner)
        self._arm(controller, available=False)

        controller.downloadAndInstallUpdate()

        mock_app_mock_runner.task_runner.submit.assert_not_called()
        mock_app_mock_runner._set_status.assert_called_with("No SkillManager update is available.")

    def test_successful_download_applies_the_update(self, mock_app_sync_runner, tmp_path):
        from skill_manager.core.app_update_service import InstallResult
        from skill_manager.core.release_check_service import ReleaseAsset

        controller = AppUpdateController(mock_app_sync_runner)
        self._arm(controller)
        asset = ReleaseAsset(name="SkillManager.AppImage", url="https://github.com/x/y")

        with (
            patch(
                "skill_manager.controllers.app_update_controller.select_update_asset",
                return_value=asset,
            ),
            patch(
                "skill_manager.controllers.app_update_controller.expected_checksum",
                return_value="a" * 64,
            ),
            patch(
                "skill_manager.controllers.app_update_controller.download_destination",
                return_value=tmp_path / "download",
            ),
            patch(
                "skill_manager.controllers.app_update_controller.download_asset",
                return_value=tmp_path / "download",
            ),
            patch(
                "skill_manager.controllers.app_update_controller.apply_update",
                return_value=InstallResult(True, quit_required=False),
            ) as apply,
        ):
            controller.downloadAndInstallUpdate()

        assert controller.isDownloading is False
        assert controller.installError == ""
        assert controller.state.download_progress == 100
        assert controller.state.downloaded_path == str(tmp_path / "download")
        apply.assert_called_once()
        mock_app_sync_runner._set_status.assert_any_call(
            "Installing update — SkillManager will restart..."
        )

    def test_download_failure_is_shown(self, mock_app_sync_runner, tmp_path):
        from skill_manager.core.app_update_service import UpdateDownloadError
        from skill_manager.core.release_check_service import ReleaseAsset

        controller = AppUpdateController(mock_app_sync_runner)
        self._arm(controller)
        asset = ReleaseAsset(name="SkillManager.AppImage", url="https://github.com/x/y")

        with (
            patch(
                "skill_manager.controllers.app_update_controller.select_update_asset",
                return_value=asset,
            ),
            patch(
                "skill_manager.controllers.app_update_controller.expected_checksum",
                side_effect=UpdateDownloadError("Cannot verify the update: no manifest"),
            ),
            patch("skill_manager.controllers.app_update_controller.apply_update") as apply,
        ):
            controller.downloadAndInstallUpdate()

        assert controller.isDownloading is False
        assert "Cannot verify" in controller.installError
        apply.assert_not_called()
        mock_app_sync_runner._set_status.assert_any_call(
            "Update download failed: Cannot verify the update: no manifest"
        )

    def test_cancel_stops_an_in_flight_download(self, mock_app_mock_runner):
        controller = AppUpdateController(mock_app_mock_runner)
        self._arm(controller)
        controller.state.is_downloading = True

        controller.cancelUpdateDownload()

        assert controller.isDownloading is False
        assert controller.downloadProgress == 0
        mock_app_mock_runner._set_status.assert_called_with("Update download cancelled.")

    def test_progress_is_clamped_and_reported(self, controller):
        controller.state.is_downloading = True
        controller._set_download_progress(50, 200)
        assert controller.downloadProgress == 25
        assert controller.downloadedBytes == 50
        assert controller.downloadTotalBytes == 200

        controller._set_download_progress(300, 200)
        assert controller.downloadProgress == 100

    def test_progress_is_ignored_after_cancel(self, controller):
        controller.state.is_downloading = False
        controller._set_download_progress(10, 100)
        assert controller.downloadProgress == 0
