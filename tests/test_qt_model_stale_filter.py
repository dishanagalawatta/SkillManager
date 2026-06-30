"""Tests that SkillModel accepts skills with any local_path.

The stale-skill filtering is handled at the discovery/cache level
(fingerprint + rebuildCache), NOT at the model level. setSkills and
addOrUpdateSkills accept whatever they receive — the discovery layer
is responsible for only providing existing skills.
"""
from unittest.mock import MagicMock


def _make_model():
    """Create a SkillModel with minimal config."""
    from skill_manager.core.models.qt_model import SkillModel

    config = MagicMock()
    config.get = MagicMock(return_value={})
    return SkillModel(config=config)


def test_add_or_update_skills_accepts_fake_paths(tmp_path):
    """addOrUpdateSkills does not filter by local_path existence."""
    model = _make_model()

    real_dir = tmp_path / "real-skill"
    real_dir.mkdir()
    fake_path = str(tmp_path / "fake-skill")

    skills = [
        {"name": "Real", "local_path": str(real_dir), "project_path": "", "project_label": "p"},
        {"name": "Fake", "local_path": fake_path, "project_path": "", "project_label": "p"},
    ]

    model.addOrUpdateSkills(skills)

    assert len(model._all_skills) == 2


def test_add_or_update_skills_empty_path_accepted():
    """addOrUpdateSkills accepts skills with empty local_path."""
    model = _make_model()

    skills = [
        {"name": "NoPath", "local_path": "", "project_path": "", "project_label": "p"},
    ]

    model.addOrUpdateSkills(skills)

    assert len(model._all_skills) == 1
    assert model._all_skills[0].name == "NoPath"


def test_set_skills_accepts_fake_paths(tmp_path):
    """setSkills does not filter by local_path existence."""
    model = _make_model()

    real_dir = tmp_path / "real-skill"
    real_dir.mkdir()
    fake_path = str(tmp_path / "fake-skill")

    skills = [
        {"name": "Real", "local_path": str(real_dir), "project_path": "", "project_label": "p"},
        {"name": "Fake", "local_path": fake_path, "project_path": "", "project_label": "p"},
    ]

    model.setSkills(skills)

    assert len(model._all_skills) == 2


def test_set_skills_empty_list_works():
    """setSkills with empty list results in empty model."""
    model = _make_model()

    model.setSkills([])

    assert len(model._all_skills) == 0
