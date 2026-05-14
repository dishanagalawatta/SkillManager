import pytest
from pathlib import Path
from skill_manager.core.quick_copy import (
    format_project_skill_reference,
    project_label,
    discover_source_skills,
    _resolve_resilient_path
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
