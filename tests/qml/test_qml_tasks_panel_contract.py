"""QML contract for the per-project task panel in the Quick Copy view."""

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return QML_DIR.joinpath(*parts).read_text(encoding="utf-8")


def test_tasks_panel_is_registered():
    qmldir = _read("qmldir")
    assert "ProjectTasksPanel 1.0 views/ProjectTasksPanel.qml" in qmldir
    assert (QML_DIR / "views" / "ProjectTasksPanel.qml").exists()


def test_quick_copy_hosts_the_tasks_panel():
    """The panel sits next to the skill list and follows the active project."""
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
    """Header, quick-add, filters, carry and clear-done are all present."""
    panel = _read("views", "ProjectTasksPanel.qml")

    # Header + counters
    assert '"Tasks — "' in panel
    assert "root.openCount" in panel
    assert "root.doneCount" in panel
    # Filters
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
    # Row actions
    assert "AppController.toggleProjectTask(" in panel
    assert "AppController.updateProjectTask(" in panel
    assert "AppController.deleteProjectTask(" in panel
    assert "AppController.copyTaskAsPrompt(" in panel


def test_panel_is_accessible():
    """Every interactive task control carries an accessible role and name."""
    panel = _read("views", "ProjectTasksPanel.qml")

    assert "Accessible.role: Accessible.CheckBox" in panel
    assert "Accessible.role: Accessible.PageTab" in panel
    assert "Accessible.role: Accessible.EditableText" in panel
    assert "Accessible.name:" in panel


def test_panel_uses_theme_tokens_only():
    """The panel must not hardcode colours or metrics."""
    panel = _read("views", "ProjectTasksPanel.qml")

    assert "#" not in panel.replace("# ", ""), "hardcoded colour found in the tasks panel"
