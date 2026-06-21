from unittest.mock import MagicMock

import pytest
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication


@pytest.fixture
def setup_controller_data(qapp, app_controller, temp_dir):
    """Resets and sets up dummy data for the controller before each test."""
    # Setup some initial dummy data in a test-scoped directory
    lib_dir = temp_dir / "lib"
    lib_dir.mkdir(exist_ok=True)

    # Each skill must be in its own subfolder with a SKILL.md file
    skill_folder = lib_dir / "test-skill"
    skill_folder.mkdir(exist_ok=True)
    (skill_folder / "SKILL.md").write_text("# Test Skill\nDescription here.", encoding="utf-8")

    proj_dir = temp_dir / "proj"
    proj_dir.mkdir(exist_ok=True)

    # Clear previous state
    while app_controller.sources:
        app_controller.config_mgr.removeSource(app_controller.sources[0])
    while app_controller.projects:
        app_controller.config_mgr.removeProject(app_controller.projects[0])

    # Add new ones
    app_controller.config_mgr.addSource(str(lib_dir))
    app_controller.config_mgr.addProject(str(proj_dir))

    # Add a skill to the project directory too
    proj_skill_dir = proj_dir / ".agents" / "skills" / "proj-skill"
    proj_skill_dir.mkdir(parents=True, exist_ok=True)
    (proj_skill_dir / "SKILL.md").write_text("# Project Skill\nDescription here.", encoding="utf-8")

    # Add a dummy update package by adding a source to the config
    # The AppController should pick it up on refresh.
    # However, to be absolutely sure for the Updates view, we use the controller method
    app_controller.updates.addUpdatePackage("test-package")

    # Trigger refresh
    app_controller.refreshSkills()

    # Process events to allow schedule_on_ui_thread callbacks to run
    qapp.processEvents()

    # Clear filters on both models to be sure
    app_controller.libraryModel.projectFilter = ""
    app_controller.libraryModel.filterByClient = False
    app_controller.quickCopyModel.projectFilter = ""
    app_controller.quickCopyModel.filterByClient = False
    qapp.processEvents()


def test_ui_comprehensive_flow(qtbot, qml_engine, app_controller, setup_controller_data):
    """Verify navigation, search filtering, and quick copy flow in a single sequence."""
    root = qml_engine.rootObjects()[0]
    qapp = QApplication.instance()
    assert qapp is not None, "QApplication.instance() returned None"

    # --- 1. Navigation ---
    # Force a known starting view
    app_controller.ui.currentView = "QuickCopy"
    qapp.processEvents()
    assert app_controller.ui.currentView == "QuickCopy"

    # Find and click Library button
    nav_library = root.findChild(QQuickItem, "navLibrary")
    assert nav_library is not None
    nav_library.clicked.emit()
    qapp.processEvents()
    assert app_controller.ui.currentView == "Library"

    # --- 2. Search Filtering ---
    # Give Loader time to settle
    qtbot.wait(100)
    qapp.processEvents()

    # Find search input
    search_input = root.findChild(QQuickItem, "librarySearchInput")
    assert search_input is not None

    # Initial count
    initial_count = app_controller.libraryModel.rowCount()
    assert initial_count > 0

    # Type something that doesn't match
    # Manually trigger the model filter
    app_controller.libraryModel.filterText = "xyzzy_no_match"
    qapp.processEvents()
    qtbot.wait(50)

    # Verify model is filtered
    assert app_controller.libraryModel.rowCount() == 0

    # Clear search
    app_controller.libraryModel.filterText = ""
    qapp.processEvents()
    qtbot.wait(50)
    assert app_controller.libraryModel.rowCount() == initial_count

    # --- 3. Quick Copy Flow ---
    # Go to Quick Copy
    nav_qc = root.findChild(QQuickItem, "navQuickCopy")
    nav_qc.clicked.emit()
    qapp.processEvents()
    assert app_controller.ui.currentView == "QuickCopy"

    # Ensure model has data
    assert app_controller.quickCopyModel.rowCount() > 0

    # Trigger selection of first item (Project Skill)
    app_controller.quickCopyModel.toggleSelection(0)
    qapp.processEvents()
    assert app_controller.quickCopyModel.selectedCount == 1

    # Find and click copy button
    copy_btn = root.findChild(QQuickItem, "copySelectedBtn")
    assert copy_btn is not None
    copy_btn.clicked.emit()
    qapp.processEvents()

    # Verify clipboard
    from PySide6.QtGui import QGuiApplication

    clipboard = QGuiApplication.clipboard()
    # We added "Project Skill" in a folder named "proj-skill"
    # The copier might copy the name or the command reference like /proj-skill
    text = clipboard.text()
    assert "proj-skill" in text or "Project Skill" in text


def test_ui_updates_flow(qtbot, qml_engine, app_controller, setup_controller_data):
    """Verify navigation to Updates view and interaction with scan/lists."""
    root = qml_engine.rootObjects()[0]
    qapp = QApplication.instance()
    assert qapp is not None, "QApplication.instance() returned None"

    # --- 1. Navigation ---
    nav_updates = root.findChild(QQuickItem, "navUpdates")
    assert nav_updates is not None
    nav_updates.clicked.emit()
    qapp.processEvents()
    assert app_controller.ui.currentView == "Updates"

    # --- 2. Check Lists ---
    # Wait for view to load
    qtbot.wait(200)
    qapp.processEvents()

    packages_list = root.findChild(QQuickItem, "uv_packagesList")
    assert packages_list is not None
    # We added one source via addSource in setup_controller_data
    assert len(app_controller.updatePackages) >= 1

    projects_list = root.findChild(QQuickItem, "uv_projectsList")
    assert projects_list is not None
    assert len(app_controller.config_controller.updateProjects) >= 1

    # --- 3. Scan Action ---
    scan_btn = root.findChild(QQuickItem, "scanUpdatesBtn")
    assert scan_btn is not None

    # Mock the scan method to verify call
    with pytest.MonkeyPatch().context() as m:
        mock_scan = MagicMock()
        # In AppController, the controller is self.updates
        m.setattr(app_controller.updates, "scanForUpdates", mock_scan)
        scan_btn.clicked.emit()
        qapp.processEvents()
        mock_scan.assert_called_once()
