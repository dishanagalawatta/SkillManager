from skill_manager.core.parsing import (
    categorize_skill,
    extract_markdown_description,
    normalize_description,
    parse_frontmatter,
)


def test_parse_frontmatter_complex_yaml():
    fm = """
name: "Complex Name"
tags: [tag1, tag2, tag3]
description: |
  Line 1
  Line 2
nested:
  key: value
"""
    parsed = parse_frontmatter(fm)
    assert parsed["name"] == "Complex Name"
    assert parsed["tags"] == ["tag1", "tag2", "tag3"]
    assert "Line 1" in parsed["description"]
    assert parsed["nested"]["key"] == "value"

def test_parse_frontmatter_malformed():
    fm = "this is not yaml : :::"
    parsed = parse_frontmatter(fm)
    assert isinstance(parsed, dict)
    # Should not crash, might be empty or partial

def test_normalize_description_types():
    assert normalize_description(None) == ""
    assert normalize_description(["a", "b"]) == "a b"
    assert normalize_description(123) == "123"
    assert normalize_description("  extra   spaces  ") == "extra spaces"

def test_extract_markdown_description_no_fm():
    content = """
# Title
First paragraph.

Second paragraph.
"""
    desc = extract_markdown_description(content)
    assert desc == "First paragraph."

def test_extract_markdown_description_with_fm():
    content = """---
name: Test
---
# Header
Actual description here.
"""
    desc = extract_markdown_description(content)
    assert desc == "Actual description here."

def test_categorize_skill_weighting():
    # Test that name has higher signal. Use a keyword that doesn't collide with "Tool"
    name = "Security Hack"
    desc = "A generic utility for developers"
    cat = categorize_skill(name, desc)
    assert cat["sub_category"] == "Security"

    # Test that keyword in description still works
    name = "Helper"
    desc = "This is a system deployment"
    cat = categorize_skill(name, desc)
    assert cat["sub_category"] == "DevOps"

def test_categorize_skill_uncategorized():
    cat = categorize_skill("XYZ", "abc def")
    assert cat["sub_category"] == "Uncategorized"
    assert cat["main_category"] == "⚙️ System & Workflow"
