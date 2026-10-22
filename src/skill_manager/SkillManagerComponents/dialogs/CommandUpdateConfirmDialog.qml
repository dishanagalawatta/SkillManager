/**
 * Confirmation dialog for deploying commands that already exist in the
 * target project.
 *
 * The Library is the source of truth for a command. Copying it into a
 * project where the same command file already exists is ambiguous, so the
 * copy pauses and this dialog asks what to do:
 *
 *   - "Update Existing & Copy New" — replace the project's command files
 *     with the Library versions and copy the commands that are new.
 *   - "Copy Only New" — keep the project's files and copy only the
 *     commands that do not exist there yet.
 *   - "Cancel" — abort the copy; nothing is written.
 *
 * Usage:
 *   CommandUpdateConfirmDialog {
 *       id: cmdUpdateConfirmDialog
 *   }
 *   cmdUpdateConfirmDialog.openForCopy(projectPath, commandPaths, existingEntries)
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

GlassDialog {
    id: root

    objectName: "commandUpdateConfirmDialog"

    modal: true
    anchors.centerIn: Overlay.overlay
    width: 520
    standardButtons: Dialog.NoButton

    dialogTitle: "Update Existing Commands"
    dialogIcon: "\u26A0\uFE0F"

    // ── Public state ─────────────────────────────────────────────────
    property string projectPath: ""
    property var commandPaths: []
    property var existingEntries: []
    property string projectLabel: ""

    // ── Public API ───────────────────────────────────────────────────
    function openForCopy(path, paths, existing) {
        root.projectPath = path || ""
        root.commandPaths = paths || []
        root.existingEntries = existing || []
        root.projectLabel = root.existingEntries.length > 0
            ? (root.existingEntries[0].project_label || "")
            : ""
        root.open()
        cancelBtn.forceActiveFocus()
    }

    function _existingNames() {
        var names = []
        for (var i = 0; i < root.existingEntries.length; i++) {
            var n = root.existingEntries[i].name
            if (n && names.indexOf(n) === -1) names.push(n)
        }
        return names
    }

    // ── Content ──────────────────────────────────────────────────────
    contentItem: ColumnLayout {
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 20
            Layout.bottomMargin: 8
            spacing: 12

            Text {
                textFormat: Text.StyledText
                text: {
                    var label = root.projectLabel ? " <b>" + root.projectLabel + "</b>" : ""
                    var names = root._existingNames()
                    var listed = names.length > 0
                        ? "<b>" + names.join("</b>, <b>") + "</b>"
                        : "these commands"
                    var verb = names.length === 1 ? "already exists" : "already exist"
                    return "The following command" + (names.length === 1 ? "" : "s")
                        + " " + verb + label + ": " + listed + "."
                }
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Text {
                text: "Choose what to do with the existing files."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: Font.Medium
                color: Theme.secondaryLabel
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }

    footer: Item {
        width: parent.width
        height: 92
        implicitHeight: height

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            anchors.topMargin: 16
            anchors.bottomMargin: 24
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Item { Layout.fillWidth: true }

                ActionButton {
                    id: cancelBtn
                    role: "secondary"
                    labelText: "Cancel"
                    accessibleName: "Cancel — abort the copy"
                    Layout.preferredWidth: 100
                    buttonHeight: 36
                    onClicked: {
                        AppController.cancelCommandCopyWithOverwrite()
                        root.reject()
                    }
                }

                ActionButton {
                    role: "secondary"
                    labelText: "Copy Only New"
                    accessibleName: "Copy only new — keep the existing project commands"
                    Layout.preferredWidth: 140
                    buttonHeight: 36
                    onClicked: {
                        AppController.confirmCommandCopyWithOverwrite(
                            root.projectPath,
                            JSON.stringify(root.commandPaths),
                            false
                        )
                        root.close()
                    }
                }

                ActionButton {
                    role: "primary"
                    labelText: "Update Existing & Copy New"
                    accessibleName: "Update existing and copy new — replace the project commands"
                    Layout.preferredWidth: 200
                    buttonHeight: 36
                    onClicked: {
                        AppController.confirmCommandCopyWithOverwrite(
                            root.projectPath,
                            JSON.stringify(root.commandPaths),
                            true
                        )
                        root.close()
                    }
                }
            }
        }
    }
}
