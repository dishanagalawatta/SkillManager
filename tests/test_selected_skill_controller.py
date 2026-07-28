"""Unit tests for SelectedSkillController and resolve_skill_file_path."""

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from skill_manager.controllers.selected_skill_controller import SelectedSkillController
from skill_manager.core.parsing.skill import resolve_skill_file_path


class MockSkillModel(QObject):
    """Mock SkillModel emitting Qt dataChanged & modelReset signals."""

    dataChanged = Signal(object, object, list)  # noqa: N815
    modelReset = Signal()  # noqa: N815


class MockApp(QObject):
    """Mock application for controller testing."""

    def __init__(self):
        super().__init__()
        self._library_model = MockSkillModel()
        self._quick_copy_model = MockSkillModel()


def test_resolve_skill_file_path_direct_file(tmp_path: Path):
    """Direct .md file path should return as-is."""
    skill_file = tmp_path / "test_skill.md"
    skill_file.write_text("# Test Skill\n\nSome body content.")

    res = resolve_skill_file_path(str(skill_file))
    assert res == str(skill_file)


def test_resolve_skill_file_path_directory(tmp_path: Path):
    """Directory containing SKILL.md should resolve to SKILL.md."""
    skill_dir = tmp_path / "my_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("--- \nname: my_skill\n---\n# My Skill")

    res = resolve_skill_file_path(str(skill_dir))
    assert res == str(skill_file)


def test_resolve_skill_file_path_non_existent():
    """Non-existent path should return None."""
    res = resolve_skill_file_path("/non/existent/path/skill.md")
    assert res is None


def test_selected_skill_controller_auto_read(tmp_path: Path):
    """setSelection should auto-read file from disk if body_content is missing."""
    skill_dir = tmp_path / "auto_read_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: Auto Read\ndescription: Test auto read\n---\n# Body Title\n\nFull body text."
    )

    app = MockApp()
    ctrl = SelectedSkillController(app)

    # Initial dictionary with empty body_content (as comes from discovery cache)
    skill_dict = {
        "name": "Auto Read",
        "local_path": str(skill_dir),
        "body_content": "",
        "raw_content": "",
    }

    ctrl.setSelection(skill_dict)

    assert ctrl.name == "Auto Read"
    assert "Full body text." in ctrl.body_content
    assert str(skill_dir) in ctrl.local_path


def test_selected_skill_controller_caching(tmp_path: Path):
    """setSelection should use cached parsed content on subsequent calls."""
    skill_file = tmp_path / "cached_skill.md"
    skill_file.write_text("# Cached Title\n\nCached content body.")

    app = MockApp()
    ctrl = SelectedSkillController(app)

    skill_dict = {
        "name": "Cached Skill",
        "local_path": str(skill_file),
        "body_content": "",
        "raw_content": "",
    }

    ctrl.setSelection(skill_dict)
    assert "Cached content body." in ctrl.body_content

    # Modify file on disk; second setSelection should return cached version
    skill_file.write_text("# Modified Title\n\nModified content.")
    ctrl.setSelection(skill_dict)
    assert "Cached content body." in ctrl.body_content
