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
    from unittest.mock import AsyncMock
    with patch.object(controller, "_do_discovery", new_callable=AsyncMock) as mock_discovery:
        controller.loadInitialData()
        mock_discovery.assert_called_once()


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
