/**
 * Purpose: Dialog for carrying missing skills when copying commands to another project.
 * Shows a checklist of skills the command references that aren't in the target project.
 * User can toggle individual skills, carry all, or skip carry.
 * Note: All/None buttons use RowLayout (not plain Row) to avoid "Unable to assign [undefined] to int"
 * warnings from Layout.preferredWidth attached properties on non-layout children.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Dialog {
    id: root

    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: 520
    modal: true
    padding: 0

    background: Rectangle {
        color: Theme.glassPill
        radius: Theme.radiusCard
        border.color: Theme.glassBorder
        border.width: 1

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 20
            color: Theme.glassShadow
            verticalOffset: 8
            horizontalOffset: 0
        }
    }

    property var missingSkills: []          // array of skill dicts from Python
    property string projectPath: ""
    property var commandPaths: []
    // Internal: track checked state per skill
    property var _checked: ({})

    onMissingSkillsChanged: {
        var c = {}
        for (var i = 0; i < missingSkills.length; i++) {
            var key = missingSkills[i].folder_name || missingSkills[i].name || ("skill_" + i)
            c[key] = true
        }
        _checked = c
    }

    function openWithContext(cmdPaths, projPath, skills) {
        commandPaths = cmdPaths
        projectPath = projPath
        missingSkills = skills
        open()
    }

    contentItem: ColumnLayout {
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 16
                spacing: 12

                Text {
                    text: "\uD83D\uDCE6"
                    font.pixelSize: 20
                }

                Text {
                    text: "Carry Skills to Project"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }

                IconButton {
                    text: "\u2715"
                    flat: true
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    onClicked: root.reject()

                    background: Rectangle {
                        radius: 16
                        color: parent.hovered ? Theme.glassHover : "transparent"
                    }

                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 16
                        color: Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.separator
            }
        }

        // Body
        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 24
            spacing: 16

            Text {
                text: "This command references " + root.missingSkills.length + " skill(s) not installed in the target project:"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.secondaryLabel
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(root.missingSkills.length * 40 + 16, 240)
                radius: Theme.radiusField
                color: Theme.glassHover
                border.color: Theme.glassBorder
                border.width: 1

                SmoothScrollView {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true

                    Column {
                        spacing: 0
                        width: parent.width

                        Repeater {
                            model: root.missingSkills

                            delegate: RowLayout {
                                width: parent ? parent.width : 200
                                height: 40
                                spacing: 12

                                GlassCheckBox {
                                    id: skillCheck
                                    Layout.leftMargin: 8
                                    checkState: (root._checked[modelData.folder_name || modelData.name] !== false) ? Qt.Checked : Qt.Unchecked
                                    onToggled: {
                                        var c = JSON.parse(JSON.stringify(root._checked))
                                        var key = modelData.folder_name || modelData.name
                                        c[key] = (skillCheck.checkState === Qt.Checked)
                                        root._checked = c
                                    }
                                }

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        text: modelData.name || modelData.folder_name || "Unknown"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeBody
                                        font.weight: Font.Medium
                                        color: Theme.label
                                    }
                                    Text {
                                        text: modelData.folder_name || ""
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeMetadata
                                        color: Theme.secondaryLabel
                                        visible: modelData.folder_name && modelData.folder_name !== modelData.name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

    }

    footer: Item {
        width: parent.width
        height: 76
        implicitHeight: height

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            anchors.topMargin: 12
            anchors.bottomMargin: 24
            spacing: 12
            
            // Select All / None
            RowLayout {
                spacing: 8

                ActionButton {
                    text: "All"
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 32
                    onClicked: {
                        var c = {}
                        for (var i = 0; i < root.missingSkills.length; i++) {
                            var key = root.missingSkills[i].folder_name || root.missingSkills[i].name
                            c[key] = true
                        }
                        root._checked = c
                    }

                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.glassBorder
                    }

                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        font.weight: Font.Medium
                        color: Theme.label
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                ActionButton {
                    text: "None"
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 32
                    onClicked: {
                        var c = {}
                        for (var i = 0; i < root.missingSkills.length; i++) {
                            var key = root.missingSkills[i].folder_name || root.missingSkills[i].name
                            c[key] = false
                        }
                        root._checked = c
                    }

                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.glassBorder
                    }

                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        font.weight: Font.Medium
                        color: Theme.label
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Skip (copy commands only)
            ActionButton {
                text: "Copy Commands Only"
                Layout.preferredWidth: 160
                Layout.preferredHeight: 40
                onClicked: {
                    root._carryResult([])
                    root.accept()
                }

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

            // Carry + Copy
            ActionButton {
                text: "Carry & Copy"
                Layout.preferredWidth: 130
                Layout.preferredHeight: 40
                onClicked: {
                    var confirmed = []
                    for (var i = 0; i < root.missingSkills.length; i++) {
                        var s = root.missingSkills[i]
                        var key = s.folder_name || s.name
                        if (root._checked[key] !== false) {
                            confirmed.push(s)
                        }
                    }
                    root._carryResult(confirmed)
                    root.accept()
                }

                background: Rectangle {
                    radius: Theme.radiusButton
                    color: parent.down ? Theme.accent : (parent.hovered ? Theme.alpha(Theme.accent, 0.93) : Theme.accent)
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

    // Internal: emit carry result
    signal carryConfirmed(var confirmedSkills)

    function _carryResult(confirmed) {
        carryConfirmed(confirmed)
    }
}
