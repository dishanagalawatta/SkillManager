import os

import pytest

from skill_manager.app import AppController


@pytest.fixture
def discovery_controller(session_mock_config, session_temp_dir):
    """Provides an AppController specifically for discovery testing."""
    # Clear the discovery cache before each test to ensure isolation
    from skill_manager.core.discovery import get_discovery_cache

    with get_discovery_cache() as cache:
        cache.clear()

    controller = AppController(skip_initial_load=True, config=session_mock_config)
    yield controller
    controller.on_quit()


def test_discovery_ui_integration(qtbot, qapp, discovery_controller, temp_dir):
    """Verify that adding a source folder triggers discovery and updates the UI model."""
    # 1. Setup a dummy source folder
    lib_dir = temp_dir / "new_library"
    lib_dir.mkdir()

    skill_folder = lib_dir / "my-new-skill"
    skill_folder.mkdir()
    # Use a very explicit SKILL.md that MUST be categorized as Testing
    (skill_folder / "SKILL.md").write_text(
        "---\nname: Test Automation\ncategory: Testing\n---\nThis is a testing skill for automation.",
        encoding="utf-8",
    )

    # 2. Add source via config controller
    discovery_controller.config_controller.addSource(str(lib_dir))
    qapp.processEvents()

    # 3. Trigger discovery
    discovery_controller.refreshSkills()

    qtbot.waitUntil(lambda: not discovery_controller.isLoading, timeout=5000)

    # 4. Verify UI Models are updated
    library_model = discovery_controller.libraryModel

    # Debug: print what we found
    found_names = []
    for i in range(library_model.rowCount()):
        name = library_model.data(library_model.index(i, 0), library_model.NameRole)
        cat = library_model.data(library_model.index(i, 0), library_model.CategoryRole)
        found_names.append(f"{name} ({cat})")
        if "Test Automation" in name:
            assert cat == "Testing"
            return

    pytest.fail(f"Test Automation skill not found. Found: {found_names}")


def test_discovery_incremental_ui_update(qtbot, qapp, discovery_controller, temp_dir):
    """Verify that changing a file and re-discovering only updates the changed item."""
    lib_dir = temp_dir / "incremental_lib"
    lib_dir.mkdir()

    skill_folder = lib_dir / "inc-skill"
    skill_folder.mkdir()
    skill_md = skill_folder / "SKILL.md"
    skill_md.write_text("---\nname: Version 1\n---\nBody", encoding="utf-8")

    discovery_controller.config_controller.addSource(str(lib_dir))
    discovery_controller.refreshSkills()
    qtbot.waitUntil(lambda: not discovery_controller.isLoading)

    assert discovery_controller.libraryModel.rowCount() > 0

    # Wait to ensure mtime change
    import time

    time.sleep(1.1)

    skill_md.write_text("---\nname: Version 2\n---\nBody", encoding="utf-8")
    # Touch the skill folder and the SKILL.md file
    os.utime(skill_md, None)
    os.utime(skill_folder, None)

    # Trigger refresh again
    discovery_controller.refreshSkills()
    qtbot.waitUntil(lambda: not discovery_controller.isLoading)

    # Check model
    for i in range(discovery_controller.libraryModel.rowCount()):
        name = discovery_controller.libraryModel.data(
            discovery_controller.libraryModel.index(i, 0),
            discovery_controller.libraryModel.NameRole,
        )
        if name == "Version 2":
            return

    pytest.fail("Model did not update to Version 2 after incremental discovery")
