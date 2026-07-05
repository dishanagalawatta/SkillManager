"""Tests for the QuickCopy project-filter bug fix.

Covers:
1. Label parity between ``project_label`` and ``ConfigController.getProjectLabel``
2. Boot normalization of stored project paths
3. ``addOrUpdateSkills`` recomputing ``project_label`` from ``project_path``
4. ``setCurrentProject`` with an unknown label (warning, empty list)
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.config_controller import ConfigController
from skill_manager.core.quick_copy import project_label

# ---------------------------------------------------------------------------
# 1. Label parity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, aliases",
    [
        # Standard .agents/skills path
        ("/work/my-project/.agents/skills", {}),
        # Root path (no .agents/skills in path) -- the bug scenario
        ("/work/my-project", {}),
        # Path with custom subfolder between root and .agents/skills
        ("/work/my-project/subdir/.agents/skills", {}),
        # Alias overrides
        ("/work/old-name", {"/work/old-name": "Legacy Name"}),
    ],
)
def test_project_label_parity(path, aliases):
    """project_label() and getProjectLabel() must return the same string."""
    mock_app = MagicMock()
    mock_app._project_aliases = aliases
    ctrl = ConfigController(mock_app)

    expected = project_label(path, project_aliases=aliases)
    actual = ctrl.getProjectLabel(path)
    assert actual == expected, (
        f"Label mismatch for {path!r}: project_label={expected!r}, getProjectLabel={actual!r}"
    )


def test_project_label_parity_with_alias():
    """Alias set via setProjectAlias must produce matching labels."""
    mock_app = MagicMock()
    mock_app._project_aliases = {}
    mock_app._library_model = MagicMock()
    mock_app._quick_copy_model = MagicMock()
    ctrl = ConfigController(mock_app)

    ctrl.setProjectAlias("/work/old-name", "Legacy Name")

    expected = project_label("/work/old-name", project_aliases={"/work/old-name": "Legacy Name"})
    actual = ctrl.getProjectLabel("/work/old-name")
    assert actual == expected
    assert actual == "Legacy Name"


def test_project_label_parity_root_path_no_aliases():
    """Root path with no aliases: both must return consistent labels."""
    mock_app = MagicMock()
    mock_app._project_aliases = {}
    ctrl = ConfigController(mock_app)

    if sys.platform == "win32":
        path = "C:\\Users\\test\\my-project"
    else:
        path = "/home/test/my-project"

    expected = project_label(path)
    actual = ctrl.getProjectLabel(path)
    assert actual == expected, (
        f"Root path label mismatch: project_label={expected!r}, getProjectLabel={actual!r}"
    )


# ---------------------------------------------------------------------------
# 2. Boot normalization
# ---------------------------------------------------------------------------


def _make_config(projects, aliases=None):
    """Build a mock ConfigManager for AppController tests."""
    cfg = MagicMock()
    data = {
        "sources": [],
        "projects": projects,
        "project_aliases": aliases or {},
        "default_client": "Last Selected",
        "client_format": "Antigravity",
        "skills": [],
        "custom_collections": {},
        "skill_package_auto_update_mode": "off",
        "collapsed_categories": [],
        "show_archived": False,
        "category_filter": "",
        "collection_filter": False,
        "project_filter": "",
        "show_commands": True,
        "show_starred": True,
        "is_package_only": None,
        "project_selections": {},
    }
    cfg.get = MagicMock(side_effect=lambda key, default=None: data.get(key, default))
    return cfg


def test_boot_normalize_project_paths(tmp_path):
    """Stored root paths are rewritten to .agents/skills on startup."""
    from skill_manager.app import AppController

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    root_path = str(project_root)
    config = _make_config([root_path])

    patches = [
        patch("skill_manager.app.ConfigManager", return_value=config),
        patch("skill_manager.app.BackgroundTaskRunner"),
        patch("skill_manager.app.QtScheduler"),
        patch("skill_manager.app.load_archive", return_value=[]),
        patch("skill_manager.app.load_starred", return_value=[]),
        patch("skill_manager.app.get_diagnostic_logger"),
    ]
    for p in patches:
        p.start()

    try:
        ctrl = AppController(skip_initial_load=True, config=config)
    finally:
        for p in patches:
            p.stop()

    assert len(ctrl._projects) == 1
    normalized = ctrl._projects[0].replace("\\", "/")
    assert normalized.endswith((".agents/skills", ".agents\\skills")), (
        f"Expected .agents/skills suffix, got {ctrl._projects[0]!r}"
    )
    config.set.assert_any_call("projects", ctrl._projects)


def test_boot_normalize_no_change_when_already_normalized(tmp_path):
    """Already-normalized paths are not rewritten."""
    from skill_manager.app import AppController

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    canonical_path = str(skills_dir)
    config = _make_config([canonical_path])

    patches = [
        patch("skill_manager.app.ConfigManager", return_value=config),
        patch("skill_manager.app.BackgroundTaskRunner"),
        patch("skill_manager.app.QtScheduler"),
        patch("skill_manager.app.load_archive", return_value=[]),
        patch("skill_manager.app.load_starred", return_value=[]),
        patch("skill_manager.app.get_diagnostic_logger"),
    ]
    for p in patches:
        p.start()

    try:
        ctrl = AppController(skip_initial_load=True, config=config)
    finally:
        for p in patches:
            p.stop()

    assert ctrl._projects[0] == canonical_path


# ---------------------------------------------------------------------------
# 3. addOrUpdateSkills normalizes project_label
# ---------------------------------------------------------------------------


def test_add_or_update_skills_normalizes_project_label(tmp_path):
    """addOrUpdateSkills recomputes project_label even if one is provided."""
    from skill_manager.core.models.qt_model import SkillModel

    model = SkillModel(config=MagicMock(get=MagicMock(return_value={})))

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    skill_dict = {
        "name": "TestSkill",
        "local_path": str(skills_dir / "TestSkill"),
        "project_path": str(project_root),
        "project_label": "WRONG LABEL",
    }

    model.addOrUpdateSkills([skill_dict])

    assert len(model._all_skills) == 1
    skill = model._all_skills[0]
    expected_label = project_label(str(skills_dir))
    assert skill.project_label == expected_label, (
        f"Expected {expected_label!r}, got {skill.project_label!r}"
    )


def test_add_or_update_skills_keeps_correct_label(tmp_path):
    """Skills with already-correct project_label are unchanged."""
    from skill_manager.core.models.qt_model import SkillModel

    model = SkillModel(config=MagicMock(get=MagicMock(return_value={})))

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    correct_label = project_label(str(skills_dir))
    skill_dict = {
        "name": "TestSkill",
        "local_path": str(skills_dir / "TestSkill"),
        "project_path": str(project_root),
        "project_label": correct_label,
    }

    model.addOrUpdateSkills([skill_dict])
    assert model._all_skills[0].project_label == correct_label


def test_add_or_update_skills_with_aliases(tmp_path):
    """addOrUpdateSkills respects project aliases when recomputing labels."""
    from skill_manager.core.models.qt_model import SkillModel

    project_root = tmp_path / "old-name"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    config = MagicMock()
    config.get = MagicMock(
        side_effect=lambda key, default=None: {
            "project_aliases": {str(skills_dir): "My Legacy Project"}
        }.get(key, default)
    )
    model = SkillModel(config=config)

    skill_dict = {
        "name": "TestSkill",
        "local_path": str(skills_dir / "TestSkill"),
        "project_path": str(project_root),
        "project_label": "",
    }

    model.addOrUpdateSkills([skill_dict])
    assert model._all_skills[0].project_label == "My Legacy Project"


# ---------------------------------------------------------------------------
# 4. setCurrentProject with unknown label
# ---------------------------------------------------------------------------


def test_set_current_project_unknown_label_keeps_filter():
    """setCurrentProject with an unknown label keeps the filter (empty list)."""
    from skill_manager.app import AppController

    config = _make_config(["/work/p1/.agents/skills"])

    patches = [
        patch("skill_manager.app.ConfigManager", return_value=config),
        patch("skill_manager.app.BackgroundTaskRunner"),
        patch("skill_manager.app.QtScheduler"),
        patch("skill_manager.app.load_archive", return_value=[]),
        patch("skill_manager.app.load_starred", return_value=[]),
        patch("skill_manager.app.get_diagnostic_logger"),
    ]
    for p in patches:
        p.start()

    try:
        ctrl = AppController(skip_initial_load=True, config=config)
    finally:
        for p in patches:
            p.stop()

    # Set an unknown label -- filter should still be applied
    ctrl.setCurrentProject("Nonexistent Project")
    assert ctrl._current_project_label == "Nonexistent Project"
    assert ctrl._quick_copy_model.projectFilter == "Nonexistent Project"


def test_set_current_project_valid_label():
    """setCurrentProject with a valid label sets the filter correctly."""
    from skill_manager.app import AppController

    config = _make_config(["/work/p1/.agents/skills"])

    patches = [
        patch("skill_manager.app.ConfigManager", return_value=config),
        patch("skill_manager.app.BackgroundTaskRunner"),
        patch("skill_manager.app.QtScheduler"),
        patch("skill_manager.app.load_archive", return_value=[]),
        patch("skill_manager.app.load_starred", return_value=[]),
        patch("skill_manager.app.get_diagnostic_logger"),
    ]
    for p in patches:
        p.start()

    try:
        ctrl = AppController(skip_initial_load=True, config=config)
    finally:
        for p in patches:
            p.stop()

    # During __init__, _current_project_label was set to the first project label.
    # Verify it matches the canonical label.
    label = project_label("/work/p1/.agents/skills")
    assert ctrl._current_project_label == label

    # Now switch to a different label, then back — the filter should update.
    ctrl.setCurrentProject("")
    assert ctrl._quick_copy_model.projectFilter == ""

    ctrl.setCurrentProject(label)
    assert ctrl._current_project_label == label
    assert ctrl._quick_copy_model.projectFilter == label
