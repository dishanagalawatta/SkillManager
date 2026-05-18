from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt

from skill_manager.core.models import SkillModel


@pytest.fixture
def skill_list():
    return [
        {
            "name": "Skill A",
            "category": "Dev",
            "local_path": "/a",
            "is_selected": False,
            "is_archived": False,
        },
        {
            "name": "Skill B",
            "category": "Core",
            "local_path": "/b",
            "is_selected": False,
            "is_archived": False,
        },
        {
            "name": "Skill C",
            "category": "Dev",
            "local_path": "/c",
            "is_selected": False,
            "is_archived": True,
        },
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
    assert model.data(index, SkillModel.NameRole) == "Skill B"  # Sorted by category Core then Dev
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
    assert model.rowCount() == 1  # Only A (C is archived)
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


def test_skill_model_project_filter(qapp, skill_list):
    # Add project label to one
    skill_list[0]["project_label"] = "Project X"
    model = SkillModel()
    model.setSkills(skill_list)
    model.projectFilter = "Project X"
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill A"


def test_skill_model_collection_filter(qapp, skill_list):
    # collectionFilter shows ONLY bundles
    skill_list[0]["is_bundle"] = True
    model = SkillModel()
    model.setSkills(skill_list)
    model.collectionFilter = True
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill A"


def test_skill_model_starred_filter(qapp, skill_list):
    # showStarred property controls show_starred.
    # If False, it HIDES starred skills.
    skill_list[0]["is_starred"] = True
    model = SkillModel()
    model.setSkills(skill_list)

    # Default is show_starred = True, so both A and B are shown
    assert model.rowCount() == 2

    model.showStarred = False
    # Now Skill A is hidden
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill B"


def test_skill_model_invalid_index(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    assert model.data(model.index(-1, -1), SkillModel.NameRole) is None
    assert model.data(model.index(100, 100), SkillModel.NameRole) is None


def test_skill_model_show_archived_setter(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    assert model.rowCount() == 2
    model.showArchived = True
    assert model.rowCount() == 3
    model.showArchived = True  # No change
    assert model.rowCount() == 3


def test_skill_model_is_package_only(qapp, skill_list):
    # Set up some package and project skills
    skill_list[0]["is_package"] = True
    skill_list[1]["is_package"] = False

    model = SkillModel()
    model.setSkills(skill_list)

    # Check initial state (default None/PartiallyChecked)
    assert model.isPackageOnly == Qt.PartiallyChecked

    # Filter to Packages
    model.isPackageOnly = Qt.Checked
    assert model.isPackageOnly == Qt.Checked
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill A"

    # Filter to Projects
    model.isPackageOnly = Qt.Unchecked
    assert model.isPackageOnly == Qt.Unchecked
    # In Quick Copy mode (isPackageOnly=False), only project skills are shown.
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill B"


def test_skill_model_project_mode_never_leaks_starred_packages(qapp):
    model = SkillModel()
    model.setSkills(
        [
            {
                "name": "Package Star",
                "local_path": "/pkg/star",
                "is_package": True,
                "is_starred": True,
                "project_label": "Master Library",
                "category": "Dev",
            },
            {
                "name": "Project Star",
                "local_path": "/proj/star",
                "is_package": False,
                "is_starred": True,
                "project_label": "Project A",
                "category": "Dev",
            },
            {
                "name": "Project Other",
                "local_path": "/proj/other",
                "is_package": False,
                "project_label": "Project A",
                "category": "Ops",
            },
        ]
    )

    model.isPackageOnly = Qt.Unchecked
    model.projectFilter = "Project A"
    assert [model.data(model.index(i, 0), SkillModel.NameRole) for i in range(model.rowCount())] == [
        "Project Star",
        "Project Other",
    ]

    model.categoryFilter = "Ops"
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Project Other"


def test_skill_model_data_various_roles(qapp, skill_list):
    skill_list[0].update(
        {
            "description": "Desc A",
            "is_starred": True,
            "is_bundle": True,
            "raw_content": "Raw",
            "body_content": "Body",
            "risk": "High",
            "source": "Github",
            "date": "2023",
            "client": "Codex",
        }
    )
    model = SkillModel()
    model.setSkills(skill_list)
    idx = model.index(0, 0)

    assert model.data(idx, SkillModel.DescriptionRole) == "Desc A"
    assert model.data(idx, SkillModel.IsStarredRole) is True
    assert model.data(idx, SkillModel.IsCollectionRole) is True
    assert model.data(idx, SkillModel.SectionRole) == "Special|Starred"
    assert model.data(idx, SkillModel.RawContentRole) == "Raw"
    assert model.data(idx, SkillModel.BodyContentRole) == "Body"
    assert model.data(idx, SkillModel.RiskRole) == "High"
    assert model.data(idx, SkillModel.SourceRole) == "Github"
    assert model.data(idx, SkillModel.DateRole) == "2023"
    assert model.data(idx, SkillModel.ClientRole) == "Codex"
    assert model.data(idx, SkillModel.IsCollapsedRole) is False


def test_skill_model_show_commands_setter(qapp, skill_list):
    skill_list[0]["is_command"] = True
    model = SkillModel()
    model.setSkills(skill_list)
    assert model.rowCount() == 2  # Skill A is command, but showCommands=True by default
    model.showCommands = False
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill B"


def test_skill_model_select_all(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.selectAll()
    assert model.selectedCount == 2
    assert "/a" in model.getSelectedPaths()
    assert "/b" in model.getSelectedPaths()


def test_skill_model_select_by_paths(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.selectByPaths(["/a", "/non-existent"])
    assert model.selectedCount == 1
    assert "/a" in model.getSelectedPaths()


def test_skill_model_search_engine_integration(qapp, skill_list):
    mock_search = MagicMock()
    # query returns list of (skill_dict, score)
    mock_search.query.return_value = [(skill_list[1], 1.0)]

    model = SkillModel()
    model.setSkills(skill_list)
    model._search_engine = mock_search  # Set private member for testing

    model.filterText = "skill b"
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill B"
    mock_search.query.assert_called_with("skill b", valid_paths={"/a", "/b"})


def test_skill_model_set_skills_updates(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)

    new_skills = [{"name": "New", "local_path": "/new"}]
    model.setSkills(new_skills)
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "New"


def test_skill_model_with_config(qapp):
    config = {"show_archived": True, "category_filter": "Dev", "show_commands": False}
    model = SkillModel(config=config)
    assert model.showArchived is True
    assert model.categoryFilter == "Dev"
    assert model.showCommands is False


def test_skill_model_get_skill_at(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    assert model.get_skill_at(0)["name"] == "Skill B"
    assert model.get_skill_at(-1) == {}
    assert model.get_skill_at(100) == {}


def test_skill_model_set_selected(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    model.setSelected(0, True)
    assert model.selectedCount == 1
    model.setSelected(0, False)
    assert model.selectedCount == 0


def test_skill_model_expansion_logic(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)

    # Section expansion (default all expanded)
    assert model.isAllExpanded is True
    assert model.isCategoryCollapsed("⚙️ System & Workflow|Core") is False

    # Collapse section
    model.toggleCategory("⚙️ System & Workflow|Core")
    assert model.isCategoryCollapsed("⚙️ System & Workflow|Core") is True
    assert model.isAllExpanded is False
    assert model.data(model.index(0, 0), SkillModel.IsCollapsedRole) is True

    # Expand section
    model.expandAll()
    assert model.isCategoryCollapsed("⚙️ System & Workflow|Core") is False
    assert model.isAllExpanded is True

    # Collapse all
    model.collapseAll()
    assert model.isCategoryCollapsed("⚙️ System & Workflow") is True
    assert model.isAllExpanded is False

    # Toggle all (expands since it's currently collapsed)
    model.toggleAll()
    assert model.isAllExpanded is True


def test_skill_model_collapsed_main_category_keeps_only_header_sentinel(qapp):
    model = SkillModel()
    model.setSkills(
        [
            {"name": "A1", "category": "Dev", "local_path": "/a1"},
            {"name": "A2", "category": "Dev", "local_path": "/a2"},
            {"name": "B1", "category": "Ops", "local_path": "/b1"},
        ]
    )

    assert model.rowCount() == 3
    model.toggleCategory("⚙️ System & Workflow")

    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.IsMainCollapsedRole) is True
    assert model.data(model.index(0, 0), SkillModel.IsFirstInSubcategoryRole) is True


def test_skill_model_collapsed_subcategory_keeps_one_subheader_row(qapp):
    model = SkillModel()
    model.setSkills(
        [
            {"name": "A1", "category": "Dev", "local_path": "/a1"},
            {"name": "A2", "category": "Dev", "local_path": "/a2"},
            {"name": "B1", "category": "Ops", "local_path": "/b1"},
        ]
    )

    model.toggleCategory("Dev")

    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "A1"
    assert model.data(model.index(0, 0), SkillModel.IsSubCollapsedRole) is True
    assert model.data(model.index(1, 0), SkillModel.NameRole) == "B1"


def test_skill_model_selection_survives_collapsed_visibility_changes(qapp):
    model = SkillModel()
    model.setSkills(
        [
            {"name": "A1", "category": "Dev", "local_path": "/a1"},
            {"name": "A2", "category": "Dev", "local_path": "/a2"},
            {"name": "B1", "category": "Ops", "local_path": "/b1"},
        ]
    )

    model.selectByPaths(["/a1", "/a2"])
    assert model.selectedCount == 2
    model.toggleCategory("Dev")

    assert model.selectedCount == 2
    assert set(model.getSelectedPaths()) == {"/a1", "/a2"}


def test_skill_model_setters_and_getters(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)

    # Category filter
    model.categoryFilter = "Dev"
    assert model.categoryFilter == "Dev"

    # Collection filter
    model.collectionFilter = True
    assert model.collectionFilter is True

    # Project filter
    model.projectFilter = "Proj"
    assert model.projectFilter == "Proj"

    # Client filter
    model.clientFilter = "Codex"
    assert model.clientFilter == "Codex"


def test_skill_model_collapse_special_sections(qapp):
    skills = [
        {"name": "E", "is_starred": True, "local_path": "/e"},
        {"name": "C", "is_bundle": True, "local_path": "/c"},
        {"name": "G", "local_path": "/g"},  # General
    ]
    model = SkillModel()
    model.setSkills(skills)

    model.collapseAll()
    assert model.isCategoryCollapsed("Special") is True
    assert model.isCategoryCollapsed("⚙️ System & Workflow") is True


def test_skill_model_toggle_selection_edge(qapp, skill_list):
    model = SkillModel()
    model.setSkills([{"name": "No Path"}])  # missing local_path
    model.toggleSelection(0)
    assert model.selectedCount == 0


def test_skill_model_search_no_skills(qapp):
    model = SkillModel()
    model.setSkills([])
    model.filterText = "test"
    assert model.rowCount() == 0


def test_skill_model_save_methods_with_mock_config(qapp, skill_list):
    mock_conf = MagicMock()
    model = SkillModel(config=mock_conf)
    model.setSkills(skill_list)

    model.toggleCategory("Dev")
    mock_conf.set.assert_any_call("collapsed_categories", ["Dev"])

    model.showArchived = True
    mock_conf.set.assert_any_call("show_archived", True)


def test_skill_model_role_names(qapp):
    model = SkillModel()
    roles = model.roleNames()
    assert b"name" in roles.values()
    assert b"category" in roles.values()
    assert b"sectionName" in roles.values()
    assert b"isCollapsed" in roles.values()
