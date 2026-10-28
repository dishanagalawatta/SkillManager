import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

/*!
    \qmltype TaskItem
    \inqmlmodule SkillManagerComponents
    \brief One row of a project task list, including its inline editor.

    Extracted from the task panel delegate so the row is reusable and the panel
    stays readable. The row owns only its own edit buffer; every mutation is
    reported as intent and performed by the owner, which keeps persistence in
    the controller.

    \property var task
        The task record (``id``, ``title``, ``description``, ``completed``,
        ``priority``).
    \property bool editing
        Renders the inline title/notes editor instead of the read-only summary.
*/
Item {
    id: root

    property var task: null
    property bool editing: false

    readonly property string taskId: root.task ? (root.task.id || "") : ""
    readonly property string taskTitle: root.task ? (root.task.title || "") : ""
    readonly property string taskDescription: root.task ? (root.task.description || "") : ""
    readonly property bool completed: root.task ? root.task.completed === true : false
    readonly property string priority: root.task ? (root.task.priority || "medium") : "medium"

    signal toggled(string taskId)
    signal editRequested(string taskId)
    signal deleteRequested(string taskId)
    signal copyRequested(string taskId)
    signal saveRequested(string taskId, string title, string description)
    signal editCancelled()

    function _priorityColor(value) {
        if (value === "high") return Theme.danger
        if (value === "low") return Theme.secondaryLabel
        return Theme.accent
    }

    height: layout.implicitHeight + 12
    activeFocusOnTab: true

    onEditingChanged: {
        if (!root.editing) return
        editTitleField.text = root.taskTitle
        editDescriptionField.text = root.taskDescription
    }

    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
            root.toggled(root.taskId)
            event.accepted = true
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: 2
        anchors.rightMargin: 2
        radius: Theme.radiusSmall
        color: rowHover.hovered ? Theme.glassActive : "transparent"
        border.color: root.editing ? Theme.accent : "transparent"
        border.width: root.editing ? 1 : 0
    }

    HoverHandler {
        id: rowHover
    }

    ColumnLayout {
        id: layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 6
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Completion checkbox
            Rectangle {
                id: checkTarget
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                radius: 9
                color: root.completed ? Theme.accent : "transparent"
                border.color: root.completed ? Theme.accent
                    : (checkTarget.activeFocus ? Theme.accent : Theme.glassBorder)
                border.width: root.completed || checkTarget.activeFocus ? 2 : 1
                activeFocusOnTab: true

                Accessible.role: Accessible.CheckBox
                Accessible.checkable: true
                Accessible.checked: root.completed
                Accessible.name: (root.completed ? "Mark open: " : "Mark done: ")
                    + root.taskTitle

                Text {
                    anchors.centerIn: parent
                    text: "✓"
                    color: "white"
                    font.pixelSize: 11
                    visible: root.completed
                }

                TapHandler {
                    onTapped: root.toggled(root.taskId)
                }
                Keys.onPressed: (event) => {
                    if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
                        root.toggled(root.taskId)
                        event.accepted = true
                    }
                }
            }

            // Priority dot
            Rectangle {
                Layout.preferredWidth: 8
                Layout.preferredHeight: 8
                radius: 4
                color: root._priorityColor(root.priority)
            }

            // Title (read-only) / title editor
            Text {
                Layout.fillWidth: true
                text: root.taskTitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: Font.Medium
                color: root.completed ? Theme.secondaryLabel : Theme.label
                font.strikeout: root.completed
                elide: Text.ElideRight
                visible: !root.editing
            }

            TextField {
                id: editTitleField
                Layout.fillWidth: true
                visible: root.editing
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

            // Quick actions — shown on hover or keyboard focus so the title
            // keeps the full row width. Qt resolves the tab chain lazily on
            // each Tab press, so the buttons are reachable once this row (or
            // the pointer) reveals them; keeping them permanently focusable
            // would add three tab stops to every row in a long list.
            RowLayout {
                spacing: 2
                visible: rowHover.hovered || root.activeFocus

                IconButton {
                    buttonSize: 24
                    iconSize: 14
                    flat: true
                    iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
                    tooltipText: "Copy for Agent"
                    accessibleName: "Copy task for the agent"
                    onClicked: root.copyRequested(root.taskId)
                }
                IconButton {
                    buttonSize: 24
                    iconSize: 14
                    flat: true
                    iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
                    tooltipText: "Edit task"
                    accessibleName: "Edit task"
                    onClicked: root.editRequested(root.taskId)
                }
                IconButton {
                    buttonSize: 24
                    iconSize: 14
                    flat: true
                    iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                    tooltipText: "Delete task"
                    accessibleName: "Delete task"
                    onClicked: root.deleteRequested(root.taskId)
                }
            }
        }

        // Description (read-only) / notes editor
        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 26
            text: root.taskDescription
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            color: Theme.secondaryLabel
            wrapMode: Text.WordWrap
            visible: root.taskDescription !== "" && !root.editing
        }

        TextArea {
            id: editDescriptionField
            Layout.fillWidth: true
            Layout.leftMargin: 26
            visible: root.editing
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
            visible: root.editing

            ActionButton {
                role: "primary"
                labelText: "Save"
                accessibleName: "Save task changes"
                buttonHeight: 26
                onClicked: root.saveRequested(
                    root.taskId, editTitleField.text, editDescriptionField.text)
            }
            ActionButton {
                role: "secondary"
                labelText: "Cancel"
                accessibleName: "Cancel editing the task"
                buttonHeight: 26
                onClicked: root.editCancelled()
            }
        }
    }
}
