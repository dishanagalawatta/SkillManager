import pytest
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

from skill_manager.app import AppController
from skill_manager.core.resources import qml_components_dir
from skill_manager.utils.task_runner import SynchronousTaskRunner


@pytest.fixture(scope="session")
def app_controller(session_mock_config, session_temp_dir):
    """Provides an AppController initialized for testing (session-scoped)."""
    # We use SynchronousTaskRunner to avoid threading issues in tests
    controller = AppController(skip_initial_load=True, config=session_mock_config)
    controller.task_runner = SynchronousTaskRunner()

    from contextlib import suppress

    import skill_manager.app
    skill_manager.app.current_test_controller = controller

    def controller_factory(qml_engine):
        return skill_manager.app.current_test_controller

    with suppress(Exception):
        from PySide6.QtQml import qmlRegisterSingletonType
        qmlRegisterSingletonType(AppController, "App", 1, 0, "AppController", controller_factory)

    return controller

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
        app_controller.config_mgr.removeSource(0)
    while app_controller.projects:
        app_controller.config_mgr.removeProject(0)

    # Add new ones
    app_controller.config_mgr.addSource(str(lib_dir))
    app_controller.config_mgr.addProject(str(proj_dir))

    # Add a skill to the project directory too
    proj_skill_dir = proj_dir / ".agents" / "skills" / "proj-skill"
    proj_skill_dir.mkdir(parents=True, exist_ok=True)
    (proj_skill_dir / "SKILL.md").write_text("# Project Skill\nDescription here.", encoding="utf-8")

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

    print(f"DEBUG: Library count: {app_controller.libraryModel.rowCount()}")
    print(f"DEBUG: Quick Copy count: {app_controller.quickCopyModel.rowCount()}")

@pytest.fixture
def qml_engine(qapp, app_controller):
    """Provides a QQmlApplicationEngine with the AppController already registered."""
    engine = QQmlApplicationEngine()

    engine.warnings.connect(lambda msg: print(f"QML Warning: {msg}"))
    engine.rootContext().setContextProperty("appController", app_controller)

    # Resolve QML directory relative to the src/ directory
    import skill_manager
    qml_dir = qml_components_dir(package_file=skill_manager.__file__)
    print(f"DEBUG: qml_dir={qml_dir}")
    print(f"DEBUG: qml_dir.parent={qml_dir.parent}")
    engine.addImportPath(str(qml_dir.parent))

    qml_file = qml_dir / "Main.qml"
    print(f"DEBUG: qml_file={qml_file}")
    if not qml_file.exists():
         pytest.fail(f"Main.qml not found at {qml_file}")

    engine.load(str(qml_file))

    if not engine.rootObjects():
        pytest.fail("Failed to load Main.qml")

    yield engine

    # Clean up engine to prevent crashes
    engine.deleteLater()

def test_ui_comprehensive_flow(qtbot, qml_engine, app_controller, setup_controller_data):
    """Verify navigation, search filtering, and quick copy flow in a single sequence."""
    root = qml_engine.rootObjects()[0]
    qapp = QApplication.instance()

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
    qtbot.wait(500)
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
    qtbot.wait(300)

    # Verify model is filtered
    assert app_controller.libraryModel.rowCount() == 0

    # Clear search
    app_controller.libraryModel.filterText = ""
    qapp.processEvents()
    qtbot.wait(300)
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
    # The copier might copy the name or the command reference like /skill:proj-skill
    text = clipboard.text()
    print(f"DEBUG: Clipboard text: {text}")
    assert "proj-skill" in text or "Project Skill" in text
