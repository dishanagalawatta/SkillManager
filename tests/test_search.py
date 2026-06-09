from unittest.mock import patch

import pytest

from skill_manager.core.search import SearchEngine


@pytest.fixture
def sample_skills():
    return [
        {
            "name": "brainstorming",
            "description": "Use before creative or constructive work. Transforms vague ideas into validated designs.",
            "category": "design",
            "metadata": {"tags": ["planning", "design"]},
        },
        {
            "name": "auto_commit",
            "description": "Automate git commits and push to remote.",
            "category": "git",
            "metadata": {"tags": ["automation", "vcs"]},
        },
        {
            "name": "python_test",
            "description": "Test python code using pytest.",
            "category": "testing",
            "metadata": {"tags": ["python", "pytest"]},
        },
    ]


def test_search_hides_irrelevant_skills(sample_skills):
    engine = SearchEngine(sample_skills)

    # Query 'brainstorm' should only return brainstorming
    results = engine.query("brainstorm")
    result_names = [r[0]["name"] for r in results]
    assert result_names == ["brainstorming"], f"Expected ['brainstorming'], got {result_names}"

    # Query 'python' should only return python_test
    results = engine.query("python")
    result_names = [r[0]["name"] for r in results]
    assert result_names == ["python_test"], f"Expected ['python_test'], got {result_names}"

    # Query 'test' should only return python_test
    results = engine.query("test")
    result_names = [r[0]["name"] for r in results]
    assert result_names == ["python_test"], f"Expected ['python_test'], got {result_names}"


def test_search_empty_query_valid_paths_filter(sample_skills):
    engine = SearchEngine(sample_skills)
    results_all = engine.query("")
    assert len(results_all) == 3

    skills_with_paths = [dict(s, local_path=f"/p{i}") for i, s in enumerate(sample_skills)]
    engine2 = SearchEngine(skills_with_paths)
    valid = {"/p0", "/p1"}
    results = engine2.query("", valid_paths=valid)
    assert len(results) == 2


def test_search_remove_from_index(sample_skills):
    engine = SearchEngine(sample_skills)
    engine.remove_from_index([sample_skills[0]["name"]])
    results = engine.query("")
    assert len(results) == 2


def test_search_skill_no_path(sample_skills):
    engine = SearchEngine(sample_skills)
    engine.update_index([{}])
    results = engine.query("")
    assert len(results) == 3


def test_search_fuzz_fallback_scoring(sample_skills):
    """Cover the fuzz=None fallback path."""
    engine = SearchEngine(sample_skills)
    with patch("skill_manager.core.search.fuzz", None):
        results = engine.query("brainstorming")
        assert len(results) == 1

        results = engine.query("zzzzz_not_found")
        assert len(results) == 0


def test_search_string_tags(sample_skills):
    skill = {
        "name": "tagged",
        "description": "has string tags",
        "category": "test",
        "metadata": {"tags": "alpha,beta"},
        "local_path": "/tagged",
    }
    engine = SearchEngine([skill])
    result = engine.query("alpha")
    assert len(result) == 1
