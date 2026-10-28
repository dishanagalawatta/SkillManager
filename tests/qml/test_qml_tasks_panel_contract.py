"""QML contract for the per-project task panel in the Quick Copy view.

The task list is composed from three files: the panel itself
(``views/ProjectTasksPanel.qml``), the reusable row (``TaskItem.qml``) and the
reusable filter tabs (``SegmentedFilter.qml``). The assertions below read the
whole surface so a control that moves to an extracted component keeps its
guarantee instead of silently disappearing.
"""

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return QML_DIR.joinpath(*parts).read_text(encoding="utf-8")


def _panel_surface() -> str:
    """Everything the task panel renders, wherever it now lives."""
    return "\n".join(
        _read(part)
        for part in (
            Path("views", "ProjectTasksPanel.qml"),
            Path("TaskItem.qml"),
            Path("SegmentedFilter.qml"),
        )
    )


def test_tasks_panel_is_registered():
    qmldir = _read("qmldir")
    assert "ProjectTasksPanel 1.0 views/ProjectTasksPanel.qml" in qmldir
    assert (QML_DIR / "views" / "ProjectTasksPanel.qml").exists()


def test_quick_copy_hosts_the_tasks_panel():
    """The panel follows the active project and its open state."""
    quick_copy = _read("views", "QuickCopyView.qml")

    assert "ProjectTasksPanel {" in quick_copy
    assert 'objectName: "projectTasksPanel"' in quick_copy
    assert "AppController.ui_controller.tasksPanelOpen" in quick_copy
    assert "projectPath: qcv_root._activeProjectPath" in quick_copy
    assert "projectName: AppController.currentProject" in quick_copy


def test_quick_copy_shows_the_open_task_badge():
    """The project selector carries a badge with the open task count."""
    quick_copy = _read("views", "QuickCopyView.qml")

    assert 'objectName: "projectTaskBadge"' in quick_copy
    assert "qcv_root._activeTaskCount" in quick_copy
    # The count must come from a notifying property, not a method call,
    # otherwise the badge never updates.
    assert "projectTaskCounts[" in quick_copy


def test_quick_copy_can_toggle_the_panel():
    quick_copy = _read("views", "QuickCopyView.qml")

    assert 'objectName: "tasksPanelToggle"' in quick_copy
    assert "AppController.ui_controller.setTasksPanelOpen(" in quick_copy


def test_panel_exposes_the_required_actions():
    """Title, counters, quick-add, filters, carry and clear-done are present."""
    panel = _read("views", "ProjectTasksPanel.qml")

    # Title + counters
    assert '"Tasks — "' in panel
    assert "root.openCount" in panel
    assert "root.doneCount" in panel
    # Filters (option data stays in the panel; rendering is generic)
    assert '{ key: "all", label: "All" }' in panel
    assert '{ key: "active", label: "Active" }' in panel
    assert '{ key: "done", label: "Done" }' in panel
    # Quick add
    assert "Add a task... (Enter to add)" in panel
    assert "AppController.addProjectTask(" in panel
    # Priority picker
    assert "root.pendingPriority" in panel
    # Clear done
    assert "AppController.clearCompletedProjectTasks(" in panel
    # Row actions (wired by the panel, rendered by TaskItem)
    surface = _panel_surface()
    assert "AppController.toggleProjectTask(" in panel
    assert "AppController.updateProjectTask(" in panel
    assert "AppController.deleteProjectTask(" in panel
    assert "AppController.copyTaskAsPrompt(" in panel
    assert "saveRequested" in surface
    assert "editRequested" in surface


def test_panel_is_accessible():
    """Every interactive task control carries an accessible role and name."""
    surface = _panel_surface()

    assert "Accessible.role: Accessible.CheckBox" in surface
    assert "Accessible.role: Accessible.PageTab" in surface
    assert "Accessible.role: Accessible.EditableText" in surface
    assert "Accessible.name:" in surface


def test_panel_uses_theme_tokens_only():
    """The panel must not hardcode colours or metrics."""
    surface = _panel_surface()

    assert "#" not in surface.replace("# ", ""), "hardcoded colour in the tasks panel"
