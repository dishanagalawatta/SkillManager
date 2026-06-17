from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController
from skill_manager.core.update_service import AppUpdateService


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._config = MagicMock()
    return app


@pytest.fixture
def service(tmp_path):
    tuf_dir = tmp_path / "tuf"
    target_dir = tmp_path / "updates"
    with patch("skill_manager.core.update_service.TUFClient") as mock_client:
        service = AppUpdateService(tuf_dir, target_dir)
        service._client = mock_client.return_value
        return service


@pytest.fixture
def controller(mock_app, service):
    with patch(
        "skill_manager.controllers.app_update_controller.AppUpdateService", return_value=service
    ):
        return AppUpdateController(mock_app)


class TestAppUpdateService:
    def test_check_for_updates_success(self, service):
        service._client.check_for_updates.return_value = "1.5.0"
        version, error = service.check_for_updates()
        assert version == "1.5.0"
        assert error is None

    def test_check_for_updates_no_update(self, service):
        service._client.check_for_updates.return_value = None
        version, error = service.check_for_updates()
        assert version is None
        assert error is None

    def test_check_for_updates_error(self, service):
        service._client.check_for_updates.side_effect = Exception("Network error")
        version, error = service.check_for_updates()
        assert version is None
        assert "Network error" in error

    def test_apply_update_success(self, service):
        service._client.download_and_apply_update.return_value = True
        progress_captured = []

        # Simulate tufup calling progress_hook
        def mock_download_and_apply(progress_hook=None):
            if progress_hook:
                progress_hook(50, 100)
            return True

        service._client.download_and_apply_update.side_effect = mock_download_and_apply

        success = service.apply_update(progress_callback=progress_captured.append)
        assert success is True
        assert 0.5 in progress_captured

    def test_apply_update_failure(self, service):
        service._client.download_and_apply_update.side_effect = Exception("Save failed")
        assert service.apply_update() is False


class TestAppUpdateControllerSDET:
    def test_check_for_updates_manual_success(self, controller, service):
        service._client.check_for_updates.return_value = "2.0.0"

        # Simulate background task execution
        def mock_submit(fn, callback):
            callback(fn())

        controller.app.task_runner.submit.side_effect = mock_submit

        controller.checkForUpdates(manual=True)

        assert controller.updateAvailable is True
        assert controller.latestVersion == "2.0.0"
        controller.app._set_status.assert_any_call("Update available: v2.0.0")

    def test_check_for_updates_no_update(self, controller, service):
        service._client.check_for_updates.return_value = None

        def mock_submit(fn, callback):
            callback(fn())

        controller.app.task_runner.submit.side_effect = mock_submit

        controller.checkForUpdates(manual=True)

        assert controller.updateAvailable is False
        controller.app._set_status.assert_any_call("SkillManager is up to date.")

    def test_apply_update_ui_flow(self, controller, service):
        controller._state.update_available = True
        service._client.download_and_apply_update.return_value = True

        def mock_run(fn):
            fn()

        controller.app.task_runner.run.side_effect = mock_run

        controller.downloadAndApplyUpdate()

        assert controller.isUpdating is False
        controller.app._set_status.assert_any_call("Update applied. Please restart SkillManager.")

    def test_check_for_updates_dev_mode(self, controller):
        with patch("sys.frozen", False, create=True):
            controller.checkForUpdates(manual=False)
            assert controller.hasCheckedForUpdates is True
            assert controller.isCheckingForUpdates is False


class TestEnsureRootJson:
    def test_bundled_missing_no_crash(self, tmp_path):
        tuf_dir = tmp_path / "tuf"
        target_dir = tmp_path / "updates"
        with (
            patch("skill_manager.core.update_service.TUFClient"),
            patch("skill_manager.core.update_service.Path") as mock_path_cls,
        ):
            svc = AppUpdateService(tuf_dir, target_dir)
            # Should not crash even if bundled root.json is missing
            assert tuf_dir.exists() or target_dir.exists()

    def test_already_exists_no_copy(self, tmp_path):
        tuf_dir = tmp_path / "tuf"
        tuf_dir.mkdir()
        existing = tuf_dir / "root.json"
        existing.write_text('{"existing": true}')
        target_dir = tmp_path / "updates"
        with patch("skill_manager.core.update_service.TUFClient"):
            svc = AppUpdateService(tuf_dir, target_dir)
        # File should still have original content (not overwritten)
        assert existing.read_text() == '{"existing": true}'


class TestServiceEdgeCases:
    def test_check_no_client(self, tmp_path):
        tuf_dir = tmp_path / "tuf"
        target_dir = tmp_path / "updates"
        with patch("skill_manager.core.update_service.TUFClient"):
            svc = AppUpdateService(tuf_dir, target_dir)
            svc._client = None
        version, error = svc.check_for_updates()
        assert version is None
        assert "not initialized" in error

    def test_apply_no_client(self, tmp_path):
        tuf_dir = tmp_path / "tuf"
        target_dir = tmp_path / "updates"
        with patch("skill_manager.core.update_service.TUFClient"):
            svc = AppUpdateService(tuf_dir, target_dir)
            svc._client = None
        assert svc.apply_update() is False

    def test_apply_returns_false_on_service_failure(self, service):
        service._client.download_and_apply_update.return_value = False
        assert service.apply_update() is False

    def test_client_init_exception(self, tmp_path):
        tuf_dir = tmp_path / "tuf"
        target_dir = tmp_path / "updates"
        with patch(
            "skill_manager.core.update_service.TUFClient",
            side_effect=RuntimeError("bad key"),
        ):
            svc = AppUpdateService(tuf_dir, target_dir)
            assert svc._client is None
