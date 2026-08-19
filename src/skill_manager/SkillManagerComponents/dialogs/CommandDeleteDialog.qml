/**
 * Unified delete confirmation dialog supporting two modes:
 *   - Command mode: "Delete X from which projects?" with project multi-select
 *   - Skill mode:   "Delete X from which projects?" with project multi-select
 *
 * Usage:
 *   CommandDeleteDialog {
 *       id: cmdDeleteDialog
 *   }
 *   cmdDeleteDialog.openForCommand("myCmd", ["proj1", "proj2"])
 *   cmdDeleteDialog.openForSkill("mySkill", ["proj1", "proj2"])
 *   cmdDeleteDialog.openBulkSkill(5, ["proj1", "proj2"], ["/path/to/skill1", "/path/to/skill2"])
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

GlassDialog {
    id: root

    modal: true
    anchors.centerIn: Overlay.overlay
    width: 440
    standardButtons: Dialog.NoButton

    // ── Public state ─────────────────────────────────────────────────
    property bool commandMode: false
    property string itemName: ""
    property string skillPath: ""
    property int bulkCount: 0
    property var holderProjects: []
    property var checkedProjects: []
    property var bulkPaths: []
    property var selectedNames: []

    // ── Dynamic title ────────────────────────────────────────────────
    dialogTitle: bulkCount > 0 ? "Delete Items" : "Delete Item"
    dialogIcon: "\u26A0\uFE0F"

    // ── Public API ───────────────────────────────────────────────────
    function openForCommand(name, projects) {
        root.commandMode = true
        root.itemName = name
        root.selectedNames = [name]
        root.holderProjects = projects || []
        
        var cp = AppController.currentProject
        if (cp && root.holderProjects.indexOf(cp) >= 0) {
            root.checkedProjects = [cp]
        } else {
            root.checkedProjects = root.holderProjects.slice()
        }
        projectSelect.selectedValues = root.checkedProjects

        root.bulkCount = 0
        root.bulkPaths = []
        root.open()
        cancelBtn.forceActiveFocus()
    }

    function openForSkill(name, projects, path) {
        root.commandMode = false
        root.itemName = name
        root.selectedNames = [name]
        root.skillPath = path || ""
        root.holderProjects = projects || []
        
        var cp = AppController.currentProject
        if (cp && root.holderProjects.indexOf(cp) >= 0) {
            root.checkedProjects = [cp]
        } else {
            root.checkedProjects = root.holderProjects.slice()
        }
        projectSelect.selectedValues = root.checkedProjects

        root.bulkCount = 0
        root.bulkPaths = []
        root.open()
        cancelBtn.forceActiveFocus()
    }

    function openBulkSkill(count, projects, paths, names) {
        root.commandMode = false
        root.itemName = ""
        root.bulkCount = count
        root.bulkPaths = paths || []
        if (names) {
            root.selectedNames = names
        } else if (paths) {
            root.selectedNames = paths.map(function(p) {
                var idx1 = p.lastIndexOf("/")
                var idx2 = p.lastIndexOf("\\")
                var idx = Math.max(idx1, idx2)
                return idx >= 0 ? p.substring(idx + 1) : p
            })
        } else {
            root.selectedNames = []
        }
        root.holderProjects = projects || []
        
        var cp = AppController.currentProject
        if (cp && root.holderProjects.indexOf(cp) >= 0) {
            root.checkedProjects = [cp]
        } else {
            root.checkedProjects = root.holderProjects.slice()
        }
        projectSelect.selectedValues = root.checkedProjects

        root.open()
        cancelBtn.forceActiveFocus()
    }

    // ── Reset state on open ──────────────────────────────────────────
    onOpened: {}

    onClosed: {}

    // ── Content ──────────────────────────────────────────────────────
    contentItem: ColumnLayout {
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 20
            Layout.bottomMargin: 8
            spacing: 16

            // Message text
            Text {
                textFormat: Text.StyledText
                text: {
                    if (root.bulkCount > 0) {
                        var boldNames = root.selectedNames.map(function(n) { return "<b>" + n + "</b>"; }).join(", ");
                        var label = root.bulkCount === 1 ? "item " : "items ";
                        return "Delete " + label + boldNames + " from which projects?"
                    }
                    return "Delete item <b>" + root.itemName + "</b> from which projects?"
                }
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            // Project multi-select
            GlassMultiSelect {
                id: projectSelect
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                model: root.holderProjects
                // Imperatively set via openFor* functions to prevent binding breakages
                placeholderText: "Select projects..."
                allLabel: "All Projects"
                onSelectionChanged: root.checkedProjects = selectedValues
            }
        }

    }

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

            Item { Layout.fillWidth: true }

            ActionButton {
                id: cancelBtn
                role: "secondary"
                labelText: "Cancel"
                accessibleName: "Cancel \u2014 close dialog"
                Layout.preferredWidth: 100
                buttonHeight: 36
                onClicked: root.reject()
            }

            ActionButton {
                id: deleteBtn
                role: "danger"
                labelText: "Delete"
                accessibleName: "Delete \u2014 confirm deletion"
                Layout.preferredWidth: 100
                buttonHeight: 36
                enabled: root.checkedProjects.length > 0

                onClicked: {
                    if (root.commandMode) {
                        AppController.deleteCustomCommand(root.itemName, root.checkedProjects)
                    } else if (root.bulkCount > 0) {
                        AppController.deleteSkillsByPaths(root.bulkPaths)
                    } else {
                        AppController.deleteSkillFromProjects(root.skillPath, root.checkedProjects)
                    }
                    root.close()
                }
            }
        }
    }
}
