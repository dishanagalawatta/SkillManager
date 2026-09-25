import pytest

from skill_manager.core.models import FilterEngine, FilterState, Skill


@pytest.fixture
def engine():
    return FilterEngine()


@pytest.fixture
def skill_data():
    return {
        "name": "Test Skill",
        "category": "Core Workflow",
        "description": "A test skill",
        "local_path": "/path/to/skill",
        "is_starred": False,
        "is_archived": False,
        "is_bundle": False,
        "is_command": False,
        "main_category": "⚙️ System & Workflow",
    }


def test_skill_from_dict(skill_data):
    skill = Skill.from_dict(skill_data)
    assert skill.name == "Test Skill"
    assert skill.category == "Core Workflow"
    assert skill.main_category == "⚙️ System & Workflow"


def test_skill_getitem_missing_key():
    skill = Skill()
    with pytest.raises(KeyError):
        _ = skill["nonexistent"]


def test_skill_setitem_missing_key():
    skill = Skill()
    with pytest.raises(KeyError):
        skill["nonexistent"] = "value"


def test_skill_contains():
    skill = Skill(name="test")
    assert "name" in skill
    assert "nonexistent" not in skill


def test_skill_get_default():
    skill = Skill(name="test")
    assert skill.get("name") == "test"
    assert skill.get("nonexistent", "fallback") == "fallback"


def test_filter_engine_get_main_category(engine, skill_data):
    skill = Skill.from_dict(skill_data)
    assert engine.get_main_category(skill) == "⚙️ System & Workflow"

    skill.is_starred = True
    assert engine.get_main_category(skill) == "Special"


def test_filter_engine_filter_by_category(engine):
    skills = [
        Skill.from_dict({"name": "S1", "category": "A", "local_path": "p1"}),
        Skill.from_dict({"name": "S2", "category": "B", "local_path": "p2"}),
    ]
    state = FilterState(category_filter="A")
    filtered = engine.filter_skills(skills, state)

    assert len(filtered) == 1
    assert filtered[0].name == "S1"


def test_filter_engine_filter_archived(engine):
    skills = [
        Skill.from_dict({"name": "S1", "is_archived": False, "local_path": "p1"}),
        Skill.from_dict({"name": "S2", "is_archived": True, "local_path": "p2"}),
    ]

    # Default: don't show archived
    state = FilterState(show_archived=False)
    assert len(engine.filter_skills(skills, state)) == 1

    # Show archived
    state.show_archived = True
    assert len(engine.filter_skills(skills, state)) == 2


def test_filter_engine_sort_key(engine):
    s1 = Skill.from_dict(
        {"name": "Apple", "main_category": "⚙️ System & Workflow", "local_path": "p1"}
    )
    s2 = Skill.from_dict(
        {"name": "Zebra", "main_category": "⚙️ System & Workflow", "local_path": "p2"}
    )

    key1 = engine.sort_key(s1)
    key2 = engine.sort_key(s2)

    assert key1 < key2
    assert "1_⚙️ System & Workflow" in key1[0]


def test_filter_engine_build_visible_rows_collapsed(engine):
    skills = [
        Skill.from_dict({"name": "S1", "main_category": "Cat A", "local_path": "p1"}),
        Skill.from_dict({"name": "S2", "main_category": "Cat A", "local_path": "p2"}),
        Skill.from_dict({"name": "S3", "main_category": "Cat B", "local_path": "p3"}),
    ]
    # Prepare rows to set internal names
    engine.prepare_rows(skills)

    # Collapse Cat A
    collapsed = {"Cat A"}
    visible = engine.build_visible_rows(skills, collapsed)

    # Should show one entry for Cat A (representing the collapsed header) and S3
    assert len(visible) == 2
    assert visible[0].main_category_name == "Cat A"
    assert visible[1].name == "S3"


def test_diff_fallback_keys_mixed_int_str_match_all_str():
    """Mixed str/int diff keys must diff identically to all-str keys.

    Guards the pipeline optimization that uses ``s.local_path or id(s)``
    instead of ``s.local_path if s.local_path else str(id(s))``:
    ``difflib.SequenceMatcher`` compares by equality, and ``str`` never
    equals ``int``, so fallback ids can never collide with real paths.
    """
    import difflib

    old_list = [
        Skill(name="S1", local_path="/a"),
        Skill(name="S2", local_path=""),
        Skill(name="S3", local_path="/b"),
    ]
    new_list = [
        Skill(name="S1", local_path="/a"),
        Skill(name="S4", local_path=""),
        Skill(name="S3", local_path="/b"),
    ]

    str_keys = (
        [s.local_path if s.local_path else str(id(s)) for s in old_list],
        [s.local_path if s.local_path else str(id(s)) for s in new_list],
    )
    mixed_keys = (
        [s.local_path or id(s) for s in old_list],
        [s.local_path or id(s) for s in new_list],
    )

    old_opcodes = difflib.SequenceMatcher(None, *str_keys).get_opcodes()
    new_opcodes = difflib.SequenceMatcher(None, *mixed_keys).get_opcodes()
    assert [tag for tag, *_ in old_opcodes] == [tag for tag, *_ in new_opcodes]
    # Distinct objects without paths never match each other in either scheme.
    assert ("equal", 1, 2, 1, 2) not in [
        (tag, i1, i2, j1, j2) for tag, i1, i2, j1, j2 in new_opcodes
    ]
