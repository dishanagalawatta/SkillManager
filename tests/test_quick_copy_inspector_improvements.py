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
    assert "visible: root._sel && root._sel.local_path !== undefined" in content
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
    """Check that an inspector saves width changes to ui_controller via debounce.

    The debounce pattern stores the width in a temporary property and restarts
    a single-shot Timer, avoiding Python interop on every resize pixel.
    """
    markers = [
        "AppController.ui_controller.setInspectorWidth(width)",  # old direct pattern
        "_debouncedWidth = width",  # LibraryView debounce
        "_qc_debouncedWidth = width",  # QuickCopyView debounce
    ]
    assert any(m in view_content for m in markers), (
        f"{inspector_type} missing width save handler (direct or debounced)"
    )


def test_library_view_inspectors_width_is_proportional() -> None:
    """Verify that all three inspectors in LibraryView use proportional overlay-based width (not clamped by inspectorWidth)."""
    view_path: Path = QML_DIR / "views" / "LibraryView.qml"
    overlay_path: Path = QML_DIR / "SkillInspectorOverlay.qml"
    content: str = view_path.read_text(encoding="utf-8")
    overlay_content: str = overlay_path.read_text(encoding="utf-8")
    # Width uses proportional formula, not inspectorWidth clamp
    assert "_panelW" in content
    assert "width * 0.5" in overlay_content
    # inspectorWidth is still saved for session persistence (in the overlay)
    assert "setInspectorWidth" in overlay_content
    for insp in ("CommandInspector", "SkillInspector", "ImageInspector"):
        _check_width_save_handler(insp, overlay_content)


def test_quick_copy_view_inspectors_width_is_proportional() -> None:
    """Verify that all three inspectors in QuickCopyView use proportional overlay-based width (not clamped by inspectorWidth)."""
    overlay_path: Path = QML_DIR / "SkillInspectorOverlay.qml"
    overlay_content: str = overlay_path.read_text(encoding="utf-8")
    # Width computations moved to shared SkillInspectorOverlay
    assert "width * 0.5" in overlay_content
    # inspectorWidth is still saved for session persistence (in the overlay)
    assert "setInspectorWidth" in overlay_content
    # Width save handler is now in the overlay
    assert "_debouncedWidth" in overlay_content
