import pytest
import shutil
from pathlib import Path
from skill_manager.core.copier import copy_skill_folders_to_targets

@pytest.fixture
def skill_source(temp_dir):
    skill_dir = temp_dir / "sources" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("test content")
    return skill_dir

def test_copy_skill_folders_to_targets_success(temp_dir, skill_source):
    target_dir = temp_dir / "projects" / "target-a"
    target_dir.mkdir(parents=True)
    
    skills = [{"name": "Test Skill", "local_path": str(skill_source)}]
    targets = [str(target_dir)]
    
    result = copy_skill_folders_to_targets(skills, targets)
    
    assert result["copied"] == 1
    assert (target_dir / "test-skill").is_dir()
    assert (target_dir / "test-skill" / "SKILL.md").exists()

def test_copy_skill_folders_to_targets_merge(temp_dir, skill_source):
    target_dir = temp_dir / "projects" / "target-a"
    skill_in_target = target_dir / "test-skill"
    skill_in_target.mkdir(parents=True)
    
    skills = [{"name": "Test Skill", "local_path": str(skill_source)}]
    targets = [str(target_dir)]
    
    result = copy_skill_folders_to_targets(skills, targets)
    
    assert result["merged"] == 1
    assert (target_dir / "test-skill" / "SKILL.md").exists()

def test_copy_skill_folders_to_targets_missing_skill_md(temp_dir):
    skill_dir = temp_dir / "invalid-skill"
    skill_dir.mkdir() # No SKILL.md
    
    target_dir = temp_dir / "target"
    target_dir.mkdir()
    
    skills = [{"name": "Invalid", "local_path": str(skill_dir)}]
    targets = [str(target_dir)]
    
    result = copy_skill_folders_to_targets(skills, targets)
    assert result["skipped"] == 1
    assert "missing SKILL.md" in result["details"][0]["message"]

def test_copy_skill_folders_to_targets_update_only(temp_dir, skill_source):
    target_dir = temp_dir / "target"
    target_dir.mkdir()
    
    skills = [{"name": "Test Skill", "local_path": str(skill_source)}]
    targets = [str(target_dir)]
    
    # Target doesn't have the skill, and we set update_only=True
    result = copy_skill_folders_to_targets(skills, targets, update_only=True)
    
    assert result["copied"] == 0
    assert not (target_dir / "test-skill").exists()
