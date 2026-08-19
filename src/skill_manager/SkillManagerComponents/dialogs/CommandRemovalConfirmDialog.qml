/**
 * Purpose: Confirmation dialog for removing a command from selected projects.
 * Shown when AppController emits commandPendingRemovals.
 *
 * Built on GlassDialog for a unified "Solid Matte" surface: custom header
 * (icon + title + close), drop shadow, and ActionButton-based footer.
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

GlassDialog {
    id: root

    property var pendingRemovals: []
    property string localPath: ""
    property var approvedLabels: []

    modal: true
    anchors.centerIn: Overlay.overlay
    width: 450
    standardButtons: Dialog.NoButton

    dialogTitle: "Remove from Projects"
    dialogIcon: "\u26A0\uFE0F"

    onOpened: {
        // Default: all items checked
        root.approvedLabels = root.pendingRemovals.slice()
        for (let i = 0; i < removalRepeater.count; i++) {
            let item = removalRepeater.itemAt(i)
            if (item) item.checked = true
        }
        keepAllBtn.forceActiveFocus()
    }

    // ── Content ──────────────────────────────────────────────────────
    contentItem: ColumnLayout {
        spacing: 12

        Text {
            text: "The command will be removed from the following projects:"
            wrapMode: Text.WordWrap
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            color: Theme.label
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 24
            Layout.fillWidth: true
        }

        ColumnLayout {
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.bottomMargin: 24
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

    // ── Footer ───────────────────────────────────────────────────────
    footer: Item {
        width: parent.width
        height: 80
        implicitHeight: height

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            anchors.topMargin: 16
            anchors.bottomMargin: 24
            spacing: 12

            ActionButton {
                id: keepAllBtn
                role: "secondary"
                labelText: "Keep All"
                accessibleName: "Keep All \u2014 cancel removal"
                Layout.preferredWidth: 100
                buttonHeight: 36
                onClicked: {
                    AppController.confirmCommandRemovals(root.localPath, [])
                    root.close()
                }
            }

            Item { Layout.fillWidth: true }

            ActionButton {
                role: "danger"
                labelText: "Remove Checked"
                accessibleName: "Remove Checked \u2014 delete selected project copies"
                Layout.preferredWidth: 140
                buttonHeight: 36
                enabled: root.approvedLabels.length > 0
                onClicked: {
                    AppController.confirmCommandRemovals(root.localPath, root.approvedLabels)
                    root.close()
                }
            }
        }
    }
}
