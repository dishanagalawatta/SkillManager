from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.core.schemas import CacheState, SkillRecord


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
        assert mock_app._is_loading is True
        mock_app.isLoadingChanged.emit.assert_called()
        mock_app.task_runner.submit.assert_called_once()

    @patch("skill_manager.controllers.discovery_controller.DiscoveryService")
    def test_run_discovery_sync_success(self, mock_service_class, controller, mock_app):
        mock_service = mock_service_class.return_value
        mock_result = {
            "skills": [{"name": "Skill 1", "local_path": "/path/1"}],
            "projects": [],
            "categories": ["Cat 1"],
            "project_labels": [],
            "status": "Done"
        }
        mock_service.discover_all.return_value = mock_result

        result = controller._run_discovery_sync()

        assert isinstance(result, CacheState)
        assert len(result.skills) == 1
        assert result.skills[0].name == "Skill 1"
        assert result.categories == ["Cat 1"]

    def test_finalize_loading_full_set(self, controller, mock_app):
        state = CacheState(
            skills=[SkillRecord(name="Skill 1", local_path="/path/1")],
            categories=["Cat 1"],
            status="Ready"
        )

        controller._finalize_loading(state, is_final=True)

        mock_app._library_model.setSkills.assert_called_once()
        mock_app._quick_copy_model.setSkills.assert_called_once()
        assert mock_app._categories == ["Cat 1"]
        assert mock_app._is_loading is False
        mock_app._set_status.assert_called_with("Ready")

    def test_incremental_update_diffing(self, controller, mock_app):
        # 1. First load
        s1 = SkillRecord(name="Skill 1", local_path="/path/1")
        state1 = CacheState(skills=[s1], status="First")
        controller._finalize_loading(state1, is_final=True)

        # 2. Incremental update (add s2, update s1)
        s1_updated = SkillRecord(name="Skill 1 Updated", local_path="/path/1")
        s2 = SkillRecord(name="Skill 2", local_path="/path/2")
        state2 = CacheState(skills=[s1_updated, s2], status="Updated")

        controller._finalize_loading(state2, is_final=True)

        # Verify addOrUpdateSkills was called with both
        # We need to capture the arguments
        calls = mock_app._library_model.addOrUpdateSkills.call_args_list
        assert len(calls) == 1
        added_updated = calls[0][0][0]
        assert len(added_updated) == 2
        assert added_updated[0]["name"] == "Skill 1 Updated"
        assert added_updated[1]["name"] == "Skill 2"

    def test_incremental_removal(self, controller, mock_app):
        # 1. First load
        s1 = SkillRecord(name="Skill 1", local_path="/path/1")
        s2 = SkillRecord(name="Skill 2", local_path="/path/2")
        state1 = CacheState(skills=[s1, s2])
        controller._finalize_loading(state1)

        # 2. Remove s1
        state2 = CacheState(skills=[s2])
        controller._finalize_loading(state2)

        mock_app._library_model.removeSkillsByPath.assert_called_once_with(["/path/1"])

    def test_handle_loading_error(self, controller, mock_app):
        controller._handle_loading_error("Fail")
        assert mock_app._is_loading is False
        mock_app._set_status.assert_called_with("Fail")

    @patch("skill_manager.controllers.discovery_controller.DiscoveryService")
    def test_cache_callback_validation(self, mock_service_class, controller, mock_app):
        mock_service = mock_service_class.return_value

        # Setup signals to capture emissions
        success_emitted = []
        controller._discoverySuccess.connect(lambda state, final: success_emitted.append(state))

        def mock_discover(cache_callback):
            cache_callback({"skills": [{"name": "Cached", "local_path": "/c"}], "status": "From Cache"})
            return {"skills": [], "status": "Final"}

        mock_service.discover_all.side_effect = mock_discover

        controller._run_discovery_sync()

        assert len(success_emitted) == 1
        assert success_emitted[0].skills[0].name == "Cached"
        assert success_emitted[0].status == "From Cache"
