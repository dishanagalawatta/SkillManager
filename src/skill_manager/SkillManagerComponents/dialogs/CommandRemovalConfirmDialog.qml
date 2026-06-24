/**
 * Purpose: Confirmation dialog for removing a command from selected projects.
 * Shown when AppController emits commandPendingRemovals.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Dialog {
    id: root

    property var pendingRemovals: []
    property string localPath: ""
    property var approvedLabels: []

    title: "Remove from projects"
    modal: true
    anchors.centerIn: parent
    standardButtons: Dialog.NoButton
    width: 450

    onOpened: {
        // Default: all items checked
        root.approvedLabels = root.pendingRemovals.slice()
        for (let i = 0; i < removalRepeater.count; i++) {
            let item = removalRepeater.itemAt(i)
            if (item) item.checked = true
        }
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
            text: "The command will be removed from the following projects:"
            wrapMode: Text.Wrap
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            color: Theme.label
            Layout.margins: 16
            Layout.fillWidth: true
        }

        ColumnLayout {
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            Layout.bottomMargin: 8
            spacing: 8

            Repeater {
                id: removalRepeater
                model: root.pendingRemovals

                CheckBox {
                    id: removalCheckBox
                    text: modelData
                    checked: true
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    contentItem: Text {
                        text: removalCheckBox.text
                        font: removalCheckBox.font
                        color: Theme.label
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: removalCheckBox.indicator.width + removalCheckBox.spacing
                    }
                    indicator: Rectangle {
                        width: 18
                        height: 18
                        radius: 4
                        color: removalCheckBox.checked ? Theme.accent : Theme.glassHover
                        border.color: removalCheckBox.checked ? Theme.accent : Theme.glassBorder
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "\u2713"
                            color: "white"
                            font.pixelSize: 12
                            font.bold: true
                            visible: removalCheckBox.checked
                        }
                    }

                    onCheckedChanged: {
                        let labels = []
                        for (let i = 0; i < removalRepeater.count; i++) {
                            let item = removalRepeater.itemAt(i)
                            if (item && item.checked) {
                                labels.push(root.pendingRemovals[i])
                            }
                        }
                        root.approvedLabels = labels
                    }

                    Accessible.role: Accessible.CheckBox
                    Accessible.name: "Remove from " + modelData
                }
            }
        }
    }

    footer: RowLayout {
        spacing: 8
        Layout.margins: 12

        ActionButton {
            text: "Keep All"
            Layout.preferredWidth: 100
            Layout.preferredHeight: 36
            onClicked: {
                AppController.confirmCommandRemovals(root.localPath, [])
                root.close()
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

            Accessible.role: Accessible.Button
            Accessible.name: "Keep All — cancel removal"
        }

        Item { Layout.fillWidth: true }

        ActionButton {
            text: "Remove Checked"
            Layout.preferredWidth: 140
            Layout.preferredHeight: 36
            enabled: root.approvedLabels.length > 0
            onClicked: {
                AppController.confirmCommandRemovals(root.localPath, root.approvedLabels)
                root.close()
            }

            background: Rectangle {
                radius: Theme.radiusButton
                color: parent.hovered ? Theme.alpha(Theme.accent, 0.85) : Theme.accent
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

            Accessible.role: Accessible.Button
            Accessible.name: "Remove Checked — delete selected project copies"
        }
    }

}
