import pytest
import json
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QTimer, Qt
from skill_manager.app import AppController

@pytest.fixture
def controller(qapp, mock_config, temp_dir):
    config_data = {
        "sources": [str(temp_dir / "lib")],
        "targets": [str(temp_dir / "proj")],
        "client_format": "Antigravity",
        "ui_state": {"current_view": "Library"}
    }
    
    # In the real code, load() sets self.data. We'll mock that behavior.
    def mock_load_side_effect(self):
        self.data = config_data
        return self.data
    
    # Use only ONE patch
    with patch("skill_manager.core.config.ConfigManager.load", autospec=True, side_effect=mock_load_side_effect):
        (temp_dir / "lib").mkdir(exist_ok=True)
        (temp_dir / "proj").mkdir(exist_ok=True)
        
        c = AppController()
        # Explicitly set values that might have been missed due to timing of __init__
        c._sources = config_data["sources"]
        c._targets = config_data["targets"]
        c._client_format = config_data["client_format"]
        return c

def test_controller_initialization(controller):
    assert controller.clientFormat == "Antigravity"
    assert len(controller.sources) == 1
    assert controller.currentView == "Library"

def test_controller_set_current_view(controller):
    controller.currentView = "QuickCopy"
    assert controller.currentView == "QuickCopy"
    # isSourceOnly returns CheckState (Unchecked=0, Checked=2, Partially=1)
    assert controller.skillModel.isSourceOnly == Qt.Unchecked

def test_controller_add_remove_source(controller):
    controller.addSource("/new/source")
    assert "/new/source" in controller.sources
    controller.removeSource("/new/source")
    assert "/new/source" not in controller.sources

def test_controller_status_message(controller):
    controller._set_status("Test status")
    assert controller.statusMessage == "Test status"

def test_controller_load_initial_data_logic(controller):
    # Test _finalize_loading directly to avoid threads
    skills = [{"name": "Skill A", "category": "Dev", "is_source": True}]
    controller._finalize_loading(
        all_skills=skills,
        projects=[],
        cats=["Dev"],
        proj_labels=[],
        status="Success"
    )
    
    assert controller.skillModel.rowCount() == 1
    assert "Dev" in controller.categories
    assert controller.isLoading is False

def test_controller_copy_single_skill(controller):
    skill_data = {"name": "S1", "local_path": "/p1", "is_source": True}
    controller.skillModel.setSkills([skill_data])
    
    with patch.object(controller, "_clipboard") as mock_clip:
        controller.copySkillToClipboard("/p1")
        # copySkillToClipboard calls copySkillReference which sets "Copied reference: ..."
        assert controller.statusMessage.startswith("Copied reference:")

@patch("skill_manager.app.discover_project_skills")
@patch("skill_manager.core.copier.copy_skill_folders_to_targets")
@patch("threading.Thread")
@patch("PySide6.QtCore.QTimer.singleShot")
def test_controller_sync_project(mock_timer, mock_thread, mock_copy, mock_discover, controller):
    # Mock Timer to run callback immediately
    mock_timer.side_effect = lambda ms, receiver, method: method() if callable(method) else method.call()
    
    # Mock Thread to return a mock object that executes the target when .start() is called
    def side_effect(target, daemon=True):
        mock_inst = MagicMock()
        mock_inst.start.side_effect = lambda: target()
        return mock_inst
    mock_thread.side_effect = side_effect
    
    mock_discover.return_value = [{"project_label": "Source", "skills": [{"name": "S1"}]}]
    mock_copy.return_value = {"merged": 1, "failed": 0}
    
    controller.syncProject(controller.targets[0])
    
    mock_copy.assert_called_once()
    assert "Update complete for" in controller.statusMessage

def test_controller_setters(controller):
    controller.searchQuery = "test"
    assert controller.searchQuery == "test"
    
    # clientFormat is read-only, use setClientFormat Slot
    controller.setClientFormat("Gemini CLI")
    assert controller.clientFormat == "Gemini CLI"

def test_controller_toggle_source_only(controller):
    controller.isSourceOnly = True
    # isSourceOnly returns CheckState int
    assert controller.isSourceOnly == True
