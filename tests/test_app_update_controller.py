from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.app_update_controller import AppUpdateController


@pytest.fixture(autouse=True)
def mock_tufup_client():
    with patch('skill_manager.controllers.app_update_controller.Client') as mock:
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
    assert controller.downloadUrl == "https://github.com/dishanagalawatta/SkillManager/releases/latest"
    assert controller.isUpdating is False
    assert controller.updateProgress == 0.0

@pytest.mark.asyncio
async def test_check_for_updates_slots():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)
    controller._is_updating = True
    controller.checkForUpdates()  # Should return early

    controller._is_updating = False
    with patch('skill_manager.controllers.app_update_controller.asyncio.create_task') as mock_task:
        controller.checkForUpdates()
        mock_task.assert_called_once()
        coro = mock_task.call_args[0][0]
        coro.close()

@pytest.mark.asyncio
async def test_check_tuf_updates_no_client():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)
    controller._client = None
    # Should return early without error
    await controller._check_tuf_updates()

@pytest.mark.asyncio
async def test_download_and_apply_update_early_returns():
    mock_app = MagicMock()
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

@pytest.mark.asyncio
async def test_download_and_apply_update_success():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    controller._client = MagicMock()
    controller._update_available = True

    with patch('skill_manager.controllers.app_update_controller.asyncio.create_task') as mock_task:
        controller.downloadAndApplyUpdate()
        assert controller._is_updating is True
        mock_task.assert_called_once()
        coro = mock_task.call_args[0][0]
        coro.close()

@pytest.mark.asyncio
async def test_apply_update_success():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    # Call progress hook to test it
    def side_effect(*args, **kwargs):
        kwargs['progress_hook'](50, 100)
        return True
    mock_client.download_and_apply_update.side_effect = side_effect
    controller._client = mock_client

    controller.isUpdatingChanged = MagicMock()
    controller.updateProgressChanged = MagicMock()

    await controller._apply_update()

    assert controller.updateProgress == 0.5
    controller.updateProgressChanged.emit.assert_called_with(0.5)
    mock_app._set_status.assert_called_with("Update applied. Please restart SkillManager.")
    assert controller.isUpdating is False

@pytest.mark.asyncio
async def test_apply_update_failure():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.download_and_apply_update.return_value = False
    controller._client = mock_client

    await controller._apply_update()
    mock_app._set_status.assert_called_with("Update failed.")

@pytest.mark.asyncio
async def test_apply_update_exception():
    mock_app = MagicMock()
    controller = AppUpdateController(mock_app)

    mock_client = MagicMock()
    mock_client.download_and_apply_update.side_effect = Exception("Download error")
    controller._client = mock_client

    await controller._apply_update()
    mock_app._set_status.assert_called_with("Update error: Download error")
