from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.update_controller import UpdateController


@pytest.fixture
def update_controller(mock_app):
    # Initialize mock_app with specific values needed for update controller
    mock_app._sources = ["/src"]
    app_projects = ["/project"]
    mock_app._projects = app_projects
    mock_app._update_packages = [{"name": "Source1", "is_updating": False, "just_finished": False}]
    mock_app._syncing_projects = []
    mock_app._project_aliases = {}
    mock_app._library_model._all_skills = []
    # override getProjectLabel for this test if needed, but conftest already has a generic one
    mock_app.getProjectLabel.side_effect = lambda t: "ProjectLabel" if t == "/project" else t
    return UpdateController(mock_app)


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_update_now(mock_service_class, update_controller, mock_app):
    mock_service = mock_service_class.return_value
    update_controller.update_now()

    # Verify status and state changes
    mock_app._set_status.assert_called_with("Starting global update...")
    assert "/project" in mock_app._syncing_projects
    assert mock_app._update_packages[0]["is_updating"] is True
    mock_app.projectsChanged.emit.assert_called()
    mock_app.updatePackagesChanged.emit.assert_called()

    # Verify service call
    mock_service.run_global_update.assert_called_once()

    # Test completion callback
    args, kwargs = mock_service.run_global_update.call_args
    completion_callback = kwargs["completion_callback"]

    with patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer:
        completion_callback({"merged": 1, "failed": 0}, mock_app._update_packages)
        # Extract and run the inner finalize function
        timer_args = mock_timer.call_args_list[0][0]
        finalize_func = timer_args[2]
        finalize_func()

        mock_app.load_initial_data.assert_called_once()
        mock_app._set_status.assert_any_call("Global update complete: 1 updated, 0 failed")
        assert mock_app._syncing_projects == []


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_for_updates(mock_service_class, update_controller, mock_app):
    mock_service = mock_service_class.return_value
    update_controller.scan_for_updates()

    mock_app._set_status.assert_called_with("Scanning for updates...")
    assert mock_app._is_loading is True

    # Test completion callback
    args, kwargs = mock_service.scan_for_updates.call_args
    completion_callback = kwargs["completion_callback"]

    with patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer:
        completion_callback([{"status": "up_to_date"}], mock_app._update_packages)
        finalize_func = mock_timer.call_args[0][2]
        finalize_func()

        assert mock_app._is_loading is False
        mock_app.isLoadingChanged.emit.assert_called()
        mock_app._set_status.assert_any_call("Scan complete: 1 skills processed")


def test_update_skill_in_project_success(update_controller, mock_app):
    mock_app._library_model._all_skills = [
        {"is_source": True, "name": "Skill1", "local_path": "/p1"}
    ]
    mock_app._projects = ["/project"]

    with (
        patch("skill_manager.core.copier.copy_skill_folders_to_projects") as mock_copy,
        patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer,
    ):
        mock_copy.return_value = {"failed": 0}

        update_controller.update_skill_in_project("Skill1", "ProjectLabel")

        mock_copy.assert_called_once()
        # Verify timers (status update and re-scan)
        assert mock_timer.call_count >= 2


def test_recalculate_stats(update_controller, mock_app):
    mock_app._update_results = [
        {"status": "up_to_date"},
        {"status": "outdated"},
        {"status": "missing"},
        {"status": "outdated"},
    ]
    update_controller.recalculate_stats()

    assert mock_app._stats_up_to_date == 1
    assert mock_app._stats_outdated == 2
    assert mock_app._stats_missing == 1
    mock_app.statsChanged.emit.assert_called_once()
