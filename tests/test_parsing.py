import pytest
from pathlib import Path
from skill_manager.core.parsing import (
    parse_skill_md,
    parse_command_md,
    parse_frontmatter,
    normalize_description,
    extract_markdown_description,
    categorize_skill,
    build_skill_search_text
)

def test_parse_frontmatter_standard():
    fm = "name: Test Skill\ndescription: A test description\ncategory: Development"
    parsed = parse_frontmatter(fm)
    assert parsed["name"] == "Test Skill"
    assert parsed["description"] == "A test description"
    assert parsed["category"] == "Development"

def test_parse_frontmatter_multiline():
    fm = "description: >\n  Line 1\n  Line 2\ncategory: Test"
    parsed = parse_frontmatter(fm)
    assert parsed["description"].strip() == "Line 1 Line 2"
    assert parsed["category"] == "Test"

def test_normalize_description():
    assert normalize_description("  Too   many   spaces  ") == "Too many spaces"
    assert normalize_description(["part1", "part2"]) == "part1 part2"
    assert normalize_description(None) == ""

def test_extract_markdown_description():
    content = """---
name: Ignore me
---
# Header
First paragraph.

Second paragraph.
"""
    desc = extract_markdown_description(content)
    assert desc == "First paragraph."

def test_parse_skill_md(temp_dir):
    skill_file = temp_dir / "SKILL.md"
    skill_file.write_text("""---
name: Alpha
description: Test skill alpha
type: bundle
---
# Alpha Skill
This is the body.
""", encoding="utf-8")
    
    data = parse_skill_md(str(skill_file))
    assert data["name"] == "Alpha"
    assert data["description"] == "Test skill alpha"
    assert data["is_bundle"] is True
    assert "This is the body." in data["body_content"]

def test_parse_command_md(temp_dir):
    cmd_file = temp_dir / "DEPLOY.Codex.md"
    cmd_file.write_text("""---
name: Deploy
description: Deploy command
---
# Deploy
Body here.
""", encoding="utf-8")
    
    data = parse_command_md(str(cmd_file))
    assert data["name"] == "Deploy"
    assert data["client"] == "Codex"
    assert data["description"] == "Deploy command"

def test_categorize_skill():
    assert categorize_skill("brainstorming", "creative work") == "Core Workflow"
    assert categorize_skill("git commit", "source control") == "Developer Tools"
    assert categorize_skill("react component", "ui development") == "Web Development"
    assert categorize_skill("unknown", "nothing") == "Uncategorized"

def test_build_skill_search_text():
    skill_data = {
        "name": "Alpha",
        "description": "Desc",
        "category": "Cat",
        "metadata": {"version": "1.0.0"}
    }
    search_text = build_skill_search_text(skill_data)
    assert "alpha" in search_text
    assert "desc" in search_text
    assert "cat" in search_text
    assert "1.0.0" in search_text
