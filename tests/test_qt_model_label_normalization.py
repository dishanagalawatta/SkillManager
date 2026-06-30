"""Tests for addOrUpdateSkills project_path normalization.

Verifies that skills loaded from cache with stale root-path project_path
get their project_label recomputed from the NORMALIZED path via get_skills_dir,
so the label matches what getProjectLabel (dropdown) produces.
"""
from unittest.mock import MagicMock

from skill_manager.core.models.qt_model import SkillModel
from skill_manager.core.quick_copy import project_label


def _make_model():
    """Create a SkillModel with a mock config that has no aliases."""
    config = MagicMock()
    config.get = MagicMock(side_effect=lambda key, default=None: {
        "project_aliases": {},
        "collapsed_categories": [],
        "show_archived": False,
        "category_filter": "",
        "collection_filter": False,
        "project_filter": "",
        "client_format": "",
        "show_commands": True,
        "show_starred": True,
        "is_package_only": None,
        "project_selections": {},
    }.get(key, default))
    return SkillModel(config=config)


def test_root_path_normalized_to_skills_dir(tmp_path):
    """Skill with root-path project_path gets label matching normalized path."""
    model = _make_model()

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    # Feed a skill with root-path project_path and a stale label
    skill_dict = {
        "name": "TestSkill",
        "local_path": str(project_root / ".agents" / "skills" / "TestSkill"),
        "project_path": str(project_root),  # root path, not normalized
        "project_label": "stale-label",
    }

    model.addOrUpdateSkills([skill_dict])

    assert len(model._all_skills) == 1
    skill = model._all_skills[0]
    # The label should match what getProjectLabel produces for the normalized path
    expected = project_label(str(skills_dir))
    assert skill.project_label == expected, (
        f"Expected {expected!r}, got {skill.project_label!r}"
    )


def test_normalized_path_unchanged(tmp_path):
    """Skill with already-normalized project_path is unchanged."""
    model = _make_model()

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    correct_label = project_label(str(skills_dir))
    skill_dict = {
        "name": "TestSkill",
        "local_path": str(skills_dir / "TestSkill"),
        "project_path": str(skills_dir),
        "project_label": correct_label,
    }

    model.addOrUpdateSkills([skill_dict])
    assert model._all_skills[0].project_label == correct_label


def test_skills_dir_label_matches_dropdown(tmp_path):
    """The label from addOrUpdateSkills matches getProjectLabel for the normalized path."""
    from skill_manager.controllers.config_controller import ConfigController

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    model = _make_model()
    skill_dict = {
        "name": "TestSkill",
        "local_path": str(skills_dir / "TestSkill"),
        "project_path": str(project_root),  # root path
        "project_label": "",
    }

    model.addOrUpdateSkills([skill_dict])
    model_label = model._all_skills[0].project_label

    # The dropdown uses normalized paths from _projects, so getProjectLabel
    # receives the normalized .agents/skills path, not the root path.
    mock_app = MagicMock()
    mock_app._project_aliases = {}
    ctrl = ConfigController(mock_app)
    dropdown_label = ctrl.getProjectLabel(str(skills_dir))

    assert model_label == dropdown_label, (
        f"Model label {model_label!r} != dropdown label {dropdown_label!r}"
    )


def test_mismatch_warning_emitted(tmp_path):
    """A WARNING diagnostic is emitted when incoming label differs from recomputed."""
    from skill_manager.core.diagnostics import CATEGORY_PROJECT_LABEL_MISMATCH

    model = _make_model()

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    skill_dict = {
        "name": "TestSkill",
        "local_path": str(skills_dir / "TestSkill"),
        "project_path": str(project_root),
        "project_label": "completely-wrong-label",
    }

    # Enable diagnostic logging so the event is captured
    from skill_manager.core.diagnostics import get_diagnostic_logger

    diag = get_diagnostic_logger()
    was_enabled = diag.is_enabled()
    diag.set_enabled(True)
    # Clear ring buffer to avoid accumulation from prior tests
    diag.ring.clear()
    try:
        model.addOrUpdateSkills([skill_dict])

        # Check the ring buffer directly
        events = [
            e
            for e in diag.ring
            if e.get("category") == CATEGORY_PROJECT_LABEL_MISMATCH
        ]
        assert len(events) == 1, (
            f"Expected 1 mismatch event, got {len(events)}"
        )
        event = events[0]
        assert event["level"] == "WARNING"
        assert event["data"]["incoming_label"] == "completely-wrong-label"
        assert event["data"]["local_path"] == str(skills_dir / "TestSkill")
    finally:
        diag.set_enabled(was_enabled)
