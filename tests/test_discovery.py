import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from skill_manager.core.discovery import DiscoveryService

@pytest.fixture
def service():
    return DiscoveryService(
        sources=["/src1"],
        targets=["/target1"],
        archive_paths=[],
        essential_paths=[]
    )

def test_transform_skill_source(service):
    skill = {
        "name": "Test Skill",
        "local_path": "/src1/skill1",
        "category": "Test",
        "metadata": {"risk": "High"}
    }
    transformed = service._transform_skill(skill, is_source=True)
    assert transformed["name"] == "Test Skill"
    assert transformed["is_source"] is True
    assert transformed["risk"] == "High"
    assert transformed["project_label"] == "Master Library"

def test_transform_skill_project(service):
    skill = {
        "name": "Proj Skill",
        "local_path": "/target1/skillA",
        "category": "Dev",
        "skill_base_relative": "skillA",
        "folder_name": "skillA"
    }
    transformed = service._transform_skill(skill, is_source=False, project_label="My Project")
    assert transformed["name"] == "Proj Skill"
    assert transformed["is_source"] is False
    assert transformed["project_label"] == "My Project"
    assert transformed["folder_name"] == "skillA"

@patch("skill_manager.core.discovery.discover_source_skills")
@patch("skill_manager.core.discovery.discover_project_skills")
@patch("skill_manager.core.discovery.save_cache")
@patch("skill_manager.core.discovery.load_cache")
def test_discover_all(mock_load, mock_save, mock_proj, mock_src, service):
    mock_load.return_value = None
    mock_src.return_value = [{"name": "S1", "local_path": "/s1", "category": "Cat1"}]
    mock_proj.return_value = [{
        "project_label": "P1",
        "target_path": "/t1",
        "skills": [{"name": "P1S1", "local_path": "/t1/s1", "category": "Cat2"}]
    }]
    
    result = service.discover_all(use_cache=False)
    
    assert len(result["skills"]) == 2
    assert "Cat1" in result["categories"]
    assert "Cat2" in result["categories"]
    assert "P1" in result["project_labels"]
    assert mock_save.called
