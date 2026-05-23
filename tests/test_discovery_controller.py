from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._sources = ["/src"]
    app._update_packages = []
    app._projects = ["/proj"]
    app._archive_paths = []
    app._starred_paths = []
    app._project_aliases = {}
    app._config = MagicMock()
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app._categories = []
    app._client_format = "Gemini"
    app.ui = MagicMock()
    app.ui._default_project_filter = "all"
    return app

@pytest.fixture
def controller(mock_app):
    return DiscoveryController(mock_app)

def test_load_initial_data_success(controller, mock_app):
    # Mock DiscoveryService.discover_all to return a valid result
    mock_result = {
        "skills": [{"name": "Skill 1"}],
        "projects": ["/proj"],
        "categories": ["Dev"],
        "project_labels": ["Project"],
        "status": "Ready"
    }

    with patch("skill_manager.controllers.discovery_controller.DiscoveryService") as mock_service, \
         patch("skill_manager.controllers.discovery_controller.schedule_on_ui_thread") as mock_schedule:

        service_instance = mock_service.return_value
        service_instance.discover_all.return_value = mock_result

        # Capture the background task
        background_task = None
        def mock_run(task):
            nonlocal background_task
            background_task = task

        mock_app.task_runner.run.side_effect = mock_run

        controller.loadInitialData()

        # Verify initial state changes
        assert mock_app._is_loading is True
        mock_app.isLoadingChanged.emit.assert_called()

        # Execute the background task
        background_task()

        # Verify discover_all was called
        service_instance.discover_all.assert_called_once()

        # Verify schedule_on_ui_thread was called for finalization
        mock_schedule.assert_called()

        # Verify cache callback behavior if needed, but here we test the happy path

def test_finalize_loading(controller, mock_app):
    skills = [{"name": "S1"}]
    cats = ["Cat1"]

    controller._finalize_loading(skills, ["/p"], cats, ["L"], "Finished", is_final=True)

    assert mock_app._categories == cats
    mock_app.categoriesChanged.emit.assert_called_once()
    mock_app._library_model.setSkills.assert_called_with(skills)
    mock_app._quick_copy_model.setSkills.assert_called_with(skills)
    assert mock_app._is_loading is False
    mock_app.isLoadingChanged.emit.assert_called()

def test_handle_loading_error(controller, mock_app):
    controller._handle_loading_error("Error occurred")
    mock_app._set_status.assert_called_with("Error occurred")
    assert mock_app._is_loading is False
    mock_app.isLoadingChanged.emit.assert_called()
