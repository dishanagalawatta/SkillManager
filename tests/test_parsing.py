from skill_manager.core.parsing import (
    build_skill_search_text,
    categorize_skill,
    extract_markdown_description,
    normalize_description,
    parse_command_md,
    parse_frontmatter,
    parse_skill_md,
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
    skill_file.write_text(
        """---
name: Alpha
description: Test skill alpha
type: bundle
---
# Alpha Skill
This is the body.
""",
        encoding="utf-8",
    )

    data = parse_skill_md(str(skill_file))
    assert data["name"] == "Alpha"
    assert data["description"] == "Test skill alpha"
    assert data["is_bundle"] is True
    assert "This is the body." in data["body_content"]


def test_parse_command_md(temp_dir):
    cmd_file = temp_dir / "DEPLOY.Codex.md"
    cmd_file.write_text(
        """---
name: Deploy
description: Deploy command
---
# Deploy
Body here.
""",
        encoding="utf-8",
    )

    data = parse_command_md(str(cmd_file))
    assert data["name"] == "Deploy"
    assert data["client"] == "Codex"
    assert data["description"] == "Deploy command"


def test_parse_frontmatter_malformed():
    # Invalid YAML that yaml.safe_load might still parse as a partial dict or string
    fm = "name: : invalid : yaml"
    parsed = parse_frontmatter(fm)
    assert parsed == {"name": ": invalid : yaml"}


def test_parse_frontmatter_empty():
    assert parse_frontmatter("") == {}
    assert parse_frontmatter(None) == {}


def test_parse_skill_md_missing():
    data = parse_skill_md("/non/existent/path")
    assert data["name"] == ""
    assert data["raw_content"] == ""


def test_parse_skill_md_no_frontmatter(temp_dir):
    skill_file = temp_dir / "SKILL.md"
    skill_file.write_text("# Only Header\nNo frontmatter here.")
    data = parse_skill_md(str(skill_file))
    assert data["name"] == ""
    assert data["body_content"].strip() == "# Only Header\nNo frontmatter here."


def test_categorize_skill_more_keywords():
    assert categorize_skill("docker", "")["sub_category"] == "Cloud Infrastructure"
    assert categorize_skill("python script", "")["sub_category"] == "Programming Languages"
    assert categorize_skill("react component", "")["sub_category"] == "Web Development"
    assert categorize_skill("security audit", "")["sub_category"] == "Security"
    assert categorize_skill("sql query", "")["sub_category"] == "Databases"
    assert categorize_skill("unit testing", "")["sub_category"] == "Testing"


def test_build_skill_search_text_missing_fields():
    # It adds spaces between default empty parts
    assert build_skill_search_text({}).strip() == ""
    assert build_skill_search_text({"name": "Test"}).strip() == "test"
