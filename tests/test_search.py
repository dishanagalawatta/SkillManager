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
