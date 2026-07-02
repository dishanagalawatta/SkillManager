import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Rectangle {
    id: root

    property var skill: ({})
    property bool isCollapsed: false
    property var editDialog: null
    property var dependencyList: []
    property var referenceRanges: []

    readonly property int targetWidth: {
        if (!root.skill || root.skill.local_path === undefined) return 0;
        if (isCollapsed) return 32;

        let dynamicWidth = parent ? parent.width * 0.5 : 400;
        return Math.min(800, Math.max(400, dynamicWidth));
    }

    signal closed()
    signal deleteRequested(string name, string path, bool isCommand)

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

    onSkillChanged: {
        var s = root.skill
        if (s && s.is_command && s.local_path && typeof AppController !== "undefined" && AppController) {
            root.dependencyList = AppController.ops_controller.getReferencedSkillsForCommand(s.local_path)
            root.referenceRanges = AppController.ops_controller.getSkillReferenceRanges(s.local_path)
        } else {
            root.dependencyList = []
            root.referenceRanges = []
        }
        if (bodyArea) {
            bodyArea._lastHighlightedText = ""
        }
        _applyHighlights(-1)
    }

    function _applyHighlights(focusedIndex) {
        if (typeof AppController === "undefined" || !AppController) return
        if (root.referenceRanges && root.referenceRanges.length > 0) {
            AppController.ops_controller.applySkillHighlights(
                bodyArea,
                JSON.stringify(root.referenceRanges),
                focusedIndex
            )
        } else {
            AppController.ops_controller.clearSkillHighlights(bodyArea)
        }
    }

    function _scrollToFocused(index) {
        if (!bodyArea || index < 0 || index >= root.referenceRanges.length) return
        var range = root.referenceRanges[index]
        bodyArea.cursorPosition = range.start
        bodyArea.forceActiveFocus()
    }

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
                    ContextMenu.menu: null
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
                    tooltipText: "Edit settings"
                }

                IconButton {
                    iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                    role: "destructive"
                    flat: true
                    onClicked: (mouse) => {
                        root.deleteRequested(root.skill.name || "", root.skill.local_path || "", true)
                    }
                    visible: root.skill && root.skill.local_path !== undefined
                    tooltipText: "Delete command"
                }

                IconButton {
                    text: "✕"
                    flat: true
                    onClicked: (mouse) => root.closed()
                    visible: root.skill && root.skill.local_path !== undefined
                    tooltipText: "Close Inspector"
                }
            }

            // Skill Dependencies Section
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                visible: root.dependencyList.length > 0

                Text {
                    text: "Skill Dependencies"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: Theme.secondaryLabel
                    opacity: 0.8
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 6

                    Repeater {
                        model: root.dependencyList

                        Rectangle {
                            id: depPill
                            height: 22
                            width: depRow.implicitWidth + 12
                            radius: Theme.radiusSmall
                            color: Theme.glassHover
                            border.color: Theme.glassBorder
                            border.width: 1

                            Row {
                                id: depRow
                                anchors.centerIn: parent
                                spacing: 4

                                Text {
                                    text: modelData.name
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    color: Theme.label
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: modelData.occurrences > 1 ? ("× " + modelData.occurrences) : ""
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 9
                                    color: Theme.secondaryLabel
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: modelData.occurrences > 1
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: (mouse) => {
                                    // Find the first range index for this skill name
                                    for (var i = 0; i < root.referenceRanges.length; i++) {
                                        if (root.referenceRanges[i].name === modelData.name) {
                                            _applyHighlights(i)
                                            _scrollToFocused(i)
                                            break
                                        }
                                    }
                                }
                            }

                            Accessible.role: Accessible.Link
                            Accessible.name: "Skill dependency: " + modelData.name + (modelData.occurrences > 1 ? " (" + modelData.occurrences + " occurrences)" : "")
                        }
                    }
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
                            ContextMenu.menu: null
                            objectName: "commandBodyTextArea"
                            width: parent.width - parent.leftPadding - parent.rightPadding
                            Accessible.role: Accessible.EditableText
                            Accessible.name: "Command Details"
                            property string _lastHighlightedText: ""
                            text: root.skill.body_content || ""
                            onTextChanged: {
                                if (text !== _lastHighlightedText) {
                                    _lastHighlightedText = text
                                    _applyHighlights(-1)
                                }
                            }
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
