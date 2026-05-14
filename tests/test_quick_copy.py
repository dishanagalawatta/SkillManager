import pytest
from pathlib import Path
from unittest.mock import patch
from skill_manager.core.quick_copy import (
    format_project_skill_reference,
    project_label,
    discover_source_skills,
    _resolve_resilient_path,
    delete_project_skill_folders
)

def test_resolve_resilient_path(temp_dir):
    agent_dir = temp_dir / ".agent"
    agent_dir.mkdir()
    
    # Try resolving .agents when only .agent exists
    res = _resolve_resilient_path(temp_dir / ".agents")
    assert res.name == ".agent"

def test_project_label_standard():
    path = Path("/work/my-project/.agents/skills")
    label = project_label(path)
    assert label == "my-project"

def test_project_label_alias():
    path = Path("/work/p1")
    aliases = {"/work/p1": "My Legacy Project"}
    label = project_label(path, target_aliases=aliases)
    assert label == "My Legacy Project"

def test_format_project_skill_reference_codex():
    skill = {
        "name": "Test",
        "skill_md_path": "/path/to/SKILL.md",
        "local_path": "/path/to"
    }
    ref = format_project_skill_reference(skill, "Codex")
    assert ref == "[$Test](/path/to/SKILL.md)"

def test_format_project_skill_reference_gemini():
    skill = {
        "folder_name": "test-skill",
        "skill_base_relative": ".agents/skills",
        "local_path": "/root/.agents/skills/test-skill"
    }
    ref = format_project_skill_reference(skill, "Gemini CLI")
    assert ref == "@.agents/skills/test-skill/SKILL.md"

def test_discover_source_skills(temp_dir):
    source_dir = temp_dir / "library"
    skill_dir = source_dir / "alpha"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: Alpha\n---\n")
    
    def mock_parse(p): return {"name": "Alpha"}
    def mock_cat(n, d): return "Cat"
    def mock_search(s): return "search"
    
    skills = discover_source_skills([str(source_dir)], mock_parse, mock_cat, mock_search)
    assert len(skills) == 1
    assert skills[0]["name"] == "Alpha"
    assert skills[0]["is_source"] is True

def test_delete_project_skill_folders_success(temp_dir):
    target_dir = temp_dir / "project"
    target_dir.mkdir()
    skill_dir = target_dir / "skill-a"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("info")

    skills = [{
        "name": "Skill A",
        "local_path": str(skill_dir),
        "target_path": str(target_dir)
    }]

    result = delete_project_skill_folders(skills)

    assert result["deleted"] == 1
    assert not skill_dir.exists()
    assert result["details"][0]["status"] == "deleted"

def test_delete_project_skill_folders_validation_errors(temp_dir):
    target_dir = temp_dir / "project"
    target_dir.mkdir()

    skill_dir = target_dir / "skill-a"
    skill_dir.mkdir()
    # No SKILL.md here yet

    skills = [
        {
            "name": "Missing Target",
            "local_path": str(skill_dir),
            "target_path": str(temp_dir / "non-existent")
        },
        {
            "name": "Missing Source",
            "local_path": str(temp_dir / "no-skill"),
            "target_path": str(target_dir)
        },
        {
            "name": "Not Direct Child",
            "local_path": str(temp_dir), # temp_dir is parent of target_dir, not child
            "target_path": str(target_dir)
        },
        {
            "name": "Missing SKILL.md",
            "local_path": str(skill_dir),
            "target_path": str(target_dir)
        }
    ]

    result = delete_project_skill_folders(skills)

    assert result["skipped"] == 4
    assert result["deleted"] == 0
    assert "Target folder does not exist" in result["details"][0]["message"]
    assert "Skill folder does not exist" in result["details"][1]["message"]
    assert "Skill folder is not a direct child" in result["details"][2]["message"]
    assert "Skill folder is missing SKILL.md" in result["details"][3]["message"]

def test_delete_project_skill_folders_failure(temp_dir):
    target_dir = temp_dir / "project"
    target_dir.mkdir()
    skill_dir = target_dir / "skill-a"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("info")

    skills = [{
        "name": "Skill A",
        "local_path": str(skill_dir),
        "target_path": str(target_dir)
    }]

    with patch("skill_manager.core.quick_copy.shutil.rmtree") as mock_rmtree:
        mock_rmtree.side_effect = OSError("Permission denied")
        result = delete_project_skill_folders(skills)

    assert result["failed"] == 1
    assert result["details"][0]["status"] == "failed"
    assert "Permission denied" in result["details"][0]["message"]
