import pytest
import os
import time
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QTimer, Qt, QObject, QPointF
from PySide6.QtGui import QGuiApplication, QClipboard
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from skill_manager.app import AppController

@pytest.fixture
def e2e_app(qtbot, mock_config, temp_dir):
    """Sets up a full QML engine for E2E testing."""
    # Force isolation by reloading config if needed, 
    # but mock_config fixture already set the env var.
    # We should ensure the discovery service doesn't load real data.
    
    # 1. Prepare mock data
    lib_path = temp_dir / "library"
    lib_path.mkdir()
    # Create a unique name to avoid collisions with real skills
    unique_name = f"E2E-Test-Skill-{time.time()}"
    skill_file = lib_path / "test-skill" / "SKILL.md"
    skill_file.parent.mkdir()
    skill_file.write_text(f"# {unique_name}\ncategory: Testing\n")
    
    # Update config
    from skill_manager.core.config import ConfigManager
    cfg = ConfigManager()
    cfg.set("sources", [str(lib_path)])
    cfg.set("client_format", "Gemini CLI")
    cfg.save()

    # 2. Initialize Controller with patched discovery to prevent real data leaks
    with patch("skill_manager.app.DiscoveryService"), \
         patch("skill_manager.app.AppController.load_initial_data"):
        controller = AppController()
    
    # Ensure selected IDs are clear
    controller.libraryModel._selected_ids.clear()
    controller.quickCopyModel._selected_ids.clear()

    # Try to register singleton, handle if already registered
    try:
        qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
    except Exception:
        pass # Already registered in previous test

    # 3. Setup Engine
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
    engine.addImportPath(str(qml_dir.parent))
    
    qml_file = qml_dir / "Main.qml"
    engine.load(str(qml_file))
    
    if not engine.rootObjects():
        pytest.fail("Failed to load QML root objects")
    
    # 4. Wait for initial loading
    qtbot.waitUntil(lambda: not controller.isLoading, timeout=5000)
    
    # Manually set the skill on BOTH models to avoid discovery isolation issues
    mock_skill = {
        "id": "e2e-id",
        "name": unique_name,
        "category": "Testing",
        "local_path": str(skill_file.parent),
        "is_source": False, # Make it look like a project skill
        "is_essential": True, # And also essential for good measure
        "project": "Test Project",
        "project_label": "Test Project"
    }
    controller.libraryModel.setSkills([mock_skill])
    controller.quickCopyModel.setSkills([mock_skill])
    
    return controller, engine, qtbot, unique_name

def test_e2e_sync_to_clipboard(e2e_app):
    controller, engine, qtbot, unique_name = e2e_app
    root = engine.rootObjects()[0]
    
    # 1. Navigate to Quick Copy view
    controller.currentView = "QuickCopy"
    qtbot.wait(200)
    
    # 2. Use Search to find our specific skill and select it
    controller.searchQuery = unique_name
    qtbot.wait(200)
    
    # Toggle selection of the first item
    controller.skillModel.toggleSelection(0)
    assert controller.skillModel.selectedCount == 1
    
    # 3. Find the "Copy Selected" button
    copy_btn = root.findChild(QObject, "copySelectedBtn")
    assert copy_btn is not None
    
    # 4. Clear clipboard first
    clipboard = QGuiApplication.clipboard()
    clipboard.setText("OLD_VALUE")
    
    # 5. Click the button
    # In headless environments, mouseClick on QML items is often unreliable.
    # invokeMethod is more robust for CI while still testing the UI->Controller integration.
    from PySide6.QtCore import QMetaObject
    QMetaObject.invokeMethod(copy_btn, "clicked")
    
    # 6. Verify clipboard content
    qtbot.waitUntil(lambda: "OLD_VALUE" not in clipboard.text(), timeout=2000)
    
    final_text = clipboard.text()
    assert unique_name in final_text or "test-skill" in final_text
    assert "@" in final_text
    assert controller.statusMessage.startswith("Copied")
