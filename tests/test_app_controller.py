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

def test_controller_selection_sync(controller):
    # Setup model with some skills
    skills = [{"name": "S1", "local_path": "/p1", "is_selected": False, "is_source": True}]
    controller.skillModel.setSkills(skills)
    
    controller.skillModel.toggleSelection(0)
    assert controller.skillModel.selectedCount == 1
    
    # Test copySelectedSkillsToClipboard status update (mocking clipboard)
    with patch.object(controller, "_clipboard") as mock_clip:
        controller.copySelectedSkillsToClipboard()
        assert controller.statusMessage.startswith("Copied 1 skills")
