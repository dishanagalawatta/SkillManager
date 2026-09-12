"""Contract tests for GlassMultiSelect single-tab-stop rows.

Pins the roving-tabindex design: each row is the one focusable CheckBox
(AT role, checked state, both handlers, keyboard toggle, focus ring)
while the inner GlassCheckBox instances are removed from the tab order.
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
TEXT = (QML_DIR / "GlassMultiSelect.qml").read_text(encoding="utf-8")


def test_rows_are_the_only_tab_stops():
    # Closed control + select-all row + item delegate template are focusable;
    # both inner GlassCheckBox instances are removed from the tab order.
    assert TEXT.count("activeFocusOnTab: true") == 3
    assert TEXT.count("activeFocusOnTab: false") == 2  # allCheck + itemCheck


def test_select_all_row_carries_checkbox_contract():
    assert "Accessible.checked: root.allSelected" in TEXT
    assert "Accessible.onPressAction: allCheck.toggled()" in TEXT
    assert "Accessible.onToggleAction: allCheck.toggled()" in TEXT
    assert "+ root.allLabel" in TEXT


def test_item_row_carries_checkbox_contract():
    assert "Accessible.checked: root.selectedValues.indexOf(delegateRoot.modelData) >= 0" in TEXT
    assert "Accessible.onPressAction: itemCheck.toggled()" in TEXT
    assert "Accessible.onToggleAction: itemCheck.toggled()" in TEXT


def test_rows_toggle_by_keyboard_and_show_focus():
    assert "allCheck.toggled()" in TEXT
    assert "itemCheck.toggled()" in TEXT
    assert "event.accepted = false" in TEXT
    assert "allRow.activeFocus" in TEXT
    assert "delegateRoot.activeFocus" in TEXT


def test_mouse_click_lands_focus_on_row():
    assert "allRow.forceActiveFocus()" in TEXT
    assert "delegateRoot.forceActiveFocus()" in TEXT


def test_programmatic_popup_and_focus_hooks():
    assert "function openPopup()" in TEXT
    assert "function focusRow(idx: int)" in TEXT
