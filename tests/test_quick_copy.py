import pytest
from pathlib import Path
from unittest.mock import patch
from skill_manager.core.quick_copy import (
    format_project_skill_reference,
    project_label,
    discover_source_skills,
    discover_project_skills,
    _resolve_resilient_path,
    delete_project_skill_folders,
    normalize_manual_references,
    normalize_manual_reference,
    merge_manual_references,
    _normalize_path,
    _looks_like_explicit_reference,
    _project_root_for_target,
    _classification_text
)

def test_normalize_manual_reference():
    assert normalize_manual_reference("test") == "@test"
    assert normalize_manual_reference("@test") == "@test"
    assert normalize_manual_reference("[link](path)") == "[link](path)"
    assert normalize_manual_reference("path/to/file.md") == "path/to/file.md"
    assert normalize_manual_reference("C:\\path") == "C:\\path"
    assert normalize_manual_reference("") == ""

def test_normalize_manual_references():
    text = "ref1\n@ref2\nref1" # Deduplication
    refs = normalize_manual_references(text)
    assert refs == ["@ref1", "@ref2"]

def test_merge_manual_references():
    existing = ["@ref1"]
    additions = ["ref2", "ref1"]
    merged = merge_manual_references(existing, additions)
    assert merged == ["@ref1", "@ref2"]

def test_normalize_path():
    assert _normalize_path("C:\\Path\\To/File").lower() == "c:/path/to/file"
    assert _normalize_path("") == ""

def test_discover_project_skills_success(temp_dir):
    project_dir = temp_dir / "my-project"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    
    skill_a = skills_dir / "alpha"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text("---\nname: Alpha\n---\n")
    
    def mock_parse(p): return {"name": "Alpha"}
    def mock_cat(n, d): return "Cat"
    def mock_search(s): return "search"
    
    projects = discover_project_skills([str(skills_dir)], mock_parse, mock_cat, mock_search)
    assert len(projects) == 1
    assert projects[0]["project_label"] == "my-project"
    assert len(projects[0]["skills"]) == 1
    assert projects[0]["skills"][0]["name"] == "Alpha"

def test_project_label_non_standard_base():
    path = Path("/work/proj/custom/skills")
    # Marker not found, root = path.parent (/work/proj/custom), base = skills
    assert project_label(path) == "custom (skills)"

def test_resolve_resilient_path_swapping(temp_dir):
    # Test swapping .agent <-> .agents
    agent_dir = temp_dir / ".agent"
    agent_dir.mkdir()
    
    # Passing .agents should resolve to .agent
    res = _resolve_resilient_path(temp_dir / ".agents")
    assert res.name == ".agent"
    
    # Passing .agent/sub should resolve to .agent/sub (if exists, but we test the logic)
    # Actually it only resolves IF it exists.
    
def test_project_label_normalization(temp_dir):
    # Test normalization in project_label aliases
    path = "C:\\Work\\Proj"
    aliases = {"C:/Work/Proj": "Normalized Alias", "c:/work/proj": "Normalized Alias"}
    assert project_label(path, aliases) == "Normalized Alias"

def test_format_project_skill_reference_error_handling():
    # Test relative_to failure in command formatting
    skill = {
        "is_command": True,
        "project_root": "/other/root",
        "local_path": "/work/proj/manuals/cmd.md"
    }
    # /work/proj/manuals/cmd.md is not relative to /other/root
    ref = format_project_skill_reference(skill, "Plain Path")
    assert ref == "cmd.md"

def test_skill_base_relative_error():
    # Test ValueError in relative_to
    path = Path("/some/path")
    # _project_root_for_target returns /some (parent)
    # relative_to(/some) succeeds normally. 
    # To force error, we need a root that is not a parent.
    with patch("skill_manager.core.quick_copy._project_root_for_target") as mock_root:
        mock_root.return_value = Path("/different/root")
        from skill_manager.core.quick_copy import _skill_base_relative
        assert _skill_base_relative(path) == "path"

