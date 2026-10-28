"""QML contract for the shared side-panel shell and its building blocks.

Every right-hand panel in the app must look and behave identically.  Before
this refactor only the inspector panels were resize/close capable; the Quick
Copy task list was an inline ``RowLayout`` child with a fixed 340 px width.
These tests pin the shared shell so the next panel cannot fork the behaviour
again.
"""

from __future__ import annotations

import re
from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return QML_DIR.joinpath(*parts).read_text(encoding="utf-8")


def _strip_comments(text: str) -> str:
    """Drop comments so prose cannot satisfy (or break) a code assertion."""
    without_block = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", without_block)


def _assert_no_hardcoded_colour(text: str, name: str) -> None:
    assert "#" not in _strip_comments(text), f"hardcoded colour literal in {name}"


# ── Registration ────────────────────────────────────────────────────


def test_side_panel_parts_are_registered():
    """New shared components must be importable from the QML module."""
    qmldir = _read("qmldir")

    for entry, path in (
        ("SidePanel", "SidePanel.qml"),
        ("PanelResizeHandle", "PanelResizeHandle.qml"),
        ("SegmentedFilter", "SegmentedFilter.qml"),
        ("TaskItem", "TaskItem.qml"),
    ):
        assert f"{entry} 1.0 {path}" in qmldir
        assert (QML_DIR / path).exists(), f"{path} is registered but missing"


# ── Shared shell ────────────────────────────────────────────────────


def test_side_panel_is_a_generic_item_shell():
    """The shell is slot-based, so hosts only supply content."""
    panel = _strip_comments(_read("SidePanel.qml"))

    assert "default property alias content:" in panel
    for declaration in (
        "property string title",
        "property string badgeText",
        "property string widthKey",
        "property bool open",
        "property bool resizable",
        "property bool showClose",
        "property int preferredWidth",
        "property int minimumPanelWidth",
        "property real topMargin",
        "signal closeRequested()",
    ):
        assert declaration in panel, f"SidePanel must expose {declaration!r}"


def test_side_panel_owns_the_panel_chrome():
    """Chrome lives in one place so panels stop re-declaring it."""
    panel = _strip_comments(_read("SidePanel.qml"))

    assert "radius: Theme.radiusCard" in panel
    assert "color: Theme.glassPill" in panel
    assert "border.color: Theme.glassBorder" in panel
    assert "anchors.margins: 16" in panel
    _assert_no_hardcoded_colour(_read("SidePanel.qml"), "SidePanel.qml")


def test_side_panel_has_a_close_affordance():
    """Panels are dismissable from inside, like the inspector panels."""
    panel = _read("SidePanel.qml")

    assert 'objectName: "sidePanelClose"' in panel
    assert "close-icon.svg" in panel
    assert "root.closeRequested()" in panel


def test_side_panel_persists_its_width():
    """A resized panel must survive a restart, like the inspector does."""
    panel = _strip_comments(_read("SidePanel.qml"))

    assert "AppController.ui_controller.getPanelWidth(root.widthKey)" in panel
    assert "AppController.ui_controller.setPanelWidth(root.widthKey" in panel
    assert "Timer {" in panel, "width writes must be debounced"
    # Clamp so a drag cannot collapse or explode the panel.
    assert "Math.max(root.minimumPanelWidth" in panel


def test_side_panel_respects_reduced_motion():
    """Animations are opt-out through the existing accessibility setting."""
    panel = _strip_comments(_read("SidePanel.qml"))

    assert "ui_controller.reducedMotion" in panel


def test_side_panel_does_not_steal_the_escape_shortcut():
    """Main.qml owns Esc (clear selection); a second one is ambiguous."""
    panel = _strip_comments(_read("SidePanel.qml"))

    assert "Shortcut {" not in panel
    assert "Qt.Key_Escape" not in panel


# ── Resize affordance ───────────────────────────────────────────────


def test_resize_handle_is_the_single_drag_implementation():
    handle = _strip_comments(_read("PanelResizeHandle.qml"))

    assert "signal widthEdited(int width)" in handle
    assert "signal widthCommitted(int width)" in handle
    assert "Qt.SizeHorCursor" in handle
    assert "Accessible.ignored: true" in handle
    _assert_no_hardcoded_colour(_read("PanelResizeHandle.qml"), "PanelResizeHandle.qml")


