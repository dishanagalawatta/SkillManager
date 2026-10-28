/**
 * Purpose: Per-project task list for the Quick Copy workspace.
 * Usage:
 *   ProjectTasksPanel {
 *       anchors.fill: parent
 *       topMargin: headerRow.height
 *       open: AppController.ui_controller.tasksPanelOpen
 *       projectPath: "..."
 *       projectName: "My Project"
 *   }
 *
 * The panel renders inside the shared ``SidePanel`` shell, so it is a
 * right-anchored, resizable, closable overlay with a persisted width — the
 * same behaviour as the inspector side panels. Only the body is task-specific:
 * the filter tabs (``SegmentedFilter``), the task rows (``TaskItem``) and the
 * inline ``TaskComposer`` footer that replaces the old one-line quick-add pill.
 *
 * The panel lists the tasks of ONE project. An empty project path means
 * "no project selected" and renders the "select a project" empty state.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

SidePanel {
    id: root

    // ── Public state ─────────────────────────────────────────────────
    property string projectPath: ""
    property string projectName: ""
    property var tasks: AppController.task_controller.currentProjectTasks
    property string filter: "all" // all | active | done
    property string editingId: ""

    // Drafts are kept per project so switching project (or closing the panel)
    // never throws away a half-written task, and never leaks it into another
    // project either.
    property var _drafts: ({})
    property string _draftKey: ""

    // ── Derived ──────────────────────────────────────────────────────
    // `tasks` comes from the controller as a loose `var`; a null while the
    // controller is still booting must not throw inside a binding.
    // NOTE: a `QVariantList` property surfaces in QML as a sequence object
    // (`[object V4Sequence]`), for which `Array.isArray()` is false even
    // though `.length`/`.filter()` work. Duck-type instead of array-testing.
    readonly property var _taskList: {
        var list = root.tasks
        return (list && typeof list.length === "number") ? list : []
    }
    readonly property var visibleTasks: {
        if (root.filter === "active") {
            return root._taskList.filter(function(t) { return !t.completed })
        }
        if (root.filter === "done") {
            return root._taskList.filter(function(t) { return t.completed })
        }
        return root._taskList
    }
    // Counts are derived from the same list the rows come from, so the header
    // badge can never disagree with the panel body.
    readonly property int openCount:
        root._taskList.filter(function(t) { return !t.completed }).length
    readonly property int doneCount:
        root._taskList.filter(function(t) { return t.completed }).length

    // ── Shell configuration ──────────────────────────────────────────
    title: root.projectName ? "Tasks — " + root.projectName : "Tasks"
    badgeText: root.openCount + " Open · " + root.doneCount + " Done"
    widthKey: "quickcopy.tasks"
    preferredWidth: 360
    minimumPanelWidth: 300

    onCloseRequested: AppController.ui_controller.setTasksPanelOpen(false)

    // An edit in flight belongs to the project that started it. Switching
    // project (or closing the panel) drops the buffer instead of letting it
    // be written into a different project's task list.
    onProjectPathChanged: {
        root.editingId = ""
        if (root._draftKey !== "") root._saveDraft(root._draftKey)
        root._draftKey = root.projectPath
        root._loadDraft(root.projectPath)
    }
    onOpenChanged: {
        if (!root.open) root.editingId = ""
    }

    // ── Filter row ───────────────────────────────────────────────────
    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        SegmentedFilter {
            objectName: "taskFilterTabs"
            groupName: "Task filter"
            currentKey: root.filter
            options: [
                { key: "all", label: "All" },
                { key: "active", label: "Active" },
                { key: "done", label: "Done" }
            ]
            onActivated: (key) => root.filter = key
        }

        Item { Layout.fillWidth: true }

        ActionButton {
            role: "secondary"
            labelText: "Clear Done"
            accessibleName: "Clear Done — remove every completed task"
            buttonHeight: 26
            enabled: root.doneCount > 0
            onClicked: AppController.clearCompletedProjectTasks(root.projectPath)
        }
    }

    // ── Task list + inline composer ──────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        radius: Theme.radiusSmall
        color: Theme.glassHover
        border.color: Theme.glassBorder
        border.width: 1
        clip: true

        ListView {
            id: taskList
            anchors.fill: parent
            anchors.margins: 6
            anchors.bottomMargin: composer.visible ? composer.height + 12 : 6
            clip: true
            spacing: 4
            model: root.visibleTasks
            boundsBehavior: Flickable.StopAtBounds

            // Empty states
            ColumnLayout {
                anchors.centerIn: parent
                width: parent.width - 24
                spacing: 8
                visible: taskList.count === 0

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: root.projectPath === ""
                        ? "Select a project above to manage its tasks."
                        : root.filter === "done"
                            ? "No completed tasks yet."
                            : root._taskList.length === 0
                                ? "No tasks yet — write the first one below."
                                : "Nothing to show in this filter."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.secondaryLabel
                    wrapMode: Text.WordWrap
                }
            }

            delegate: TaskItem {
                required property var modelData
                required property int index

                width: taskList.width
                task: modelData
                editing: root.editingId !== "" && root.editingId === modelData.id

                onToggled: (taskId) => AppController.toggleProjectTask(
                    root.projectPath, taskId)
                onCopyRequested: (taskId) => AppController.copyTaskAsPrompt(
                    root.projectPath, taskId)
                onDeleteRequested: (taskId) => AppController.deleteProjectTask(
                    root.projectPath, taskId)
                onEditRequested: (taskId) => root.editingId = taskId
                onEditCancelled: root.editingId = ""
                onSaveRequested: (taskId, title, description) => {
                    AppController.updateProjectTask(
                        root.projectPath, taskId, title, description, modelData.priority)
                    root.editingId = ""
                }
            }
        }

        // The composer sits where the task will land: a footer inside the
        // same box as the list, not a detached pill above it.
        TaskComposer {
            id: composer
            objectName: "taskComposer"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 6
            visible: root.projectPath !== ""
            projectPath: root.projectPath

            onSubmitted: (title, notes, priority, attachments) => {
                var added = AppController.addProjectTask(
                    root.projectPath, title, priority, notes, attachments)
                if (!added) return
                root._drafts[root.projectPath] = null
                composer.reset()
                composer.focusEditor()
            }
            onCancelled: {
                composer.reset()
                root._drafts[root.projectPath] = null
                composer.focusEditor()
            }
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────
    function _saveDraft(projectPath) {
        if (!projectPath || !composer) return
        var draft = {
            text: composer.text,
            priority: composer.priority,
            attachments: (composer.attachments || []).slice()
        }
        if (draft.text.trim() === "" && draft.attachments.length === 0) {
            root._drafts[projectPath] = null
            return
        }
        root._drafts[projectPath] = draft
    }

    function _loadDraft(projectPath) {
        if (!composer) return
        composer.reset()
        if (!projectPath) return
        var draft = root._drafts[projectPath]
        if (!draft) return
        composer.text = draft.text || ""
        composer.priority = draft.priority || "medium"
        composer.attachments = (draft.attachments || []).slice()
    }
}
