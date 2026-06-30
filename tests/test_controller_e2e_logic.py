from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication

from skill_manager.app import AppController
from skill_manager.utils.task_runner import SynchronousTaskRunner


@pytest.fixture
def app_controller(qapp, mock_config, temp_dir, monkeypatch):
    """Provides an AppController initialized for testing."""
    # Isolation: Mock cache to prevent loading real data from project root
    import skill_manager.core.discovery as discovery
    import skill_manager.core.persistence as persistence

    monkeypatch.setattr(persistence, "load_cache", lambda: None)
    monkeypatch.setattr(persistence, "save_cache", lambda x: True)
    monkeypatch.setattr(discovery, "load_cache", lambda: None)
    monkeypatch.setattr(discovery, "save_cache", lambda x: True)

    # We use SynchronousTaskRunner to avoid threading issues in tests
    controller = AppController(skip_initial_load=True, config=mock_config)
    controller.task_runner = SynchronousTaskRunner()

    # Setup some initial dummy data in a proper structure
    lib_dir = temp_dir / "lib"
    lib_dir.mkdir(exist_ok=True)
    skill_folder = lib_dir / "test-skill"
    skill_folder.mkdir(exist_ok=True)
    skill_file = skill_folder / "SKILL.md"
    # Using frontmatter so name is correctly parsed as "Test Skill"
    skill_file.write_text(
        "---\nname: Test Skill\ncategory: Testing\n---\n# Test Skill\nDescription here.",
        encoding="utf-8",
    )

    proj_dir = temp_dir / "proj"
    proj_dir.mkdir(exist_ok=True)

    # Setup project skill (for Quick Copy) in .agents/skills
    proj_skills_root = proj_dir / ".agents" / "skills"
    proj_skills_root.mkdir(parents=True, exist_ok=True)
    proj_skill_folder = proj_skills_root / "project-skill"
    proj_skill_folder.mkdir(exist_ok=True)
    (proj_skill_folder / "SKILL.md").write_text(
        "---\nname: Project Skill\ncategory: ProjCategory\n---\n# Project Skill\nProj description.",
        encoding="utf-8",
    )

    # Setup test configuration
    # Clear EVERYTHING to ensure total isolation from default/real config
    controller._sources = []
    controller._projects = []
    mock_config.set("projects", [])
    mock_config.set("sources", [])

    controller.config_mgr.addSource(str(lib_dir))
    controller.config_mgr.addProject(str(proj_dir))

    # Force a refresh
    controller.refreshSkills("test", False)

    yield controller

    # Teardown: stop timers, flush pending events, and destroy the controller
    # to prevent access violations in pytestqt._process_events.
    controller.on_quit()
    from PySide6.QtCore import QCoreApplication

    QCoreApplication.processEvents()  # Flush pending QTimer.singleShot events
    controller.deleteLater()  # Schedule controller for deletion
    QCoreApplication.processEvents()  # Process the deletion event


def test_controller_navigation_workflow(app_controller):
    """Verify navigation state management across controllers."""
    # Navigate to Library
    app_controller.currentView = "Library"
    assert app_controller.ui.currentView == "Library"
    assert app_controller.skillModel == app_controller.libraryModel

    # Navigate to Settings
    app_controller.currentView = "Settings"
    assert app_controller.ui.currentView == "Settings"

    # Navigate to Quick Copy (allow both variants if space-stripped)
    app_controller.currentView = "Quick Copy"
    assert app_controller.ui.currentView.replace(" ", "") == "QuickCopy"
    assert app_controller.skillModel == app_controller.quickCopyModel


def test_controller_search_and_filter_workflow(app_controller):
    """Verify search filtering logic through the controller bridge."""
    app_controller.currentView = "Library"
    # Library should only have "Test Skill" (is_package_only=True)
    initial_count = app_controller.libraryModel.rowCount()
    assert initial_count == 1

    # Simulate search input from UI
    # We use a very long random string that definitely won't match
    app_controller.libraryModel.filterText = "KJFSD8934URKFDJ9834URKFDJ9834UR"
    assert app_controller.libraryModel.rowCount() == 0


def test_controller_quick_copy_workflow(app_controller):
    """Verify the end-to-end quick copy flow via controller slots."""
    app_controller.currentView = "Quick Copy"

    # Ensure model is loaded (should have 1 project skill)
    assert app_controller.quickCopyModel.rowCount() > 0

    # Find the index of "Project Skill"
    test_skill_idx = -1
    for i in range(app_controller.quickCopyModel.rowCount()):
        if app_controller.quickCopyModel.get_skill_at(i).get("name") == "Project Skill":
            test_skill_idx = i
            break

    assert test_skill_idx != -1, "Project Skill not found in Quick Copy model"

    app_controller.quickCopyModel.toggleSelection(test_skill_idx)
    assert app_controller.quickCopyModel.selectedCount == 1

    # Set client format to Antigravity (returns /Name)
    app_controller.ui.setClientFormat("Antigravity")

    # Execute copy
    app_controller.ops.copySelectedSkillsToClipboard()

    # Verify clipboard
    clipboard = QGuiApplication.clipboard()
    text = clipboard.text()
    assert text == "/Project Skill"


def test_controller_skill_deletion_workflow(app_controller, temp_dir):
    """Verify skill deletion flow and its impact on the models."""
    # Use Quick Copy view which contains project skills
    app_controller.currentView = "Quick Copy"

    # Find our project skill
    test_skill_idx = -1
    for i in range(app_controller.quickCopyModel.rowCount()):
        if app_controller.quickCopyModel.get_skill_at(i).get("name") == "Project Skill":
            test_skill_idx = i
            break

    assert test_skill_idx != -1, "Project Skill not found in Quick Copy model"
    initial_count = app_controller.quickCopyModel.rowCount()

    # Get the skill data
    skill_data = app_controller.quickCopyModel.get_skill_at(test_skill_idx)
    skill_path = skill_data.get("local_path")
    assert skill_path is not None

    # Delete the skill
    app_controller.ops.deleteSkill(skill_path)

    # Process events to let the QTimer fire refreshSkills
    from PySide6.QtCore import QCoreApplication

    QCoreApplication.processEvents()  # Fires refreshSkills
    QCoreApplication.processEvents()  # Fires _on_discovery_finished

    # Verify file is gone
    assert not Path(skill_path).exists()

    # Verify model is updated
    final_count = app_controller.quickCopyModel.rowCount()
    assert final_count == initial_count - 1
