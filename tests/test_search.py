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


def test_search_none_tags_in_metadata():
    """Test that skills with None tags in metadata don't crash the indexer."""
    skill_with_none_tags = {
        "name": "none_tagged",
        "description": "has None tags in metadata",
        "category": "test",
        "metadata": {"tags": None},
        "local_path": "/none_tagged",
    }
    skill_with_empty_metadata = {
        "name": "empty_meta",
        "description": "has empty metadata",
        "category": "test",
        "metadata": {},
        "local_path": "/empty_meta",
    }
    skill_with_no_metadata = {
        "name": "no_meta",
        "description": "has no metadata key",
        "category": "test",
        "local_path": "/no_meta",
    }
    skill_with_tags_at_top_level = {
        "name": "top_level_tags",
        "description": "tags at top level not in metadata",
        "category": "test",
        "tags": ["important", "urgent"],
        "metadata": {},
        "local_path": "/top_level_tags",
    }

    engine = SearchEngine(
        [
            skill_with_none_tags,
            skill_with_empty_metadata,
            skill_with_no_metadata,
            skill_with_tags_at_top_level,
        ]
    )

    results = engine.query("none_tagged")
    assert len(results) == 1
    assert results[0][0]["name"] == "none_tagged"

    results = engine.query("important")
    assert len(results) == 1
    assert results[0][0]["name"] == "top_level_tags"


def test_search_exact_token_fast_path_invariants(sample_skills):
    """Lock the existing substring-based fast path.

    The search scoring short-circuits fuzz.ratio when a query token is a
    substring of the document's full_text. This guards against a regression
    that would force every query through the expensive fuzzy loop, and confirms
    exact-token queries still rank the right skill at the top.
    """
    engine = SearchEngine(sample_skills)

    # "brainstorm" is a substring of "brainstorming" -> fast path should fire
    # and return brainstorming as the sole, top-ranked result.
    results = engine.query("brainstorm")
    assert [r[0]["name"] for r in results] == ["brainstorming"]
    assert results[0][1] >= 65  # passed the token-match gate

    # A query with no substring overlap must hide all skills (score 0 gate).
    results = engine.query("zzzzz_nonexistent")
    assert results == []


def test_search_fast_path_matches_fuzzy_only_path(sample_skills):
    """Fast path and fuzzy-only path must agree on relevance.

    A correct fast path must never change *which* skills are returned compared
    to the slower fuzzy-only computation. We compare results with the fast path
    enabled (default) against a forced fuzzy-only evaluation.
    """
    engine = SearchEngine(sample_skills)

    # Force the fuzzy-only slow path by making full_text empty so the substring
    # fast path can never match, while all_doc_tokens remain populated.
    for _, idx in engine._indexed_data:
        idx["full_text"] = ""

    for query in ("brainstorm", "python", "test", "git", "design"):
        fuzzy_only = [r[0]["name"] for r in engine.query(query)]
        # Rebuild with pristine index data for the fast-path comparison.
        engine2 = SearchEngine(sample_skills)
        fast_path = [r[0]["name"] for r in engine2.query(query)]
        assert fast_path == fuzzy_only, (
            f"Fast path disagrees with fuzzy-only path for {query!r}: {fast_path} != {fuzzy_only}"
        )
