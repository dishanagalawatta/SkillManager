import pytest
from skill_manager.core.search import SearchEngine, SkillIndexer

@pytest.fixture
def skills():
    return [
        {"name": "Brainstorming", "description": "Creative work features", "category": "Core"},
        {"name": "Git Commit", "description": "Source control tool", "category": "DevTools", "metadata": {"tags": ["git", "vc"]}},
        {"name": "React UI", "description": "Frontend components", "category": "Web"},
    ]

def test_indexer_tokens():
    indexer = SkillIndexer()
    tokens = indexer.tokenize("Hello World, testing 123!")
    assert "hello" in tokens
    assert "world" in tokens
    assert "testing" in tokens
    assert "123" in tokens # \w+ matches digits too

def test_search_exact_name(skills):
    engine = SearchEngine(skills)
    results = engine.query("Brainstorming")
    assert len(results) >= 1
    assert results[0][0]["name"] == "Brainstorming"
    assert results[0][1] >= 90.0

def test_search_fuzzy_name(skills):
    engine = SearchEngine(skills)
    results = engine.query("brainstorm")
    assert len(results) >= 1
    assert results[0][0]["name"] == "Brainstorming"

def test_search_category(skills):
    engine = SearchEngine(skills)
    results = engine.query("Web")
    assert any(r[0]["name"] == "React UI" for r in results)

def test_search_tags(skills):
    engine = SearchEngine(skills)
    results = engine.query("vc")
    assert results[0][0]["name"] == "Git Commit"

def test_search_empty_query(skills):
    engine = SearchEngine(skills)
    results = engine.query("")
    assert len(results) == 3
    assert all(r[1] == 100.0 for r in results)

def test_search_no_match(skills):
    engine = SearchEngine(skills)
    results = engine.query("nonexistent")
    assert len(results) == 0
