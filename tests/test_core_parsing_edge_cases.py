from unittest.mock import patch

from skill_manager.core.parsing import (
    categorize_skill,
    extract_markdown_description,
    normalize_description,
)


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


def test_categorize_skill_rapidfuzz_fallback():
    """Cover the fallback path when rapidfuzz is unavailable."""
    with patch.dict("sys.modules", {"rapidfuzz": None}):
        cat = categorize_skill("docker", "container deployment")
        assert cat["sub_category"] == "Cloud Infrastructure"

        cat = categorize_skill("zyxwvut", "completely unrelated gibberish text")
        assert cat["sub_category"] == "Uncategorized"


def test_categorize_skill_metadata_exact_match():
    cat = categorize_skill("anything", "desc", {"category": "testing"})
    assert cat["sub_category"] == "Testing"


def test_get_category_patterns_caching():
    from skill_manager.core.parsing.categorizer import _get_category_patterns

    patterns = _get_category_patterns()
    assert "Testing" in patterns or "Web Development" in patterns
    patterns2 = _get_category_patterns()
    assert patterns2 is patterns


def test_categorize_skill_cat_desc_score_boost():
    """Name doesn't match but description closely matches category name."""
    cat = categorize_skill("my helper", "web development framework")
    assert cat["sub_category"] in ("Web Development",)
