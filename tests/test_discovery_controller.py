from unittest.mock import MagicMock

import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.core.models.entities import PreparedModelState, Skill
from skill_manager.core.schemas import SkillRecord


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
    mock_app.task_runner.run.assert_called_once()


def test_commit_prepared_state(controller, mock_app):
    """_commit_prepared_state applies prepared state to models."""
    skill = Skill(name="S1", local_path="/p/s1", is_package=True, main_category="")
    state = PreparedModelState(
        all_skills=[skill],
        search_engine=MagicMock(),
        all_filtered_skills=[skill],
        visible_rows=[skill],
        categories=["Cat1"],
        status="Finished",
        generation=0,
        is_final=True,
    )
    controller._commit_prepared_state(state)

    mock_app._library_model.replacePreparedState.assert_called_once()
    mock_app._quick_copy_model.replacePreparedState.assert_called_once()


def test_handle_loading_error(controller, mock_app):
    controller._handle_loading_error("Error occurred")
    mock_app._set_status.assert_called_with("Error occurred")


def test_commit_prepared_state_with_project_label(controller, mock_app):
    mock_app._current_project_label = "MyProject"
    state = PreparedModelState(
        all_skills=[],
        search_engine=MagicMock(),
        all_filtered_skills=[],
        visible_rows=[],
        categories=[],
        status="Status",
        generation=0,
        is_final=False,
    )
    controller._commit_prepared_state(state)
    assert mock_app._quick_copy_model.projectFilter == "MyProject"


def test_commit_prepared_state_safety_net_preserves_cache(controller, mock_app):
    """When final discovery returns 0 skills but cache had skills, preserve them."""
    # Simulate previous scan had skills
    controller._previous_skills = {
        "/p/s1": SkillRecord(name="S1", local_path="/p/s1", category="Dev"),
        "/p/s2": SkillRecord(name="S2", local_path="/p/s2", category="Dev"),
    }
    # Final discovery returns 0 skills (source dirs missing)
    state = PreparedModelState(
        all_skills=[],
        search_engine=MagicMock(),
        all_filtered_skills=[],
        visible_rows=[],
        categories=[],
        status="Found 0 skills (0 projects)",
        generation=0,
        is_final=True,
    )
    mock_app.ops = MagicMock()
    controller._commit_prepared_state(state)

    # Should NOT replace skills in model
    mock_app._library_model.replacePreparedState.assert_not_called()
    mock_app._quick_copy_model.replacePreparedState.assert_not_called()


def test_commit_prepared_state_safety_net_not_triggered_for_non_final(controller, mock_app):
    """Safety net only triggers on final discovery, not intermediate cache loads."""
    controller._previous_skills = {
        "/p/s1": SkillRecord(name="S1", local_path="/p/s1", category="Dev"),
    }
    # Non-final (cache callback) returns 0 skills — should NOT trigger safety net
    state = PreparedModelState(
        all_skills=[],
        search_engine=MagicMock(),
        all_filtered_skills=[],
        visible_rows=[],
        categories=[],
        status="Found 0 skills",
        generation=0,
        is_final=False,
    )
    mock_app.ops = MagicMock()
    controller._commit_prepared_state(state)

    # Non-final with 0 skills: model IS updated (safety net doesn't trigger)
    mock_app._library_model.replacePreparedState.assert_called_once()
