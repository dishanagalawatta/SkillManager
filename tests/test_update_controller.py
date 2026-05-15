import pytest
from unittest.mock import MagicMock, patch
from skill_manager.controllers.update_controller import UpdateController

@pytest.fixture
def mock_app():
    app = MagicMock()
    app._targets = []
    app._update_sources = []
    app._syncing_targets = []
    app._config = MagicMock()
    app._library_model = MagicMock()
    return app

@pytest.fixture
def update_controller(mock_app):
    return UpdateController(mock_app)

@patch("skill_manager.controllers.update_controller.UpdateService")
def test_update_controller_update_now(mock_service_class, update_controller, mock_app):
    mock_app._update_sources = [{"name": "Old"}]
    mock_service = mock_service_class.return_value
    update_controller.update_now()
    
    # Extract the callback passed to run_global_update
    _, kwargs = mock_service.run_global_update.call_args
    source_progress = kwargs["source_progress_callback"]
    completion = kwargs["completion_callback"]
    
    # Trigger source progress
    with patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer:
        source_progress(0, {"name": "S1", "is_updating": False})
        # Execute the lambda passed to singleShot
        mock_timer.call_args[0][2]()
        assert mock_app._update_sources[0]["name"] == "S1"
    
    # Trigger completion
    with patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer:
        completion({"merged": 1, "failed": 0}, [])
        mock_timer.call_args[0][2]() # finalize()
        assert "Global update complete" in mock_app._set_status.call_args[0][0]

@patch("skill_manager.controllers.update_controller.UpdateService")
def test_update_controller_scan(mock_service_class, update_controller, mock_app):
    mock_service = mock_service_class.return_value
    update_controller.scan_for_updates()
    
    # Trigger completion callback
    _, kwargs = mock_service.scan_for_updates.call_args
    completion = kwargs["completion_callback"]
    
    with patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer:
        completion([{"status": "up_to_date"}], [])
        mock_timer.call_args[0][2]() # finalize()
        assert mock_app._update_results[0]["status"] == "up_to_date"
        assert mock_app._is_loading is False

def test_update_controller_recalculate_stats(update_controller, mock_app):
    mock_app._update_results = [
        {"status": "up_to_date"},
        {"status": "outdated"},
        {"status": "missing"}
    ]
    update_controller.recalculate_stats()
    
    assert mock_app._stats_up_to_date == 1
    assert mock_app._stats_outdated == 1
    assert mock_app._stats_missing == 1
    mock_app.statsChanged.emit.assert_called_once()

@patch("skill_manager.core.copier.copy_skill_folders_to_targets")
@patch("skill_manager.controllers.update_controller.QTimer.singleShot")
@patch("threading.Thread")
def test_update_controller_surgical_update(mock_thread, mock_timer, mock_copy, update_controller, mock_app):    
    def side_effect(target, daemon=True):
        target()
        return MagicMock()
    mock_thread.side_effect = side_effect
    mock_copy.return_value = {"failed": 0}

    mock_app._library_model._all_skills = [{"is_source": True, "name": "Skill1"}]
    mock_app._targets = ["/path/target"]
    mock_app.getTargetLabel.return_value = "TargetProject"

    update_controller.update_skill_in_target("Skill1", "TargetProject")

    mock_copy.assert_called_once()
    mock_app._set_status.assert_any_call("Updating Skill1 in TargetProject...")
    mock_timer.assert_called()

