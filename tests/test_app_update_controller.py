from unittest.mock import ANY, MagicMock, patch

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController


@pytest.fixture(autouse=True)
def mock_tufup_client():
    with patch("skill_manager.controllers.app_update_controller.Client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_check_tuf_updates_success():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    # Mock the client and its check_for_updates method
    mock_client = MagicMock()
    mock_client.check_for_updates.return_value = "2.0.0"
    controller._client = mock_client

    # Mock the signals
    controller.updateAvailableChanged = MagicMock()
    controller.latestVersionChanged = MagicMock()

    await controller._check_tuf_updates()

    assert controller.updateAvailable is True
    assert controller.latestVersion == "2.0.0"
    controller.updateAvailableChanged.emit.assert_called()
    controller.latestVersionChanged.emit.assert_called()


@pytest.mark.asyncio
async def test_check_tuf_updates_no_update():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.check_for_updates.return_value = None
    controller._client = mock_client

    controller.updateAvailableChanged = MagicMock()

    await controller._check_tuf_updates()

    assert controller.updateAvailable is False
    controller.updateAvailableChanged.emit.assert_called()


@pytest.mark.asyncio
async def test_check_tuf_updates_failure():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.check_for_updates.side_effect = Exception("Network error")
    controller._client = mock_client

    # Should not raise exception but log it (guarded by try-except)
    await controller._check_tuf_updates()
    assert controller.updateAvailable is False


@pytest.mark.asyncio
async def test_properties():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)
    assert (
        controller.downloadUrl == "https://github.com/dishanagalawatta/SkillManager/releases/latest"
    )
    assert controller.isUpdating is False
    assert controller.updateProgress == 0.0


@pytest.mark.asyncio
async def test_check_for_updates_slots():
    mock_app = MagicMock()
    mock_app.task_runner = MagicMock()
    controller = AppUpdateController(mock_app)
    controller._is_updating = True
    controller.checkForUpdates()  # Should return early

    controller._is_updating = False
    with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
        mock_sys.frozen = True
        controller.checkForUpdates()
    mock_app.task_runner.submit.assert_called_once_with(
        controller._sync_check_updates, ANY
    )


@pytest.mark.asyncio
async def test_manual_check_for_updates_feedback():
    mock_app = MagicMock()
    mock_app.task_runner = MagicMock()
    controller = AppUpdateController(mock_app)

    # 1. Dev mode manual feedback
    with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
        mock_sys.frozen = False
        controller.checkForUpdates(manual=True)
        mock_app._set_status.assert_called_with("Update check skipped in development mode.")

    # 2. Production mode manual feedback (start)
    mock_app._set_status.reset_mock()
    with patch("skill_manager.controllers.app_update_controller.sys") as mock_sys:
        mock_sys.frozen = True
        controller.checkForUpdates(manual=True)
        mock_app._set_status.assert_any_call("Checking for app updates...")

    # 3. Success feedback
    mock_app._set_status.reset_mock()
    controller._on_updates_checked("2.0.0", manual=True)
    mock_app._set_status.assert_called_with("Update available: v2.0.0")

    # 4. Up to date feedback
    mock_app._set_status.reset_mock()
    controller._on_updates_checked(None, manual=True)
    mock_app._set_status.assert_called_with("SkillManager is up to date.")


@pytest.mark.asyncio
async def test_check_tuf_updates_no_client():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)
    controller._client = None
    # Should return early without error
    await controller._check_tuf_updates()


def test_download_and_apply_update_early_returns():
    mock_app = MagicMock()
    mock_app.task_runner = MagicMock()
    controller = AppUpdateController(mock_app)

    # Client is None
    controller._client = None
    controller.downloadAndApplyUpdate()

    # Is updating
    controller._client = MagicMock()
    controller._is_updating = True
    controller.downloadAndApplyUpdate()

    # Not available
    controller._is_updating = False
    controller._update_available = False
    controller.downloadAndApplyUpdate()
    assert controller._is_updating is False


def test_download_and_apply_update_success():
    mock_app = MagicMock()
    mock_app.task_runner = MagicMock()
    controller = AppUpdateController(mock_app)

    controller._client = MagicMock()
    controller._update_available = True

    controller.downloadAndApplyUpdate()
    assert controller._is_updating is True
    mock_app.task_runner.run.assert_called_once_with(
        controller._sync_apply_update
    )


def test_apply_update_success():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()

    # Call progress hook to test it
    def side_effect(*args, **kwargs):
        kwargs["progress_hook"](50, 100)
        return True

    mock_client.download_and_apply_update.side_effect = side_effect
    controller._client = mock_client

    controller.isUpdatingChanged = MagicMock()
    controller.updateProgressChanged = MagicMock()

    controller._sync_apply_update()

    assert controller.updateProgress == 0.5
    controller.updateProgressChanged.emit.assert_called_with(0.5)
    mock_app._set_status.assert_called_with("Update applied. Please restart SkillManager.")
    assert controller.isUpdating is False


def test_apply_update_failure():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.download_and_apply_update.return_value = False
    controller._client = mock_client

    controller._sync_apply_update()
    mock_app._set_status.assert_called_with("Update failed.")


def test_apply_update_exception():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.download_and_apply_update.side_effect = Exception("Download error")
    controller._client = mock_client

    controller._sync_apply_update()
    mock_app._set_status.assert_called_with("Update error: Download error")
