# Purpose: Verify the implementation of the Quick Copy Inspector improvements.
# Usage: Run via pytest: uv run pytest tests/test_quick_copy_inspector_improvements.py

from pathlib import Path

QML_DIR: Path = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


def test_skill_inspector_close_button_visibility() -> None:
    """Verify that the close button in SkillInspector.qml is visible for Quick Copy."""
    inspector_path: Path = QML_DIR / "SkillInspector.qml"
    content: str = inspector_path.read_text(encoding="utf-8")

    # The close button's visible property should not exclude root.isQuickCopy
    assert "visible: root.skill && root.skill.local_path !== undefined" in content
    assert "visible: !root.isQuickCopy" not in content


def test_quick_copy_view_right_click_toggle() -> None:
    """Verify that QuickCopyView.qml right-click delegate toggles the inspector."""
    view_path: Path = QML_DIR / "views" / "QuickCopyView.qml"
    content: str = view_path.read_text(encoding="utf-8")

    # The right-clicked handler should check if selectedSkill matches model.path and toggle it
    expected_handler: str = (
        "onRightClicked: {\n"
        "                        if (AppController.selectedSkill && AppController.selectedSkill.local_path === model.path) {\n"
        "                            AppController.ui_controller.selectSkill(-1)\n"
        "                        } else {\n"
        "                            AppController.ui_controller.selectSkill(index)\n"
        "                        }\n"
        "                    }"
    )

    # Normalize whitespace/indentation for checking
    normalized_content: str = " ".join(content.split())
    normalized_expected: str = " ".join(expected_handler.split())
    assert normalized_expected in normalized_content


def test_library_view_right_click_toggle() -> None:
    """Verify that LibraryView.qml right-click delegate toggles the inspector."""
    view_path: Path = QML_DIR / "views" / "LibraryView.qml"
    content: str = view_path.read_text(encoding="utf-8")

    # The right-clicked handler should check if selectedSkill matches model.path and toggle it
    expected_handler: str = (
        "onRightClicked: {\n"
        "                        if (AppController.selectedSkill && AppController.selectedSkill.local_path === model.path) {\n"
        "                            AppController.ui_controller.selectSkill(-1)\n"
        "                        } else {\n"
        "                            AppController.ui_controller.selectSkill(index)\n"
        "                        }\n"
        "                    }"
    )

    # Normalize whitespace/indentation for checking
    normalized_content: str = " ".join(content.split())
    normalized_expected: str = " ".join(expected_handler.split())
    assert normalized_expected in normalized_content


def test_image_inspector_minimum_width_increased() -> None:
    """Verify that ImageInspector's targetWidth minimum is 440 to prevent button overflow."""
    inspector_path: Path = QML_DIR / "ImageInspector.qml"
    content: str = inspector_path.read_text(encoding="utf-8")
    assert "Math.max(440, dynamicWidth)" in content
    assert "Math.max(350, dynamicWidth)" not in content


def test_image_inspector_default_width_increased() -> None:
    """Verify that ImageInspector's fallback width is 440 when no parent."""
    inspector_path: Path = QML_DIR / "ImageInspector.qml"
    content: str = inspector_path.read_text(encoding="utf-8")
    assert "parent ? parent.width * 0.5 : 440" in content


def _check_persisted_width_binding(inspector_type: str, view_content: str) -> None:
    """Check that an inspector type in a view uses persisted width from ui_controller."""
    marker = "SplitView.preferredWidth: {\n                    var p = AppController.ui_controller.inspectorWidth\n                    return p > 0 ? Math.max(p, targetWidth) : targetWidth\n                }"
    assert marker in view_content, f"{inspector_type} missing persisted width binding"


def _check_width_save_handler(inspector_type: str, view_content: str) -> None:
    """Check that an inspector saves width changes to ui_controller."""
    marker = "AppController.ui_controller.setInspectorWidth(width)"
    assert marker in view_content, f"{inspector_type} missing width save handler"


def test_library_view_inspectors_persist_width() -> None:
    """Verify that all three inspectors in LibraryView use persisted width binding and save on change."""
    view_path: Path = QML_DIR / "views" / "LibraryView.qml"
    content: str = view_path.read_text(encoding="utf-8")
    for insp in ("CommandInspector", "SkillInspector", "ImageInspector"):
        _check_persisted_width_binding(insp, content)
        _check_width_save_handler(insp, content)


def test_quick_copy_view_inspectors_persist_width() -> None:
    """Verify that all three inspectors in QuickCopyView use persisted width binding and save on change."""
    view_path: Path = QML_DIR / "views" / "QuickCopyView.qml"
    content: str = view_path.read_text(encoding="utf-8")
    for insp in ("CommandInspector", "SkillInspector", "ImageInspector"):
        _check_persisted_width_binding(insp, content)
        _check_width_save_handler(insp, content)
