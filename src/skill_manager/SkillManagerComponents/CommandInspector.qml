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
                        visible: parent.hovered || parent.visualFocus
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
                        AppController.ops_controller.deleteSkills([{
                            "local_path": root.skill.local_path,
                            "is_command": true
                        }])
                        root.closed()
                    }
                    visible: root.skill && root.skill.local_path !== undefined
                    SleekToolTip {
                        id: delCmdToolTip
                        text: "Delete command"
                        visible: parent.hovered || parent.visualFocus
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
                        visible: parent.hovered || parent.visualFocus
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
}
