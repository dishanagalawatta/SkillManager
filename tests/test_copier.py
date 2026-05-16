import os
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch
from skill_manager.core.copier import copy_skill_folders_to_targets

@pytest.fixture
def temp_dir(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    return source, target

def test_copy_skill_folders_to_targets_success(temp_dir):
    source, target = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")
    (skill_dir / "data.txt").write_text("data")
    
    skills = [{"local_path": str(skill_dir), "name": "Test Skill"}]
    targets = [str(target)]
    
    result = copy_skill_folders_to_targets(skills, targets)
    
    assert result["copied"] == 1
    assert (target / "test_skill" / "SKILL.md").exists()
    assert (target / "test_skill" / "data.txt").read_text() == "data"

def test_copy_skill_folders_to_targets_update_only(temp_dir):
    source, target = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")
    
    skills = [{"local_path": str(skill_dir), "name": "Test Skill"}]
    targets = [str(target)]
    
    # First run with update_only=True should skip because it doesn't exist in target
    result = copy_skill_folders_to_targets(skills, targets, update_only=True)
    assert result["copied"] == 0
    assert not (target / "test_skill").exists()
    
    # Create it in target then run update_only=True
    (target / "test_skill").mkdir()
    result = copy_skill_folders_to_targets(skills, targets, update_only=True)
    assert result["merged"] == 1
    assert (target / "test_skill" / "SKILL.md").exists()

def test_copy_skill_folders_to_targets_missing_skill_md(temp_dir):
    source, target = temp_dir
    skill_dir = source / "bad_skill"
    skill_dir.mkdir()
    # No SKILL.md
    
    skills = [{"local_path": str(skill_dir), "name": "Bad Skill"}]
    targets = [str(target)]
    
    result = copy_skill_folders_to_targets(skills, targets)
    assert result["skipped"] == 1
    assert "missing SKILL.md" in result["details"][0]["message"]

def test_copy_skill_folders_to_targets_invalid_target(temp_dir):
    source, target = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")
    
    # Target is a file, not a directory
    bad_target = target / "file.txt"
    bad_target.write_text("not a dir")
    
    skills = [{"local_path": str(skill_dir)}]
    targets = [str(bad_target)]
    
    result = copy_skill_folders_to_targets(skills, targets)
    assert result["skipped"] == 1
    assert "not a folder" in result["details"][0]["message"]

def test_copy_skill_folders_to_targets_permission_denied(temp_dir):
    source, target = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")
    
    skills = [{"local_path": str(skill_dir)}]
    targets = [str(target)]
    
    with patch("shutil.copytree", side_effect=PermissionError("Permission Denied")):
        result = copy_skill_folders_to_targets(skills, targets)
        assert result["failed"] == 1
        assert "Permission Denied" in result["details"][0]["message"]

def test_copy_skill_folders_to_targets_mkdir_failure(temp_dir):
    source, target = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")
    
    skills = [{"local_path": str(skill_dir)}]
    # Path that doesn't exist but has an existing parent, so it passes normalization
    target_path = target / "new_dir"
    targets = [str(target_path)]
    
    # Mock mkdir to fail even if it passes the pre-normalization check
    with patch("pathlib.Path.mkdir", side_effect=OSError("Drive Read Only")):
        result = copy_skill_folders_to_targets(skills, targets)
        assert result["failed"] == 1
        assert "Drive Read Only" in result["details"][0]["message"]

def test_copy_skill_folders_to_targets_normalization_failure(temp_dir):
    source, target = temp_dir
    skill_dir = source / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")
    
    skills = [{"local_path": str(skill_dir)}]
    # Normalization fails if parent doesn't exist
    targets = [str(target / "nonexistent" / "target")]
    
    result = copy_skill_folders_to_targets(skills, targets)
    assert result["skipped"] == 1
    assert "parent folder does not exist" in result["details"][0]["message"]
