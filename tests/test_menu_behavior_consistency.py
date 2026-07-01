# Purpose: Statically verify QML implementation contract for menu behavior consistency.
# Usage: Run via pytest: uv run pytest tests/test_menu_behavior_consistency.py

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


def test_skill_item_mouse_buttons_and_signals():
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")

    # Check that acceptedButtons is configured for Left and Right clicks
    assert "acceptedButtons: Qt.LeftButton | Qt.RightButton" in skill_item

    # Check that rightClicked signal is declared
    assert "signal rightClicked()" in skill_item

    # Check click handling logic for distinguishing Right and Left buttons
    assert "Qt.RightButton" in skill_item
    assert "rightClicked()" in skill_item


def test_library_view_behavior_contracts():
    library_view = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")

    # Check that onClicked toggles selection in LibraryView
    assert "toggleSelection(index)" in library_view

    # Check double-clicked only calls selectSkill and does NOT call clipboard copy
    # The old code had:
    # onClicked: (mouse) => {
    #     AppController.selectSkill(index)
    # }
    # onDoubleClicked: (mouse) => {
    #     AppController.selectSkill(index)
    #     AppController.copySkillToClipboard(model.path)
    # }

    # Ensure doubleClicked does not copy to clipboard in LibraryView
    assert "copySkillToClipboard" not in library_view

    # Check that rightClicked is handled in the delegate and triggers selectSkill
    assert "onRightClicked" in library_view
    assert "selectSkill(index)" in library_view


def test_quick_copy_view_behavior_contracts():
    quick_copy_view = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")

    # Ensure doubleClicked does not copy to clipboard in QuickCopyView
    # The old code had:
    # onDoubleClicked: (mouse) => {
    #     AppController.selectSkill(index)
    #     AppController.copySkillToClipboard(model.path)
    # }

    assert "copySkillToClipboard" not in quick_copy_view

    # Check that rightClicked is handled in the delegate and triggers selectSkill
    assert "onRightClicked" in quick_copy_view
    assert "selectSkill(index)" in quick_copy_view


def test_inspector_context_menus_disabled():
    import re

    skill_inspector = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    command_inspector = (QML_DIR / "CommandInspector.qml").read_text(encoding="utf-8")

    # Verify that in SkillInspector, TextField and TextArea have ContextMenu.menu: null
    assert re.search(r"id:\s*argField\s*\r?\n\s*ContextMenu\.menu:\s*null", skill_inspector) is not None
    assert re.search(r"id:\s*rawContentArea\s*\r?\n\s*ContextMenu\.menu:\s*null", skill_inspector) is not None

    # Verify that in CommandInspector, TextField and TextArea have ContextMenu.menu: null
    assert re.search(r"id:\s*nameField\s*\r?\n\s*ContextMenu\.menu:\s*null", command_inspector) is not None
    assert re.search(r"id:\s*bodyArea\s*\r?\n\s*ContextMenu\.menu:\s*null", command_inspector) is not None
