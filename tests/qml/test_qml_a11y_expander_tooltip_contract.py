"""Contract tests for the PR #280/#278 accessibility consolidation.

Pins the ADR-0031 expander pattern (CheckBox + checkable/checked + both
handlers) and the keyboard-focus tooltip pattern (explicit visible binding,
IconButton.tooltipText instead of nested SleekToolTip) so regressions are
caught as text contracts without instantiating the QML engine.
"""

from __future__ import annotations

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(rel: str) -> str:
    return (QML_DIR / rel).read_text(encoding="utf-8")


def test_missing_skills_expand_toggle_is_checkbox_with_handlers():
    text = _read("dialogs/MissingSkillsDialog.qml")
    assert "Accessible.role: Accessible.CheckBox" in text
    assert "Accessible.checkable: true" in text
    assert "Accessible.checked: modelData.detailsExpanded" in text
    assert "Accessible.onPressAction: root.toggleDetails(index)" in text
    assert "Accessible.onToggleAction: root.toggleDetails(index)" in text


def test_skill_item_tooltips_surface_on_keyboard_focus():
    text = _read("SkillItem.qml")
    assert "visible: subCatHover.hovered || subHeader.activeFocus" in text
    assert "visible: checkboxHover.hovered || checkboxRect.activeFocus" in text


def test_skill_item_delete_uses_native_tooltip_text():
    text = _read("SkillItem.qml")
    assert 'tooltipText: "Delete "' in text
    delete_block = text.split("id: deleteBtn", 1)[1].split("Accessible.", 1)[0]
    assert "SleekToolTip" not in delete_block


def test_sidebar_collapse_toggle_is_checkbox_with_handlers():
    text = _read("Sidebar.qml")
    assert "Accessible.role: Accessible.CheckBox" in text
    assert "Accessible.checked: !root.isCollapsed" in text
    assert "Accessible.onPressAction: root.isCollapsed = !root.isCollapsed" in text
    assert "Accessible.onToggleAction: root.isCollapsed = !root.isCollapsed" in text


def test_zoom_preset_has_accessible_button():
    text = _read("ImageInspector.qml")
    assert 'Accessible.name: "Set zoom to " + modelData + "%"' in text
    assert "Accessible.role: Accessible.Button" in text


def test_dialog_and_overflow_buttons_expose_tooltips():
    for rel, needle in [
        ("dialogs/MissingSkillsDialog.qml", 'tooltipText: "Copy details to clipboard"'),
        ("dialogs/PackageEditDialog.qml", 'tooltipText: "Choose folder"'),
        ("views/LibraryView.qml", 'tooltipText: "More actions"'),
        ("views/QuickCopyView.qml", 'tooltipText: "More actions"'),
        ("views/UpdatesView.qml", 'tooltipText: "Close Inspector"'),
        ("GlassDialog.qml", 'tooltipText: "Close"'),
    ]:
        assert needle in _read(rel), f"{rel} missing {needle}"
    for rel in [
        "dialogs/ArchiveConfirmDialog.qml",
        "dialogs/CommandCarrySkillsDialog.qml",
        "dialogs/CommandCreateDialog.qml",
        "dialogs/ProjectRenameDialog.qml",
        "dialogs/ProjectReorderDialog.qml",
    ]:
        assert 'tooltipText: "Close"' in _read(rel), f"{rel} missing Close tooltip"
