import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from skill_manager.core.skill_sources import (
    normalize_skill_source_config,
    detect_source_config,
    run_skill_source_update,
    _relocate_skills_from_output
)

def test_normalize_skill_source_config():
    data = {"package_name": "test-package"}
    normalized = normalize_skill_source_config(data)
    assert normalized["name"] == "test-package"
    assert normalized["source_type"] == "npm"
    assert "npx --yes test-package" in normalized["update_command"]

def test_detect_source_config_npm():
    data = {"package_name": "npx --yes my-pkg --foo"}
    detected = detect_source_config(data)
    assert detected["source_type"] == "npm"
    assert detected["package_name"] == "my-pkg"
    assert detected["install_args"] == "--foo"

def test_detect_source_config_git():
    data = {"source_type": "git", "repository_url": "http://git.com/repo"}
    detected = detect_source_config(data)
    assert detected["source_type"] == "git"

def test_relocate_skills_from_output(temp_dir):
    target_path = temp_dir / "project_skills"
    target_path.mkdir()
    
    # Create a dummy skill in a temp location
    source_skill_dir = temp_dir / "some_random_path" / "caveman"
    source_skill_dir.mkdir(parents=True)
    (source_skill_dir / "SKILL.md").write_text("content")
    
    output = [f"Installed to {source_skill_dir}"]
    
    _relocate_skills_from_output(output, str(target_path), None)
    
    # Check if it moved
    assert (target_path / "caveman").is_dir()
    assert (target_path / "caveman" / "SKILL.md").exists()
    assert not source_skill_dir.exists()

@patch("skill_manager.core.skill_sources._run_process")
@patch("skill_manager.core.skill_sources.run_version_command")
def test_run_skill_source_update(mock_version, mock_run):
    source = {"source_type": "custom", "update_command": "echo 'hi'", "name": "test"}
    mock_version.return_value = "1.0.0"
    
    updated = run_skill_source_update(source)
    
    assert updated["current_version"] == "1.0.0"
    assert "last_updated" in updated
    mock_run.assert_called_once()
