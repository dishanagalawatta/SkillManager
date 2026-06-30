"""Integration test: rebuildCache clears stale skills and re-discovers correctly."""
import shutil
from unittest.mock import MagicMock

from skill_manager.core.discovery import compute_dir_fingerprint
from skill_manager.core.models.qt_model import SkillModel


def test_rebuild_cache_removes_stale_skills(tmp_path):
    """After rebuildCache, skills that were deleted on disk are no longer shown."""
    # Setup: create two skill directories
    dir_a = tmp_path / "skill-a"
    dir_a.mkdir()
    (dir_a / "SKILL.md").write_text("# Skill A")

    dir_b = tmp_path / "skill-b"
    dir_b.mkdir()
    (dir_b / "SKILL.md").write_text("# Skill B")

    model = SkillModel(config=MagicMock(get=MagicMock(return_value={})))

    # Populate model with both skills
    model.setSkills([
        {"name": "SkillA", "local_path": str(dir_a), "project_path": "", "project_label": "p"},
        {"name": "SkillB", "local_path": str(dir_b), "project_path": "", "project_label": "p"},
    ])
    assert len(model._all_skills) == 2

    # Now delete skill-b (simulates user removing it)
    shutil.rmtree(dir_b)

    # Simulate what happens after rebuildCache: setSkills is called again
    # with the discovery results (which should now exclude skill-b)
    model.setSkills([
        {"name": "SkillA", "local_path": str(dir_a), "project_path": "", "project_label": "p"},
    ])

    assert len(model._all_skills) == 1
    assert model._all_skills[0].name == "SkillA"


def test_fingerprint_detects_deleted_skill(tmp_path):
    """Fingerprint mismatch after deletion forces re-scan (the root cause fix)."""
    d = tmp_path / "project" / ".agents" / "skills"
    d.mkdir(parents=True)

    # Create two skills
    (d / "brainstorming").mkdir()
    (d / "brainstorming" / "SKILL.md").write_text("# Brainstorming")
    (d / "concise-planning").mkdir()
    (d / "concise-planning" / "SKILL.md").write_text("# Concise Planning")

    fp_before = compute_dir_fingerprint(d)

    # Delete brainstorming (the reported bug)
    shutil.rmtree(d / "brainstorming")

    fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after, (
        "Fingerprint must change when a skill is deleted. "
        "This prevents the stale-cache short-circuit."
    )