def test_inspector_overlay_reuses_the_shared_resize_handle():
    """No second copy of the drag maths is allowed to reappear."""
    overlay = _strip_comments(_read("SkillInspectorOverlay.qml"))

    assert "PanelResizeHandle {" in overlay
    assert "Qt.SizeHorCursor" not in overlay, "inline resize mouse area still present"


# ── Reusable content pieces ─────────────────────────────────────────


def test_segmented_filter_is_generic():
    """The All/Active/Done control must serve any tab-like filter."""
    filter_qml = _strip_comments(_read("SegmentedFilter.qml"))

    assert "property var options" in filter_qml
    assert "property string currentKey" in filter_qml
    assert "property string groupName" in filter_qml
    assert "signal activated(string key)" in filter_qml
    assert "Accessible.PageTab" in filter_qml
    assert "Qt.Key_Space" in filter_qml
    assert "Qt.Key_Return" in filter_qml
    _assert_no_hardcoded_colour(_read("SegmentedFilter.qml"), "SegmentedFilter.qml")


def test_task_item_is_a_self_contained_row():
    """The row owns its edit buffer and reports intent through signals."""
    item = _strip_comments(_read("TaskItem.qml"))

    assert "property var task" in item
    assert "property bool editing" in item
    for signal in (
        "signal toggled(string taskId)",
        "signal editRequested(string taskId)",
        "signal deleteRequested(string taskId)",
        "signal copyRequested(string taskId)",
        "signal saveRequested(string taskId, string title, string description)",
        "signal editCancelled()",
    ):
        assert signal in item, f"TaskItem must expose {signal!r}"
    assert "Accessible.CheckBox" in item
    _assert_no_hardcoded_colour(_read("TaskItem.qml"), "TaskItem.qml")


# ── Composed panel ──────────────────────────────────────────────────


def test_tasks_panel_composes_the_shared_shell():
    panel = _strip_comments(_read("views", "ProjectTasksPanel.qml"))

    assert "SidePanel {" in panel
    assert 'widthKey: "quickcopy.tasks"' in panel
    assert "SegmentedFilter {" in panel
    assert "TaskItem {" in panel
    # The panel must not paint its own chrome anymore.
    assert "color: Theme.glassPill" not in panel
    assert "anchors.margins: 12" not in panel


def test_quick_copy_hosts_the_panel_as_an_overlay():
    """The list keeps its full width; the panel floats like the inspectors."""
    quick_copy = _read("views", "QuickCopyView.qml")
    start = quick_copy.index("ProjectTasksPanel {")
    block = quick_copy[start : quick_copy.index("SkillInspectorOverlay {")]

    assert "anchors.fill: parent" in block
    assert "open: AppController.ui_controller.tasksPanelOpen" in block
    assert "topMargin:" in block
    assert "Layout.preferredWidth" not in block, "panel is still an inline layout child"


# ── Editing safety ──────────────────────────────────────────────────


def test_panel_drops_an_edit_in_flight_when_the_project_changes():
    """An edit buffer must never be saved into a different project."""
    panel = _strip_comments(_read("views", "ProjectTasksPanel.qml"))

    assert 'onProjectPathChanged: root.editingId = ""' in panel
    assert "onOpenChanged:" in panel
    # The delegate only enters edit mode for the row the panel is editing.
    assert 'root.editingId !== "" && root.editingId === modelData.id' in panel


def test_panel_guards_against_a_null_task_list():
    """`currentProjectTasks` is a loose var; a null must not break bindings.

    ``QVariantList`` properties reach QML as a *sequence* object, not a JS
    array: ``Array.isArray()`` is false for them while ``.length`` and
    ``.filter()`` work.  An array check therefore silently emptied the panel.
    """
    panel = _strip_comments(_read("views", "ProjectTasksPanel.qml"))

    assert "Array.isArray" not in panel
    assert 'typeof list.length === "number"' in panel
    assert "root.tasks.filter(" not in panel
    assert "root.tasks.length" not in panel


def test_panel_counts_match_the_rendered_rows():
    """Header badge and body must read the same list, or they can disagree."""
    panel = _strip_comments(_read("views", "ProjectTasksPanel.qml"))

    assert "readonly property int openCount:" in panel
    assert "readonly property int doneCount:" in panel
    assert "AppController.task_controller.activeTaskCount" not in panel
    assert "AppController.task_controller.completedTaskCount" not in panel
