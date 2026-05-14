import pytest
from PySide6.QtCore import Qt
from skill_manager.core.models import SkillModel

@pytest.fixture
def skill_list():
    return [
        {"name": "Skill A", "category": "Dev", "local_path": "/a", "is_selected": False, "is_archived": False},
        {"name": "Skill B", "category": "Core", "local_path": "/b", "is_selected": False, "is_archived": False},
        {"name": "Skill C", "category": "Dev", "local_path": "/c", "is_selected": False, "is_archived": True},
    ]

def test_skill_model_row_count(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    # Default: showArchived=False, so only A and B
    assert model.rowCount() == 2

def test_skill_model_data_roles(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    index = model.index(0, 0)
    assert model.data(index, SkillModel.NameRole) == "Skill B" # Sorted by category Core then Dev
    assert model.data(index, SkillModel.CategoryRole) == "Core"

def test_skill_model_show_archived(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.showArchived = True
    assert model.rowCount() == 3

def test_skill_model_category_filter(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.categoryFilter = "Dev"
    assert model.rowCount() == 1 # Only A (C is archived)
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill A"

def test_skill_model_selection(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.toggleSelection(0)
    assert model.selectedCount == 1
    assert model.data(model.index(0, 0), SkillModel.IsSelectedRole) is True

def test_skill_model_clear_selection(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.toggleSelection(0)
    model.clearSelection()
    assert model.selectedCount == 0

def test_skill_model_search_filter(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.filterText = "skill b"
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill B"
