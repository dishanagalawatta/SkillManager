import pytest
from unittest.mock import MagicMock, patch
from skill_manager.core.update_service import UpdateService

@pytest.fixture
def service():
    return UpdateService(
        sources=["/src"],
        targets=["/target"],
        update_sources=[{"name": "S1", "url": "url1"}]
    )

@patch("skill_manager.core.update_service.run_skill_source_update")
@patch("skill_manager.core.update_service.discover_project_skills")
@patch("skill_manager.core.update_service.copy_skill_folders_to_targets")
def test_run_global_update(mock_copy, mock_proj, mock_src_upd, service):
    mock_src_upd.return_value = {"name": "S1", "removed_folders": ["old_f"]}
    mock_proj.return_value = [{"project_label": "P1", "skills": []}]
    mock_copy.return_value = {"merged": 1, "failed": 0}
    
    status_cb = MagicMock()
    progress_cb = MagicMock()
    comp_cb = MagicMock()
    
    # We test the logic inside the thread (calling directly for simplicity in mock test)
    with patch("threading.Thread") as mock_thread:
        mock_instance = MagicMock()
        mock_thread.return_value = mock_instance
        # Make the thread run immediately for testing logic
        mock_instance.start.side_effect = lambda: run_global_update_logic()
        
        # We need to capture the inner function. 
        # A better way: refactor Service to have a non-threaded method, but for now:
        def run_global_update_logic():
            # This is a bit tricky because the function is local.
            # Let's just mock Thread to run the target.
            pass

    # Actually, a simpler way to test threaded logic is to mock Thread to just execute the target
    with patch("threading.Thread") as mock_thread:
        def side_effect(target, daemon=True):
            target()
            return MagicMock()
        mock_thread.side_effect = side_effect
        service.run_global_update(status_cb, progress_cb, comp_cb)
    
    assert mock_src_upd.called
    assert mock_copy.called
    assert comp_cb.called

@patch("skill_manager.core.update_service.discover_source_skills")
@patch("skill_manager.core.update_service.discover_project_skills")
@patch("skill_manager.core.update_service.check_skill_source_versions")
def test_scan_for_updates(mock_check, mock_proj, mock_src, service):
    mock_src.return_value = [{"name": "Skill1", "folder_name": "f1"}]
    mock_proj.return_value = [{"project_label": "P1", "skills": []}]
    mock_check.return_value = {"name": "S1", "latest_version": "2.0"}
    
    status_cb = MagicMock()
    comp_cb = MagicMock()
    
    with patch("threading.Thread") as mock_thread:
        def side_effect(target, daemon=True):
            target()
            return MagicMock()
        mock_thread.side_effect = side_effect
        service.scan_for_updates(status_cb, comp_cb)
    
    assert comp_cb.called
    results, sources = comp_cb.call_args[0]
    assert results[0]["status"] == "missing"
    assert sources[0]["latest_version"] == "2.0"
    assert status_cb.called
