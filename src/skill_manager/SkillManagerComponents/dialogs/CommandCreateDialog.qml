/**
 * Purpose: A modern "Solid Matte" dialog for creating or editing custom commands.
 * Usage:
 * CommandCreateDialog {
 *     id: commandDialog
 *     onAccepted: () => console.log("Command created")
 * }
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
    width: 750
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

    property bool editMode: false
    property string editLocalPath: ""
    property var editProjectLabels: []
    property string editCategoryValue: ""
    property string orphanCategory: ""
    property bool awaitingConflictResolution: false
    property var pendingArgs: ({})
    property var removalDialog: null

    function openWithContext() {
        editMode = false
        editLocalPath = ""
        editProjectLabels = AppController.currentProject ? [AppController.currentProject] : (AppController.projectLabels.length > 0 ? [AppController.projectLabels[0]] : [])
        editCategoryValue = ""
        orphanCategory = ""
        awaitingConflictResolution = false
        cmdNameInput.text = ""
        cmdBodyInput.text = ""
        open()
    }

    function openForEdit(skill) {
        editMode = true
        editLocalPath = skill.local_path || ""
        editProjectLabels = AppController.commandProjectsForPath(skill.local_path || "")
        if (editProjectLabels.length === 0) {
            editProjectLabels = AppController.currentProject ? [AppController.currentProject] : []
        }
        editCategoryValue = skill.category || ""
        orphanCategory = (skill.category
                          && AppController.categories.indexOf(skill.category) === -1)
            ? skill.category : ""
        awaitingConflictResolution = false
        cmdNameInput.text = skill.name || ""
        cmdBodyInput.text = skill.body_content || ""
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
                    text: "\u2328\uFE0F"
                    font.pixelSize: 20
                }

                Text {
                    text: editMode ? "Edit Custom Command" : "Create Custom Command"
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

        // Content
        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 24
            spacing: 20

            // Name and Category
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Command Name"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                    TextField {
                        id: cmdNameInput
                        placeholderText: "e.g. PR Template"
                        Accessible.role: Accessible.EditableText
                        Accessible.name: "Command Name"
                        Layout.fillWidth: true
                        selectByMouse: true
                        font.family: Theme.fontFamily
                        color: Theme.label
                        placeholderTextColor: Theme.secondaryLabel
                        leftPadding: 16
                        rightPadding: 16
                        topPadding: 12
                        bottomPadding: 12
                        background: Rectangle {
                            radius: Theme.radiusField
                            color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                            border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                            border.width: parent.activeFocus ? 2 : 1
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Category"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                    GlassDropdown {
                        id: cmdCategoryDrop
                        Layout.fillWidth: true
                        model: {
                            let cats = AppController.categories.slice()
                            if (root.orphanCategory && cats.indexOf(root.orphanCategory) === -1) {
                                cats = cats.concat([root.orphanCategory]).sort()
                            }
                            return ["\u2014 No Category \u2014"].concat(cats)
                        }
                        currentIndex: {
                            if (!root.editCategoryValue) return 0
                            let idx = model.indexOf(root.editCategoryValue)
                            return idx === -1 ? 0 : idx
                        }
                        onActivated: (index) => {
                            if (index === 0) {
                                root.editCategoryValue = ""
                            } else {
                                let cats = AppController.categories.slice()
                                if (root.orphanCategory && cats.indexOf(root.orphanCategory) === -1) {
                                    cats = cats.concat([root.orphanCategory]).sort()
                                }
                                root.editCategoryValue = cats[index - 1] || ""
                            }
                            root.orphanCategory = ""
                        }
                    }
                }
            }

            // Projects (multi-select)
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Projects"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                    GlassMultiSelect {
                        id: projectMultiSelect
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
                        model: AppController.projectLabels
                        selectedValues: root.editProjectLabels
                        placeholderText: "Select projects..."
                        allLabel: "All Projects"
                        onSelectionChanged: root.editProjectLabels = selectedValues
                    }
                }
            }

            // Command Body
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 4
                Text { text: "Command Content"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 350
                    radius: Theme.radiusField
                    color: Theme.glassHover
                    border.color: cmdBodyInput.activeFocus ? Theme.accent : Theme.glassBorder
                    border.width: cmdBodyInput.activeFocus ? 2 : 1

                    SmoothScrollView {
                        anchors.fill: parent
                        anchors.margins: 12
                        clip: true

                        TextArea {
                            id: cmdBodyInput
                            placeholderText: "Paste your command or system prompt here..."
                            Accessible.role: Accessible.EditableText
                            Accessible.name: "Command Content"
                            color: Theme.label
                            font.family: "Consolas", "Monospace", "monospace"
                            font.pixelSize: 13
                            wrapMode: TextArea.Wrap
                            selectByMouse: true
                            background: null
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

            Item { Layout.fillWidth: true }

            ActionButton {
                text: "Cancel"
                Layout.preferredWidth: 100
                Layout.preferredHeight: 40
                onClicked: root.reject()

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

            ActionButton {
                id: createBtn
                text: editMode ? "Update Command" : "Create Command"
                Layout.preferredWidth: 160
                Layout.preferredHeight: 40
                enabled: cmdNameInput.text !== "" && cmdBodyInput.text !== "" && root.editProjectLabels.length > 0

                onClicked: {
                    root.pendingArgs = {
                        localPath: editMode ? editLocalPath : "",
                        name: cmdNameInput.text,
                        body: cmdBodyInput.text,
                        category: editCategoryValue,
                        projectLabels: projectMultiSelect.selectedValues.slice()
                    }
                    root.awaitingConflictResolution = editMode
                    if (editMode) {
                        AppController.updateCustomCommandFull(
                            root.pendingArgs.localPath,
                            root.pendingArgs.name,
                            root.pendingArgs.body,
                            root.pendingArgs.category,
                            root.pendingArgs.projectLabels,
                            ""
                        )
                    } else {
                        AppController.createCustomCommand(
                            root.pendingArgs.name,
                            root.pendingArgs.body,
                            root.pendingArgs.projectLabels,
                            root.pendingArgs.category
                        )
                    }
                    root.accept()
                }

                background: Rectangle {
                    radius: Theme.radiusButton
                    color: !parent.enabled ? Theme.secondaryLabel : (parent.down ? Theme.accent : (parent.hovered ? Theme.alpha(Theme.accent, 0.93) : Theme.accent))
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

    // Removal confirmation dialog
    CommandRemovalConfirmDialog {
        id: removalConfirmDialog
        parent: Overlay.overlay
    }

    // Conflict resolution dialog
    GlassDialog {
        id: conflictDialog
        parent: Overlay.overlay
        dialogTitle: "File Already Exists"
        dialogIcon: "\u26A0\uFE0F"
        modal: true
        anchors.centerIn: parent
        width: 480
        standardButtons: Dialog.NoButton
        property string conflictPath: ""
        property string suggestedRename: ""

        onRejected: {
            AppController.updateCustomCommandFull(
                root.pendingArgs.localPath,
                root.pendingArgs.name,
                root.pendingArgs.body,
                root.pendingArgs.category,
                root.pendingArgs.projectLabels,
                "cancel"
            )
            conflictDialog.close()
            root.awaitingConflictResolution = false
            root.reject()
        }

        contentItem: ColumnLayout {
            spacing: 16
            Layout.fillWidth: true

            // Warning Banner
            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.topMargin: 20
                implicitHeight: warningLayout.implicitHeight + 24
                radius: 8
                color: Theme.alpha(Theme.danger, 0.06)
                border.color: Theme.alpha(Theme.danger, 0.15)
                border.width: 1

                RowLayout {
                    id: warningLayout
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    Text {
                        text: "\u26A0\uFE0F"
                        font.pixelSize: 22
                        Layout.alignment: Qt.AlignTop
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: "Conflict Detected"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeBody
                            font.weight: Font.Bold
                            color: Theme.danger
                            Layout.fillWidth: true
                        }

                        Text {
                            text: "A file named <b>" + conflictDialog.suggestedRename + "</b> already exists in the target location."
                            textFormat: Text.StyledText
                            wrapMode: Text.Wrap
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeBody
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            Text {
                text: "What would you like to do?"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                font.weight: Font.Medium
                color: Theme.secondaryLabel
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.bottomMargin: 8
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

                ActionButton {
                    id: cancelBtn
                    role: "secondary"
                    labelText: "Cancel"
                    accessibleName: "Cancel conflict resolution"
                    Layout.preferredWidth: 90
                    buttonHeight: 36
                    onClicked: conflictDialog.reject()
                }

                Item { Layout.fillWidth: true }

                ActionButton {
                    id: overwriteBtn
                    role: "danger"
                    labelText: "Overwrite"
                    accessibleName: "Overwrite existing file"
                    Layout.preferredWidth: 100
                    buttonHeight: 36
                    onClicked: {
                        AppController.updateCustomCommandFull(
                            root.pendingArgs.localPath,
                            root.pendingArgs.name,
                            root.pendingArgs.body,
                            root.pendingArgs.category,
                            root.pendingArgs.projectLabels,
                            "overwrite"
                        )
                        conflictDialog.accept()
                        root.awaitingConflictResolution = false
                        root.accept()
                    }
                }

                ActionButton {
                    id: renameBtn
                    role: "primary"
                    labelText: "Rename to '" + conflictDialog.suggestedRename + "'"
                    accessibleName: "Rename to suggested name"
                    Layout.preferredWidth: implicitWidth
                    buttonHeight: 36
                    onClicked: {
                        AppController.updateCustomCommandFull(
                            root.pendingArgs.localPath,
                            root.pendingArgs.name,
                            root.pendingArgs.body,
                            root.pendingArgs.category,
                            root.pendingArgs.projectLabels,
                            "rename"
                        )
                        conflictDialog.accept()
                        root.awaitingConflictResolution = false
                        root.accept()
                    }
                }
            }
        }
    }

    Connections {
        target: AppController
        function onCommandUpdateConflict(oldPath, conflictPath, suggestedRename) {
            if (!root.awaitingConflictResolution) return
            conflictDialog.conflictPath = conflictPath
            conflictDialog.suggestedRename = suggestedRename
            if (!root.visible) {
                root.editMode = true
                root.editLocalPath = root.pendingArgs.localPath
                cmdNameInput.text = root.pendingArgs.name
                cmdBodyInput.text = root.pendingArgs.body
                root.editCategoryValue = root.pendingArgs.category
                root.editProjectLabels = root.pendingArgs.projectLabels
                root.open()
            }
            conflictDialog.open()
        }
        function onCommandUpdateCompleted(oldPath, newPath) {
            if (!root.awaitingConflictResolution) return
            if (oldPath !== root.pendingArgs.localPath) return
            root.awaitingConflictResolution = false
            root.accept()
        }
        function onCommandPendingRemovals(localPath, pendingRemovals) {
            removalConfirmDialog.localPath = localPath
            removalConfirmDialog.pendingRemovals = pendingRemovals
            removalConfirmDialog.open()
        }
    }
}
