from unittest.mock import MagicMock

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
    app._current_project_label = ""
    app.ui = MagicMock()
    return app


@pytest.fixture
def controller(mock_app):
    return DiscoveryController(mock_app)


def test_load_initial_data_success(controller, mock_app):
    mock_app.task_runner = MagicMock()
    controller.loadInitialData()
    mock_app.task_runner.submit.assert_called_once_with(
        controller._run_discovery_sync, controller._on_discovery_done
    )


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


def test_run_discovery_sync_error(controller, mock_app):
    from unittest.mock import patch

    with patch(
        "skill_manager.core.discovery.DiscoveryService.discover_all",
        side_effect=RuntimeError("Discovery failed"),
    ):
        result = controller._run_discovery_sync()
        assert "error" in result


def test_on_discovery_done_none(controller):
    controller._on_discovery_done(None)


def test_on_discovery_done_error(controller, mock_app):
    controller._on_discovery_done({"error": "Failed"})
    mock_app._set_status.assert_called()


def test_finalize_loading_with_project_label(controller, mock_app):
    mock_app._current_project_label = "MyProject"
    controller._finalize_loading([], [], [], [], "Status", is_final=False)
    assert mock_app._quick_copy_model.projectFilter == "MyProject"
