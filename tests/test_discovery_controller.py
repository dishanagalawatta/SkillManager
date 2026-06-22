from unittest.mock import MagicMock

import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.core.schemas import CacheState, SkillRecord


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
    state = CacheState(
        skills=[SkillRecord(name="S1", local_path="/p/s1")],
        categories=["Cat1"],
        project_labels=["L"],
        status="Finished",
    )

    controller._finalize_loading(state, is_final=True)

    assert mock_app._categories == ["Cat1"]
    mock_app.categoriesChanged.emit.assert_called_once()
    mock_app._library_model.setSkills.assert_called()
    mock_app._quick_copy_model.setSkills.assert_called()
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
    state = CacheState(
        skills=[],
        categories=[],
        project_labels=[],
        status="Status",
    )
    controller._finalize_loading(state, is_final=False)
    assert mock_app._quick_copy_model.projectFilter == "MyProject"


def test_finalize_loading_incremental_update_refreshes_selection(controller, mock_app):
    """Incremental discovery update calls _refresh_selected_skill for each changed skill."""
    controller._previous_skills = {
        "/p/s1": SkillRecord(name="S1", local_path="/p/s1", category="Dev"),
    }
    state = CacheState(
        skills=[SkillRecord(name="S1", local_path="/p/s1", category="Dev", body_content="updated")],
        categories=["Dev"],
        project_labels=["L"],
        status="Finished",
    )
    mock_app.ops = MagicMock()
    controller._finalize_loading(state, is_final=False)

    mock_app.ops._refresh_selected_skill.assert_called_with("/p/s1")
    mock_app._library_model.addOrUpdateSkills.assert_called_once()
    mock_app._quick_copy_model.addOrUpdateSkills.assert_called_once()


def test_finalize_loading_full_load_does_not_refresh_selection(controller, mock_app):
    """Full load (first scan) does not call _refresh_selected_skill."""
    mock_app.ops = MagicMock()
    state = CacheState(
        skills=[SkillRecord(name="S1", local_path="/p/s1")],
        categories=["Dev"],
        project_labels=["L"],
        status="Finished",
    )
    controller._finalize_loading(state, is_final=True)

    mock_app.ops._refresh_selected_skill.assert_not_called()
    mock_app._library_model.setSkills.assert_called_once()
    mock_app._quick_copy_model.setSkills.assert_called_once()


def test_finalize_loading_safety_net_preserves_cache(controller, mock_app):
    """When final discovery returns 0 skills but cache had skills, preserve them."""
    # Simulate previous scan had skills
    controller._previous_skills = {
        "/p/s1": SkillRecord(name="S1", local_path="/p/s1", category="Dev"),
        "/p/s2": SkillRecord(name="S2", local_path="/p/s2", category="Dev"),
    }
    # Final discovery returns 0 skills (source dirs missing)
    state = CacheState(
        skills=[],
        categories=[],
        project_labels=[],
        status="Found 0 skills (0 projects)",
    )
    mock_app.ops = MagicMock()
    controller._finalize_loading(state, is_final=True)

    # Should NOT remove skills from model
    mock_app._library_model.removeSkillsByPath.assert_not_called()
    mock_app._quick_copy_model.removeSkillsByPath.assert_not_called()
    # Should NOT call setSkills (full replacement)
    mock_app._library_model.setSkills.assert_not_called()
    mock_app._quick_copy_model.setSkills.assert_not_called()
    # Should set loading to False
    assert mock_app._is_loading is False
    mock_app.isLoadingChanged.emit.assert_called()
    # Status should mention the warning
    status_call = mock_app._set_status.call_args[0][0]
    assert "Warning" in status_call or "missing" in status_call.lower()


def test_finalize_loading_safety_net_not_triggered_for_non_final(controller, mock_app):
    """Safety net only triggers on final discovery, not intermediate cache loads."""
    controller._previous_skills = {
        "/p/s1": SkillRecord(name="S1", local_path="/p/s1", category="Dev"),
    }
    # Non-final (cache callback) returns 0 skills — should NOT trigger safety net
    state = CacheState(
        skills=[],
        categories=[],
        project_labels=[],
        status="Found 0 skills",
    )
    mock_app.ops = MagicMock()
    controller._finalize_loading(state, is_final=False)

    # Non-final with 0 skills and previous skills: removed_paths is non-empty,
    # but is_final=False means the safety net doesn't trigger.
    # It falls through to the incremental update path which removes old skills.
    mock_app._library_model.removeSkillsByPath.assert_called_once()