def test_discover_source_skills_duplicates(temp_dir):
    source_dir = temp_dir / "library"
    source_dir.mkdir()
    
    # Discovery twice with same path (should deduplicate)
    skills = discover_source_skills([str(source_dir), str(source_dir)], lambda p: {}, lambda n, d: "C", lambda s: "s")
    # No skills found but should only scan once (seen_sources set)
    assert len(skills) == 0

def test_resolve_resilient_path_none():
    assert str(_resolve_resilient_path(None)) == "."
    assert str(_resolve_resilient_path("")) == "."

def test_project_label_complex(temp_dir):
    target = temp_dir / "proj" / ".agents" / "skills"
    target.mkdir(parents=True)
    
    # Test with original target and aliases
    aliases = {"orig": "Alias"}
    assert project_label(target, aliases, "orig") == "Alias"
    
    # Test with normalized alias
    norm_alias = {"C:/Path": "Normalized", "c:/path": "Normalized"}
    assert project_label("C:\\Path", norm_alias) == "Normalized"

def test_format_project_skill_reference_command_fallback():
    # command without project_root but has manuals in path
    skill = {
        "is_command": True,
        "local_path": "/work/myproj/manuals/deploy.md"
    }
    ref = format_project_skill_reference(skill, "Gemini CLI")
    assert ref == "@manuals/deploy.md"
    
    # command without project_root AND no manuals in path
    skill2 = {
        "is_command": True,
        "local_path": "/work/myproj/other/deploy.md"
    }
    ref2 = format_project_skill_reference(skill2, "Gemini CLI")
    assert ref2 == "@deploy.md"

def test_looks_like_explicit_reference():
    assert _looks_like_explicit_reference("@test") is True
    assert _looks_like_explicit_reference("[link](path)") is True
    assert _looks_like_explicit_reference("./relative") is True
    assert _looks_like_explicit_reference("file.md") is True
    assert _looks_like_explicit_reference("path/file") is True
    assert _looks_like_explicit_reference("C:\\path") is True
    assert _looks_like_explicit_reference("type:name") is True
    assert _looks_like_explicit_reference("plain") is False

def test_project_root_for_target_markers(temp_dir):
    assert _project_root_for_target(temp_dir / "p" / ".codex" / "skills").name == "p"
    assert _project_root_for_target(temp_dir / "p" / ".gemini" / "skills").name == "p"

def test_classification_text():
    data = {
        "description": "Desc",
        "metadata": {"tags": ["t1", "t2"], "use_cases": "U"}
    }
    text = _classification_text(data)
    assert "Desc" in text
    assert "t1" in text
    assert "U" in text

def test_resolve_resilient_path_plural(temp_dir):
    agents_dir = temp_dir / ".agents"
    agents_dir.mkdir()
    
    # Try resolving .agent when only .agents exists
    res = _resolve_resilient_path(temp_dir / ".agent")
    assert res.name == ".agents"

def test_resolve_resilient_path_nested(temp_dir):
    agent_dir = temp_dir / ".agent" / "skills"
    agent_dir.mkdir(parents=True)
    
    # Try resolving path with .agents in it
    res = _resolve_resilient_path(str(temp_dir / ".agents" / "skills"))
    assert ".agent" in str(res)
    assert ".agents" not in str(res)

def test_project_label_cleaning():
    path = Path("/work/my-project/.agents/skills")
    assert project_label(path) == "my-project"
    
    # .agents is at index 4, so root is /work/my-project/subdir
    path2 = Path("/work/my-project/subdir/.agents/skills")
    assert project_label(path2) == "subdir"

def test_format_project_skill_reference_antigravity():
    skill = {
        "name": "TestSkill",
        "local_path": "/path/to/test-skill"
    }
    ref = format_project_skill_reference(skill, "Antigravity")
    assert ref == "/skill:TestSkill"

def test_format_project_skill_reference_command():
    skill = {
        "name": "MyCommand",
        "is_command": True,
        "project_root": "/root",
        "local_path": "/root/manuals/cmd.md"
    }
    ref = format_project_skill_reference(skill, "Antigravity")
    assert ref == "/skill:MyCommand"
    
    ref_gemini = format_project_skill_reference(skill, "Gemini CLI")
    assert ref_gemini == "@manuals/cmd.md"

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
