"""Contract tests for keyboard-operable project reordering.

Pins the ProjectReorderDialog keyboard path (Alt/Ctrl+Up/Down moves,
focus retention across model rebuilds, ListItem AT naming, focus
indicator) so the drag-only regression cannot silently return.
Text contracts only; no QML engine instantiation.
"""

from __future__ import annotations

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)
DIALOG = (QML_DIR / "dialogs" / "ProjectReorderDialog.qml").read_text(encoding="utf-8")


def test_delegate_row_is_tab_focusable():
    assert "activeFocusOnTab: true" in DIALOG


def test_keyboard_move_uses_alt_or_ctrl_with_arrows():
    assert "Qt.AltModifier | Qt.ControlModifier" in DIALOG
    assert "Qt.Key_Up" in DIALOG
    assert "Qt.Key_Down" in DIALOG
    assert "root.moveProject(delegateWrapper.index, -1)" in DIALOG
    assert "root.moveProject(delegateWrapper.index, 1)" in DIALOG
    assert "event.accepted = false" in DIALOG


def test_move_helper_clamps_and_defers():
    assert "property int pendingFocusIndex: -1" in DIALOG
    assert "function moveProject(fromIdx: int, delta: int)" in DIALOG
    assert "Qt.callLater(AppController.reorderProjects, fromIdx, toIdx)" in DIALOG


def test_focus_restored_after_model_rebuild():
    assert "root.pendingFocusIndex = toIdx" in DIALOG
    assert "delegateWrapper.forceActiveFocus()" in DIALOG


def test_row_exposes_listitem_name_with_position():
    assert "Accessible.role: Accessible.ListItem" in DIALOG
    assert '" of " + projectList.count' in DIALOG
    assert "Alt Up or Alt Down" in DIALOG


def test_focus_indicator_and_instructions():
    assert "delegateWrapper.activeFocus" in DIALOG
    assert "Alt+" in DIALOG
