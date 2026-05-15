import pytest
from skill_manager.core.models import SkillModel

@pytest.fixture
def model():
    m = SkillModel()
    m.setSkills([
        {"name": "A1", "category": "Arch", "local_path": "/a1"},
        {"name": "A2", "category": "Arch", "local_path": "/a2"},
        {"name": "W1", "category": "Work", "local_path": "/w1"},
    ])
    return m

def test_select_all(model):
    model.selectAll()
    assert model.selectedCount == 3

def test_clear_selection(model):
    model.selectAll()
    model.clearSelection()
    assert model.selectedCount == 0

def test_category_selection_logic(model):
    # This imitates the "toggle category selection" logic
    # In the new model, we can filter by category and then select all
    model.categoryFilter = "Arch"
    for i in range(model.rowCount()):
        model.setSelected(i, True)
    
    # Check if only Arch skills are selected in the full list
    selected_paths = model.getSelectedPaths()
    assert len(selected_paths) == 2
    assert "/a1" in selected_paths
    assert "/a2" in selected_paths
    assert "/w1" not in selected_paths

def test_model_reset_preserves_selection(model):
    model.setSelected(0, True)
    # Re-apply skills (simulating a refresh)
    skills = [
        {"name": "A1", "category": "Arch", "local_path": "/a1"},
        {"name": "A2", "category": "Arch", "local_path": "/a2"},
    ]
    # Note: setSkills preserves selection by path.
    model.setSkills(skills)
    assert model.selectedCount == 1
