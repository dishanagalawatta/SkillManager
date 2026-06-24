import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Rectangle {
    id: root

    property var skill: ({})
    property bool isCollapsed: false
    property var editDialog: null

    readonly property int targetWidth: {
        if (!root.skill || root.skill.local_path === undefined) return 0;
        if (isCollapsed) return 32;

        let dynamicWidth = parent ? parent.width * 0.5 : 400;
        return Math.min(800, Math.max(400, dynamicWidth));
    }

    signal closed()

    GlassMenu {
        id: inspectorContextMenu
        property var targetControl: null

        GlassMenuItem {
            text: "Copy"
            iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
            enabled: inspectorContextMenu.targetControl && inspectorContextMenu.targetControl.selectedText !== undefined && inspectorContextMenu.targetControl.selectedText.length > 0
            onTriggered: {
                if (inspectorContextMenu.targetControl) inspectorContextMenu.targetControl.copy()
            }
        }
        GlassMenuItem {
            text: "Select All"
            onTriggered: {
                if (inspectorContextMenu.targetControl) inspectorContextMenu.targetControl.selectAll()
            }
        }
    }

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    clip: true

    SmoothScrollView {
        id: mainScroll
        anchors.fill: parent
        anchors.margins: 4
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: mainScroll.width - 24
            height: Math.max(implicitHeight, mainScroll.height - 24)
            x: 12
            y: 12
            spacing: 16
            visible: !root.isCollapsed && root.skill.local_path !== undefined
            opacity: visible ? 1.0 : 0.0

            Behavior on opacity { NumberAnimation { duration: 200 } }

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TextField {
                    id: nameField
                    text: root.skill.name || ""
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                    background: Rectangle {
                        radius: Theme.radiusField
                        color: nameField.activeFocus ? Theme.glassHover : "transparent"
                        border.color: nameField.activeFocus ? Theme.glassBorder : "transparent"
                    }
                    selectByMouse: true
                    readOnly: true

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked: (mouse) => {
                            inspectorContextMenu.targetControl = nameField
                            inspectorContextMenu.popup()
                        }
                    }
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
                    flat: true
                    onClicked: (mouse) => {
                        if (root.editDialog) {
                            root.editDialog.openForEdit(root.skill)
                        }
                    }
                    visible: root.skill && root.skill.local_path !== undefined
                    SleekToolTip {
                        id: editCmdToolTip
                        text: "Edit settings"
                        visible: parent.hovered
                    }

                    Accessible.role: Accessible.Button
                    Accessible.name: "Edit settings"
                    Accessible.description: editCmdToolTip.text
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                    role: "destructive"
                    flat: true
                    onClicked: (mouse) => {
                        let holders = AppController.commandProjectsForPath(root.skill.local_path || "")
                        if (holders.length === 0) {
                            holders = [AppController.currentProject || ""]
                        }
                        deleteConfirmDialog.holderProjects = holders
                        deleteConfirmDialog.open()
                    }
                    visible: root.skill && root.skill.local_path !== undefined
                    SleekToolTip {
                        id: delCmdToolTip
                        text: "Delete command"
                        visible: parent.hovered
                    }

                    Accessible.role: Accessible.Button
                    Accessible.name: "Delete command"
                    Accessible.description: delCmdToolTip.text
                }

                IconButton {
                    text: "✕"
                    flat: true
                    onClicked: (mouse) => root.closed()
                    visible: root.skill && root.skill.local_path !== undefined
                    SleekToolTip {
                        id: closeCmdToolTip
                        text: "Close Inspector"
                        visible: parent.hovered
                    }

                    Accessible.role: Accessible.Button
                    Accessible.name: "Close Inspector"
                    Accessible.description: closeCmdToolTip.text
                }
            }

            // Command Details Section (editable)
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    radius: Theme.radiusSmall
                    color: Qt.rgba(0,0,0,0.2)
                    border.color: Theme.glassBorder
                    border.width: 1
                    clip: true

                    SmoothScrollView {
                        anchors.fill: parent
                        anchors.margins: 2
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        TextArea {
                            id: bodyArea
                            width: parent.width - parent.leftPadding - parent.rightPadding
                            Accessible.role: Accessible.EditableText
                            Accessible.name: "Command Details"
                            text: root.skill.body_content || ""
                            font.family: "Consolas", "Monaco", "Courier New", "monospace"
                            font.pixelSize: 12
                            color: Theme.label
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                            readOnly: true
                            background: null
                            padding: 12
                            verticalAlignment: TextArea.AlignTop

                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.RightButton
                                onClicked: (mouse) => {
                                    inspectorContextMenu.targetControl = bodyArea
                                    inspectorContextMenu.popup()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Collapse handle
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 32
        visible: root.isCollapsed
        color: "transparent"

        Text {
            anchors.centerIn: parent
            text: "›"
            rotation: 180
            font.pixelSize: 24
            color: Theme.secondaryLabel
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onClicked: (mouse) => root.isCollapsed = false
            cursorShape: Qt.PointingHandCursor

            SleekToolTip {
                id: expCmdToolTip
                text: "Expand Inspector"
                visible: parent.containsMouse
            }

            Accessible.role: Accessible.Button
            Accessible.name: "Expand Inspector"
        }
    }

    Behavior on width {
        NumberAnimation { duration: 300; easing.type: Easing.OutQuart }
    }

    Behavior on anchors.leftMargin {
        NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
    }

    // Delete confirmation with project checklist
    Dialog {
        id: deleteConfirmDialog
        title: "Delete Command"
        modal: true
        anchors.centerIn: parent
        width: 400
        standardButtons: Dialog.NoButton

        property var holderProjects: []
        property var checkedProjects: []

        onOpened: {
            checkedProjects = holderProjects.slice()
        }

        background: Rectangle {
            color: Theme.glassPill
            radius: Theme.radiusCard
            border.color: Theme.glassBorder
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 12

            Text {
                text: "Delete \"" + (root.skill.name || "") + "\" from which projects?"
                wrapMode: Text.Wrap
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                Layout.margins: 16
                Layout.fillWidth: true
            }

            GlassMultiSelect {
                id: deleteProjectSelect
                Layout.fillWidth: true
                Layout.margins: 16
                Layout.preferredHeight: 36
                model: deleteConfirmDialog.holderProjects
                selectedValues: deleteConfirmDialog.checkedProjects
                placeholderText: "Select projects..."
                allLabel: "All Projects"
                onSelectionChanged: deleteConfirmDialog.checkedProjects = selectedValues
            }
        }

        footer: RowLayout {
            spacing: 8
            Layout.margins: 12

            ActionButton {
                text: "Cancel"
                Layout.preferredWidth: 100
                Layout.preferredHeight: 36
                onClicked: deleteConfirmDialog.close()

                background: Rectangle {
                    radius: Theme.radiusButton
                    color: parent.hovered ? Theme.glassHover : "transparent"
                    border.color: Theme.glassBorder
                }

                contentItem: Text {
                    text: parent.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Font.Medium
                    color: Theme.label
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Item { Layout.fillWidth: true }

            ActionButton {
                text: "Delete"
                Layout.preferredWidth: 100
                Layout.preferredHeight: 36
                enabled: deleteConfirmDialog.checkedProjects.length > 0
                onClicked: {
                    AppController.deleteCustomCommand(root.skill.name, deleteConfirmDialog.checkedProjects)
                    deleteConfirmDialog.close()
                    root.closed()
                }

                background: Rectangle {
                    radius: Theme.radiusButton
                    color: !parent.enabled ? Theme.secondaryLabel : (parent.hovered ? Theme.alpha(Theme.danger, 0.93) : Theme.danger)
                }

                contentItem: Text {
                    text: parent.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Font.Bold
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
