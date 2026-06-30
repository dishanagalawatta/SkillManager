from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.core.models.entities import PreparedModelState, Skill


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._sources = ["/src"]
    app._update_packages = []
    app._projects = []
    app._archive_paths = []
    app._starred_paths = []
    app._project_aliases = {}
    app._categories = []
    app._client_format = "Antigravity"
    app._current_project_label = ""
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app.task_runner = MagicMock()
    app.isTesting = True
    return app


@pytest.fixture
def controller(mock_app):
    return DiscoveryController(mock_app)


class TestDiscoveryControllerSDET:
    def test_load_initial_data_triggers_task(self, controller, mock_app):
        controller.loadInitialData()
        mock_app.task_runner.run.assert_called_once()

    @patch("skill_manager.controllers.discovery_controller.DiscoveryService")
    def test_discover_all_background_success(self, mock_service_class, controller, mock_app):
        mock_service = mock_service_class.return_value
        mock_result = {
            "skills": [{"name": "Skill 1", "local_path": "/path/1", "is_package": True}],
            "projects": [],
            "categories": ["Cat 1"],
            "status": "Done",
        }
        mock_service.discover_all.return_value = mock_result

        result = controller._discover_all_background(mock_service, False)

        assert isinstance(result, dict)
        assert len(result["skills"]) == 1
        assert result["skills"][0]["name"] == "Skill 1"
        assert result["categories"] == ["Cat 1"]

    def test_commit_prepared_state_full_set(self, controller, mock_app):
        skill = Skill(name="Skill 1", local_path="/path/1", is_package=True, main_category="")
        state = PreparedModelState(
            all_skills=[skill],
            search_engine=MagicMock(),
            all_filtered_skills=[skill],
            visible_rows=[skill],
            categories=["Cat 1"],
            status="Ready",
            generation=0,
            is_final=True,
        )

        controller._commit_prepared_state(state)

        mock_app._library_model.replacePreparedState.assert_called_once()
        mock_app._quick_copy_model.replacePreparedState.assert_called_once()
        assert mock_app._categories == ["Cat 1"]
        mock_app._set_status.assert_called_with("Ready")

    def test_handle_loading_error(self, controller, mock_app):
        controller._handle_loading_error("Fail")
        mock_app._set_status.assert_called_with("Fail")

    def test_cancellation_supersedes_result(self, controller, mock_app):
        """After incrementing generation, in-flight results are dropped."""
        controller._refresh_generation = 0
        skill = Skill(name="S1", local_path="/p1", is_package=True, main_category="")
        state = PreparedModelState(
            all_skills=[skill],
            search_engine=MagicMock(),
            all_filtered_skills=[skill],
            visible_rows=[skill],
            categories=[],
            status="Done",
            generation=0,
            is_final=True,
        )
        controller._commit_prepared_state(state)
        mock_app._library_model.replacePreparedState.assert_called_once()

        # Now supersede
        mock_app._library_model.replacePreparedState.reset_mock()
        controller._refresh_generation = 1  # Simulate cancellation
        state.generation = 0  # Old generation
        controller._commit_prepared_state(state)
        mock_app._library_model.replacePreparedState.assert_not_called()
