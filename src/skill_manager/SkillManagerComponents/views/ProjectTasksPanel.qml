/**
 * Purpose: Collapsible per-project task panel for the Quick Copy workspace.
 * Usage:
 *   ProjectTasksPanel {
 *       id: qcv_tasksPanel
 *       projectPath: "..."
 *       projectName: "My Project"
 *   }
 *
 * The panel lists the tasks of ONE project. An empty project path means
 * "no project selected" and renders the "select a project" empty state.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Rectangle {
    id: root

    // ── Public state ─────────────────────────────────────────────────
    property string projectPath: ""
    property string projectName: ""
    property var tasks: AppController.task_controller.currentProjectTasks
    property string filter: "all" // all | active | done
    property string pendingPriority: "medium"
    property string editingId: ""
    property string editingTitle: ""
    property string editingDescription: ""

    // ── Derived ──────────────────────────────────────────────────────
    readonly property var visibleTasks: {
        if (root.filter === "active") {
            return root.tasks.filter(function(t) { return !t.completed })
        }
        if (root.filter === "done") {
            return root.tasks.filter(function(t) { return t.completed })
        }
        return root.tasks
    }
    readonly property int openCount: AppController.task_controller.activeTaskCount
    readonly property int doneCount: AppController.task_controller.completedTaskCount

    color: Theme.glassPill
    radius: Theme.radiusCard
    border.color: Theme.glassBorder
    border.width: 1

    // ── Header ───────────────────────────────────────────────────────
    ColumnLayout {
        id: rootLayout
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // Title row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: root.projectName ? "Tasks — " + root.projectName : "Tasks"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: Font.DemiBold
                color: Theme.label
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            // Open / done counter
            Rectangle {
                Layout.preferredWidth: Math.max(24, counterText.implicitWidth + 14)
                Layout.preferredHeight: 22
                radius: 11
                color: Theme.glassHover
                border.color: Theme.glassBorder
                border.width: 1

                Text {
                    id: counterText
                    anchors.centerIn: parent
                    text: root.openCount + " Open · " + root.doneCount + " Done"
                    color: Theme.secondaryLabel
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                }
            }
        }

        // Filter row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // All / Active / Done
            RowLayout {
                spacing: 0

                Repeater {
                    model: [
                        { key: "all", label: "All" },
                        { key: "active", label: "Active" },
                        { key: "done", label: "Done" }
                    ]

                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool selected: root.filter === modelData.key

                        Layout.preferredWidth: filterText.implicitWidth + 20
                        Layout.preferredHeight: 26
                        radius: 13
                        color: selected ? Theme.accent : "transparent"
                        border.color: selected ? Theme.accent : Theme.glassBorder
                        border.width: 1
                        activeFocusOnTab: true

                        Accessible.role: Accessible.PageTab
                        Accessible.checked: selected
                        Accessible.name: modelData.label + " tasks"

                        Text {
                            id: filterText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent.selected ? "white" : Theme.secondaryLabel
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            font.weight: Font.Medium
                        }

                        TapHandler {
                            onTapped: root.filter = modelData.key
                        }
                        Keys.onPressed: (event) => {
                            if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
                                root.filter = modelData.key
                                event.accepted = true
                            }
                        }
                    }
                }
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

        // Quick-add row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: addInput
                Layout.fillWidth: true
                placeholderText: root.projectPath === ""
                    ? "Select a project to add tasks"
                    : "Add a task... (Enter to add)"
                enabled: root.projectPath !== ""
                Accessible.role: Accessible.EditableText
                Accessible.name: "Add a task"
                selectByMouse: true
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                placeholderTextColor: Theme.secondaryLabel
                leftPadding: 12
                rightPadding: 12
                topPadding: 8
                bottomPadding: 8
                background: Rectangle {
                    radius: Theme.radiusField
                    color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                    border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                    border.width: parent.activeFocus ? 2 : 1
                }
                onAccepted: root._addTask()
            }

            // Priority selector
            Rectangle {
                id: priorityPill
                Layout.preferredWidth: priorityText.implicitWidth + 20
                Layout.preferredHeight: 30
                radius: 15
                color: priorityHover.hovered || priorityPill.activeFocus ? Theme.glassHover : "transparent"
                border.color: Theme.glassBorder
                border.width: 1
                activeFocusOnTab: true

                Accessible.role: Accessible.Button
                Accessible.name: "Priority: " + root.pendingPriority

                Text {
                    id: priorityText
                    anchors.centerIn: parent
                    text: root.pendingPriority === "low" ? "Low"
                        : root.pendingPriority === "high" ? "High" : "Med"
                    color: root.pendingPriority === "high" ? Theme.danger
                        : root.pendingPriority === "low" ? Theme.secondaryLabel : Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                    font.weight: Font.Medium
                }

                HoverHandler {
                    id: priorityHover
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    onTapped: {
                        root.pendingPriority = root.pendingPriority === "low" ? "medium"
                            : root.pendingPriority === "medium" ? "high" : "low"
                    }
                }
                Keys.onPressed: (event) => {
                    if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
                        root.pendingPriority = root.pendingPriority === "low" ? "medium"
                            : root.pendingPriority === "medium" ? "high" : "low"
                        event.accepted = true
                    }
                }
            }
        }

        // Task list
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
                                : root.tasks.length === 0
                                    ? "No tasks yet — add your first one above."
                                    : "Nothing to show in this filter."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        color: Theme.secondaryLabel
                        wrapMode: Text.WordWrap
                    }
                }

                delegate: Item {
                    id: taskRow
                    required property var modelData
                    required property int index

                    readonly property var task: modelData
                    readonly property bool isEditing: root.editingId === task.id

                    width: taskList.width
                    height: taskCol.implicitHeight + 12
                    activeFocusOnTab: true

                    Rectangle {
                        anchors.fill: parent
                        anchors.leftMargin: 2
                        anchors.rightMargin: 2
                        radius: Theme.radiusSmall
                        color: rowHover.hovered ? Theme.glassActive : "transparent"
                        border.color: taskRow.isEditing ? Theme.accent : "transparent"
                        border.width: taskRow.isEditing ? 1 : 0
                    }

                    HoverHandler {
                        id: rowHover
                    }

                    ColumnLayout {
                        id: taskCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 6
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            // Checkbox
                            Rectangle {
                                Layout.preferredWidth: 18
                                Layout.preferredHeight: 18
                                radius: 9
                                color: taskRow.task.completed ? Theme.accent : "transparent"
                                border.color: taskRow.task.completed ? Theme.accent
                                    : (checkFocus.activeFocus ? Theme.accent : Theme.glassBorder)
                                border.width: taskRow.task.completed || checkFocus.activeFocus ? 2 : 1
                                activeFocusOnTab: true
                                id: checkFocus

                                Accessible.role: Accessible.CheckBox
                                Accessible.checkable: true
                                Accessible.checked: taskRow.task.completed
                                Accessible.name: (taskRow.task.completed ? "Mark open: " : "Mark done: ")
                                    + taskRow.task.title

                                Text {
                                    anchors.centerIn: parent
                                    text: "✓"
                                    color: "white"
                                    font.pixelSize: 11
                                    visible: taskRow.task.completed
                                }

                                TapHandler {
                                    onTapped: AppController.toggleProjectTask(
                                        root.projectPath, taskRow.task.id)
                                }
                                Keys.onPressed: (event) => {
                                    if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
                                        AppController.toggleProjectTask(
                                            root.projectPath, taskRow.task.id)
                                        event.accepted = true
                                    }
                                }
                            }

                            // Priority dot
                            Rectangle {
                                Layout.preferredWidth: 8
                                Layout.preferredHeight: 8
                                radius: 4
                                color: taskRow.task.priority === "high" ? Theme.danger
                                    : taskRow.task.priority === "low" ? Theme.secondaryLabel
                                    : Theme.accent
                            }

                            // Title
                            Text {
                                Layout.fillWidth: true
                                text: taskRow.isEditing ? editTitleField.text : taskRow.task.title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                font.weight: Font.Medium
                                color: taskRow.task.completed ? Theme.secondaryLabel : Theme.label
                                font.strikeout: taskRow.task.completed
                                elide: Text.ElideRight
                                visible: !taskRow.isEditing
                            }

                            TextField {
                                id: editTitleField
                                Layout.fillWidth: true
                                visible: taskRow.isEditing
                                text: taskRow.task.title
                                Accessible.role: Accessible.EditableText
                                Accessible.name: "Edit task title"
                                selectByMouse: true
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                color: Theme.label
                                leftPadding: 8
                                rightPadding: 8
                                topPadding: 4
                                bottomPadding: 4
                                background: Rectangle {
                                    radius: Theme.radiusField
                                    color: Theme.glassActive
                                    border.color: Theme.accent
                                    border.width: 1
                                }
                            }

                            // Quick actions — shown on hover or keyboard focus so
                            // the task title keeps the full row width.
                            RowLayout {
                                spacing: 2
                                visible: rowHover.hovered || taskRow.activeFocus

                                IconButton {
                                    buttonSize: 24
                                    iconSize: 14
                                    flat: true
                                    iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
                                    tooltipText: "Copy for Agent"
                                    accessibleName: "Copy task for the agent"
                                    onClicked: AppController.copyTaskAsPrompt(
                                        root.projectPath, taskRow.task.id)
                                }
                                IconButton {
                                    buttonSize: 24
                                    iconSize: 14
                                    flat: true
                                    iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
                                    tooltipText: "Edit task"
                                    accessibleName: "Edit task"
                                    onClicked: {
                                        root.editingId = taskRow.task.id
                                        root.editingTitle = taskRow.task.title
                                        root.editingDescription = taskRow.task.description
                                    }
                                }
                                IconButton {
                                    buttonSize: 24
                                    iconSize: 14
                                    flat: true
                                    iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                                    tooltipText: "Delete task"
                                    accessibleName: "Delete task"
                                    onClicked: AppController.deleteProjectTask(
                                        root.projectPath, taskRow.task.id)
                                }
                            }
                        }

                        // Description / edit area
                        Text {
                            Layout.fillWidth: true
                            Layout.leftMargin: 26
                            text: taskRow.task.description
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            wrapMode: Text.WordWrap
                            visible: taskRow.task.description !== "" && !taskRow.isEditing
                        }

                        TextArea {
                            id: editDescField
                            Layout.fillWidth: true
                            Layout.leftMargin: 26
                            visible: taskRow.isEditing
                            text: taskRow.task.description
                            Accessible.role: Accessible.EditableText
                            Accessible.name: "Edit task notes"
                            selectByMouse: true
                            wrapMode: TextArea.Wrap
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.label
                            background: Rectangle {
                                radius: Theme.radiusField
                                color: Theme.glassActive
                                border.color: Theme.accent
                                border.width: 1
                            }
                        }

                        // Save / cancel (edit mode)
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: 26
                            spacing: 8
                            visible: taskRow.isEditing

                            ActionButton {
                                role: "primary"
                                labelText: "Save"
                                accessibleName: "Save task changes"
                                buttonHeight: 26
                                onClicked: {
                                    AppController.updateProjectTask(
                                        root.projectPath,
                                        taskRow.task.id,
                                        editTitleField.text,
                                        editDescField.text,
                                        taskRow.task.priority)
                                    root.editingId = ""
                                }
                            }
                            ActionButton {
                                role: "secondary"
                                labelText: "Cancel"
                                accessibleName: "Cancel editing the task"
                                buttonHeight: 26
                                onClicked: root.editingId = ""
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────
    function _addTask() {
        var title = addInput.text.trim()
        if (title === "" || root.projectPath === "") return
        AppController.addProjectTask(root.projectPath, title, root.pendingPriority, "")
        addInput.text = ""
    }
}
