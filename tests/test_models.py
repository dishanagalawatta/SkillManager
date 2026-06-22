from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QModelIndex, Qt

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
    assert model.data(index, SkillModel.PathRole) == "/b"
    assert model.data(index, SkillModel.IsStarredRole) is False
    assert model.data(index, SkillModel.IsSelectedRole) is False
    assert model.data(index, SkillModel.IsArchivedRole) is False


def test_skill_model_data_invalid_index(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    assert model.data(model.index(10, 0), SkillModel.NameRole) is None
    assert model.data(QModelIndex(), SkillModel.NameRole) is None


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
    assert [
        model.data(model.index(i, 0), SkillModel.NameRole) for i in range(model.rowCount())
    ] == [
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
    assert model.data(idx, SkillModel.SectionRole) == "Special|Dev"
    assert model.data(idx, SkillModel.RawContentRole) == "Raw"
    assert model.data(idx, SkillModel.BodyContentRole) == "Body"
    assert model.data(idx, SkillModel.RiskRole) == "High"
    assert model.data(idx, SkillModel.SourceRole) == "Github"
    assert model.data(idx, SkillModel.DateRole) == "2023"
    assert model.data(idx, SkillModel.ClientRole) == "Codex"
    assert model.data(idx, SkillModel.IsCollapsedRole) is False


def test_skill_model_client_filter_migration(qapp):
    skills = [
        {
            "name": "Debug",
            "local_path": "/cmd/debug.clienta.md",
            "is_command": True,
            "client": "ClientA",
            "category": "Dev",
        },
        {
            "name": "Debug",
            "local_path": "/cmd/debug.clientb.md",
            "is_command": True,
            "client": "ClientB",
            "category": "Dev",
        },
        {
            "name": "Other",
            "local_path": "/cmd/other.md",
            "is_command": False,
            "category": "Dev",
        },
    ]
    model = SkillModel()
    model.setSkills(skills)
    model.filterByClient = True
    model.clientFilter = "ClientA"

    # Toggle selection by path to avoid row index confusion during filters
    model.selectByPaths(["/cmd/debug.clienta.md", "/cmd/other.md"])

    selected = set(model.getSelectedPaths())
    assert "/cmd/debug.clienta.md" in selected
    assert "/cmd/other.md" in selected

    # Change client
    model.clientFilter = "ClientB"

    selected = set(model.getSelectedPaths())
    assert "/cmd/debug.clientb.md" in selected
    assert "/cmd/other.md" in selected
    assert "/cmd/debug.clienta.md" not in selected


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

    model.toggleCategory("⚙️ System & Workflow|Dev")

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

    # toggleCategory uses a debounced timer; fire it immediately
    model.toggleCategory("⚙️ System & Workflow|Dev")
    if model._collapse_save_timer is not None:
        model._collapse_save_timer.timeout.emit()
    mock_conf.set.assert_any_call("collapsed_categories", ["⚙️ System & Workflow|Dev"])

    # showArchived uses _save_filters -> set_many
    model.showArchived = True
    mock_conf.set_many.assert_called_once()
    call_args = mock_conf.set_many.call_args[0][0]
    assert call_args["show_archived"] is True


def test_skill_model_role_names(qapp):
    model = SkillModel()
    roles = model.roleNames()
    assert b"name" in roles.values()
    assert b"category" in roles.values()
    assert b"sectionName" in roles.values()
    assert b"isCollapsed" in roles.values()
    assert b"subCategoryName" in roles.values()


def test_collapsible_starred_categories(qapp):
    # Setup some test skills:
    # 1. Starred skill in "Community" category
    # 2. Starred skill in "Planning" category
    # 3. Regular skill in "Community" category
    skills = [
        {
            "name": "Star Comm",
            "category": "Community",
            "is_starred": True,
            "local_path": "/star_comm",
        },
        {
            "name": "Star Plan",
            "category": "Planning",
            "is_starred": True,
            "local_path": "/star_plan",
        },
        {
            "name": "Reg Comm",
            "category": "Community",
            "is_starred": False,
            "local_path": "/reg_comm",
        },
    ]
    model = SkillModel()
    model.setSkills(skills)

    # 1. Test grouping and roles
    # We expect sort order:
    # Starred skills at the top grouped under "Special"
    # Row 0: Star Comm (Special|Community)
    # Row 1: Star Plan (Special|Planning)
    # Row 2: Reg Comm (⚙️ System & Workflow|Community)

    assert model.rowCount() == 3

    idx_star_comm = model.index(0, 0)
    idx_star_plan = model.index(1, 0)
    idx_reg_comm = model.index(2, 0)

    assert model.data(idx_star_comm, SkillModel.NameRole) == "Star Comm"
    assert model.data(idx_star_plan, SkillModel.NameRole) == "Star Plan"
    assert model.data(idx_reg_comm, SkillModel.NameRole) == "Reg Comm"

    # Test SubCategoryNameRole returns the original category name
    assert model.data(idx_star_comm, SkillModel.SubCategoryNameRole) == "Community"
    assert model.data(idx_star_plan, SkillModel.SubCategoryNameRole) == "Planning"
    assert model.data(idx_reg_comm, SkillModel.SubCategoryNameRole) == "Community"

    # Test SectionRole returns Special|<category> for starred skills
    assert model.data(idx_star_comm, SkillModel.SectionRole) == "Special|Community"
    assert model.data(idx_star_plan, SkillModel.SectionRole) == "Special|Planning"
    assert (
        model.data(idx_reg_comm, SkillModel.SectionRole) == "⚙️ System & Workflow|Community"
    )  # Default main category is "⚙️ System & Workflow"

    # 2. Test targeted collapsing behavior using section names
    # Collapse only "Special|Community"
    model.toggleCategory("Special|Community")
    assert model.isCategoryCollapsed("Special|Community") is True
    assert model.isCategoryCollapsed("Special|Planning") is False
    assert model.isCategoryCollapsed("⚙️ System & Workflow|Community") is False

    # Check isCollapsed roles
    assert model.data(idx_star_comm, SkillModel.IsCollapsedRole) is True
    assert model.data(idx_star_plan, SkillModel.IsCollapsedRole) is False
    assert model.data(idx_reg_comm, SkillModel.IsCollapsedRole) is False


def test_category_expansion_refactor(qapp):
    model = SkillModel()

    # 1. Test collapsedCategories property
    assert hasattr(model, "collapsedCategories")
    assert isinstance(model.collapsedCategories, list)

    # 2. Test name collisions in sub-category collapse state
    skills = [
        {"name": "Skill A", "main_category": "General", "category": "SubA", "local_path": "/a"},
        {"name": "Skill B", "main_category": "MainB", "category": "General", "local_path": "/b"},
    ]
    model.setSkills(skills)

    # Collapse main category "General"
    model.toggleCategory("General")

    assert model.isCategoryCollapsed("General") is True
    assert model.isCategoryCollapsed("MainB|General") is False

    # Prepare rows so internal names exist
    rows = model._all_filtered_skills

    # Skill A (in main category "General") is collapsed because its main category is collapsed.
    assert model._is_main_collapsed(rows[0]) is True
    # Skill B (in main category "MainB", subcategory "General") should NOT have its subcategory collapsed.
    assert model._is_sub_collapsed(rows[1]) is False


def test_skill_model_filtering_uses_layout_signals(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)

    # Listeners for model reset
    reset_about_to_be_called = False
    reset_called = False

    def on_about_to_reset():
        nonlocal reset_about_to_be_called
        reset_about_to_be_called = True

    def on_reset():
        nonlocal reset_called
        reset_called = True

    model.modelAboutToBeReset.connect(on_about_to_reset)
    model.modelReset.connect(on_reset)

    # Listeners for layout change
    layout_about_to_change_called = False
    layout_change_called = False

    def on_layout_about_to_change():
        nonlocal layout_about_to_change_called
        layout_about_to_change_called = True

    def on_layout_changed():
        nonlocal layout_change_called
        layout_change_called = True

    model.layoutAboutToBeChanged.connect(on_layout_about_to_change)
    model.layoutChanged.connect(on_layout_changed)

    # Trigger a filter change
    model.showArchived = True

    # Asserting that layout signals are emitted instead of model reset
    assert layout_about_to_change_called is True
    assert layout_change_called is True
    assert reset_about_to_be_called is False
    assert reset_called is False


def test_skill_model_rebuild_uses_layout_signals(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)

    # Listeners for model reset
    reset_about_to_be_called = False
    reset_called = False

    def on_about_to_reset():
        nonlocal reset_about_to_be_called
        reset_about_to_be_called = True

    def on_reset():
        nonlocal reset_called
        reset_called = True

    model.modelAboutToBeReset.connect(on_about_to_reset)
    model.modelReset.connect(on_reset)

    # Listeners for layout change
    layout_about_to_change_called = False
    layout_change_called = False

    def on_layout_about_to_change():
        nonlocal layout_about_to_change_called
        layout_about_to_change_called = True

    def on_layout_changed():
        nonlocal layout_change_called
        layout_change_called = True

    model.layoutAboutToBeChanged.connect(on_layout_about_to_change)
    model.layoutChanged.connect(on_layout_changed)

    # Trigger a rebuild by toggling category
    model.toggleCategory("⚙️ System & Workflow|Core")

    # Asserting that layout signals are emitted instead of model reset
    assert layout_about_to_change_called is True
    assert layout_change_called is True
    assert reset_about_to_be_called is False
    assert reset_called is False


def test_skill_model_invalid_data_role(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    idx = model.index(0)
    # Testing a non-existent role
    assert model.data(idx, Qt.UserRole + 999) is None
    # Testing an invalid index
    assert model.data(model.index(-1), Qt.DisplayRole) is None


def test_skill_model_flags(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    idx = model.index(0)
    flags = model.flags(idx)
    assert flags & Qt.ItemIsSelectable
    assert flags & Qt.ItemIsEnabled


def test_skill_model_selection_persists_across_client_change_default(qapp):
    """With default filterByClient=False, client change must not affect selection."""
    skills = [
        {"name": "Client A Skill 1", "local_path": "/a1", "client": "Antigravity"},
        {"name": "Client A Skill 2", "local_path": "/a2", "client": "Antigravity"},
        {"name": "Client B Skill 1", "local_path": "/b1", "client": "Codex"},
        {"name": "Client B Skill 2", "local_path": "/b2", "client": "Codex"},
    ]
    model = SkillModel()
    model.setSkills(skills)

    # filterByClient defaults to False — client format doesn't filter view
    assert model.filterByClient is False

    model.selectByPaths(["/a1", "/a2"])
    assert set(model.getSelectedPaths()) == {"/a1", "/a2"}
    assert model.selectedCount == 2

    # Switch to client B — selection and count must stay unchanged
    model.clientFilter = "Codex"
    assert set(model.getSelectedPaths()) == {"/a1", "/a2"}
    assert model.selectedCount == 2, "selectedCount must not drop when filterByClient is False"
    assert model.data(model.index(0, 0), SkillModel.IsSelectedRole) is True
    assert model.data(model.index(1, 0), SkillModel.IsSelectedRole) is True

    # Switch back to client A — everything still intact
    model.clientFilter = "Antigravity"
    assert set(model.getSelectedPaths()) == {"/a1", "/a2"}
    assert model.selectedCount == 2


def test_skill_model_selection_survives_client_filter_when_explicitly_enabled(qapp):
    """Even with filterByClient=True, _selected_ids must persist (only filtered count drops)."""
    skills = [
        {"name": "Client A Skill 1", "local_path": "/a1", "client": "Antigravity"},
        {"name": "Client A Skill 2", "local_path": "/a2", "client": "Antigravity"},
        {"name": "Client B Skill 1", "local_path": "/b1", "client": "Codex"},
        {"name": "Client B Skill 2", "local_path": "/b2", "client": "Codex"},
    ]
    model = SkillModel()
    model.setSkills(skills)
    model.filterByClient = True

    model.selectByPaths(["/a1", "/a2"])
    assert set(model.getSelectedPaths()) == {"/a1", "/a2"}
    assert model.selectedCount == 2

    # Switch to client B — selection persists, but filtered count drops
    model.clientFilter = "Codex"
    assert set(model.getSelectedPaths()) == {"/a1", "/a2"}, (
        "Selection changed when it should not have"
    )
    assert model.data(model.index(0, 0), SkillModel.IsSelectedRole) is False
    assert model.data(model.index(1, 0), SkillModel.IsSelectedRole) is False
    assert model.selectedCount == 0, "selectedCount drops because client-filtered skills are hidden"

    # Switch back to client A — original selection restored in view
    model.clientFilter = "Antigravity"
    assert set(model.getSelectedPaths()) == {"/a1", "/a2"}
    assert model.selectedCount == 2
    assert model.data(model.index(0, 0), SkillModel.IsSelectedRole) is True
    assert model.data(model.index(1, 0), SkillModel.IsSelectedRole) is True


def test_skill_model_set_data(qapp, skill_list):
    model = SkillModel()
    model.setSkills(skill_list)
    # toggleSelection is the intended way to change selection
    model.toggleSelection(0)
    assert model.data(model.index(0), SkillModel.IsSelectedRole) is True

    # Verify that setData still returns False for now (unimplemented)
    res = model.setData(model.index(0), False, SkillModel.IsSelectedRole)
    assert res is False
