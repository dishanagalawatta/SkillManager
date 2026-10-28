/**
 * Purpose: Inline task composer for the per-project task list.
 * Usage:
 *   TaskComposer {
 *       projectPath: "..."      // empty disables the editor
 *       onSubmitted: (title, notes, priority, attachments) => ...
 *   }
 *
 * The composer is the "write it where it lands" surface for a task: a
 * multi-line editor that grows with the text, so a task can be one line or a
 * title plus notes, subtasks (`- ` bullets continue automatically) and
 * attached images. Ctrl+Enter (Cmd+Enter on macOS) adds the task; Enter
 * inserts a newline; Esc discards the draft; Ctrl+V attaches an image when
 * the clipboard holds one (and pastes text otherwise).
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Dialogs
import ".."
import App 1.0

Item {
    id: root

    property string projectPath: ""
    property string priority: "medium"
    property var attachments: []
    property alias text: editor.text
    // Transient inline feedback (e.g. "not an image") — shown in place of the
    // keyboard hint so nothing jumps when a message appears.
    property string errorText: ""
    readonly property bool hasDraft: (editor.text || "").trim() !== ""

    // Emitted on Ctrl+Enter / the Add button. The draft is left intact so the
    // caller can clear it (and keep focus) once the task is stored.
    signal submitted(string title, string notes, string priority, var attachments)
    signal cancelled()

    readonly property bool canSubmit: root.projectPath !== "" && root._split().title !== ""

    implicitHeight: frame.height
    implicitWidth: 200

    function focusEditor() {
        editor.forceActiveFocus()
    }

    function reset() {
        editor.text = ""
        root.attachments = []
        root.priority = "medium"
        root.errorText = ""
    }

    function _fail(message) {
        root.errorText = message
        errorTimer.restart()
    }

    // First non-empty line is the title; everything after it is the notes.
    function _split() {
        var normalized = (editor.text || "").replace(/\r\n/g, "\n")
        var lines = normalized.split("\n")
        var titleIndex = -1
        for (var i = 0; i < lines.length; i++) {
            if (lines[i].trim() !== "") {
                titleIndex = i
                break
            }
        }
        if (titleIndex === -1) return { title: "", notes: "" }
        var title = lines[titleIndex].trim()
        var notes = lines.slice(titleIndex + 1).join("\n").replace(/^\n+/, "").replace(/\s+$/, "")
        return { title: title, notes: notes }
    }

    // Returns the bullet prefix for the line the caret sits on, or "" when the
    // line is not a bullet. An empty bullet ends the list.
    function _bulletPrefix() {
        var before = editor.text.slice(0, editor.cursorPosition)
        var line = before.slice(before.lastIndexOf("\n") + 1)
        var match = line.match(/^(\s*)([-*])(\s+)(\[[ xX]\]\s+)?/)
        if (!match) return ""
        if (line.slice(match[0].length).trim() === "") return ""
        return match[1] + match[2] + " " + (match[4] ? "[ ] " : "")
    }

    function _stripEmptyBullet() {
        var pos = editor.cursorPosition
        var before = editor.text.slice(0, pos)
        var lineStart = before.lastIndexOf("\n") + 1
        var line = before.slice(lineStart)
        var match = line.match(/^(\s*)([-*])(\s+)(\[[ xX]\]\s+)?$/)
        if (!match) return
        editor.remove(lineStart, pos)
    }

    function _submit() {
        if (!root.canSubmit) return
        var parts = root._split()
        root.submitted(parts.title, parts.notes, root.priority, root.attachments)
    }

    function _attachFromUrl(url) {
        if (root.projectPath === "") return
        var stored = AppController.task_controller.attachTaskImage(root.projectPath, url)
        if (stored === "" || stored === undefined || stored === null) {
            root._fail("Only image files can be attached")
            return
        }
        var next = (root.attachments || []).slice()
        next.push(stored)
        root.attachments = next
    }

    function _attachFromClipboard() {
        if (root.projectPath === "") return false
        var stored = AppController.task_controller.attachClipboardImage(root.projectPath)
        if (stored === "" || stored === undefined || stored === null) return false
        var next = (root.attachments || []).slice()
        next.push(stored)
        root.attachments = next
        return true
    }

    function _removeAttachment(index) {
        var next = (root.attachments || []).slice()
        next.splice(index, 1)
        root.attachments = next
    }

    function _cyclePriority() {
        root.priority = root.priority === "low" ? "medium"
            : root.priority === "medium" ? "high" : "low"
    }

    Timer {
        id: errorTimer
        interval: 4000
        onTriggered: root.errorText = ""
    }

    // ── Frame ────────────────────────────────────────────────────────
    Rectangle {
        id: frame
        width: parent.width
        height: layout.implicitHeight + 16
        radius: Theme.radiusSmall
        color: editor.activeFocus ? Theme.glassActive : Theme.glassPill
        border.color: editor.activeFocus ? Theme.accent : Theme.glassBorder
        border.width: editor.activeFocus ? 2 : 1

        ColumnLayout {
            id: layout
            anchors.fill: parent
            anchors.margins: 8
            spacing: 6

            TextArea {
                id: editor
                objectName: "taskComposerEditor"
                Layout.fillWidth: true
                // Grows with the text, then scrolls.
                Layout.preferredHeight: Math.min(Math.max(contentHeight + 8, 44), 180)
                enabled: root.projectPath !== ""
                placeholderText: root.projectPath === ""
                    ? "Select a project to add tasks"
                    : "Add a task…\nUse - for subtasks, Ctrl+Enter to add"
                placeholderTextColor: Theme.secondaryLabel
                wrapMode: TextArea.Wrap
                selectByMouse: true
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                leftPadding: 6
                rightPadding: 6
                topPadding: 4
                bottomPadding: 4
                background: null

                Accessible.role: Accessible.EditableText
                Accessible.name: "New task. First line is the title, following lines are notes"
                Accessible.description: "Ctrl+Enter adds the task"

                Keys.onPressed: (event) => {
                    var isEnter = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                    var isPaste = event.key === Qt.Key_V
                        && (event.modifiers & (Qt.ControlModifier | Qt.MetaModifier))
                    if (isPaste) {
                        // An image on the clipboard becomes an attachment; text
                        // falls through to the editor's own paste handling.
                        if (root._attachFromClipboard()) event.accepted = true
                        return
                    }
                    if (isEnter && (event.modifiers & (Qt.ControlModifier | Qt.MetaModifier))) {
                        root._submit()
                        event.accepted = true
                        return
                    }
                    if (isEnter && !(event.modifiers & Qt.ShiftModifier)) {
                        var prefix = root._bulletPrefix()
                        if (prefix === "") {
                            // An empty bullet ends the list instead of leaving
                            // a dangling marker behind.
                            root._stripEmptyBullet()
                            return
                        }
                        editor.insert(editor.cursorPosition, "\n" + prefix)
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Escape) {
                        root.cancelled()
                        event.accepted = true
                    }
                }
            }

            // Attachment thumbnails
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                visible: (root.attachments || []).length > 0

                Repeater {
                    model: root.attachments

                    delegate: Item {
                        required property var modelData
                        required property int index
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40

                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: Theme.glassPill
                            border.color: Theme.glassBorder
                            border.width: 1
                            clip: true

                            Image {
                                anchors.fill: parent
                                anchors.margins: 2
                                source: modelData ? ("file://" + modelData) : ""
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                cache: true
                            }
                        }

                        IconButton {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.rightMargin: -5
                            anchors.topMargin: -5
                            buttonSize: 16
                            iconSize: 8
                            role: "ghost"
                            showRing: false
                            iconSource: AppController.ui_controller.getAssetUri("ui/close-icon.svg")
                            tooltipText: "Remove attachment"
                            accessibleName: "Remove attachment " + (index + 1)
                            onClicked: root._removeAttachment(index)
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                // Priority selector — click or Space/Return cycles low → medium → high
                Rectangle {
                    id: priorityPill
                    Layout.preferredWidth: priorityText.implicitWidth + 20
                    Layout.preferredHeight: 26
                    radius: 13
                    color: priorityHover.hovered || priorityPill.activeFocus
                        ? Theme.glassHover : "transparent"
                    border.color: Theme.glassBorder
                    border.width: 1
                    activeFocusOnTab: true

                    Accessible.role: Accessible.Button
                    Accessible.name: "Priority: " + root.priority
                    Accessible.onPressAction: root._cyclePriority()
                    Accessible.onToggleAction: root._cyclePriority()

                    Text {
                        id: priorityText
                        anchors.centerIn: parent
                        text: root.priority === "low" ? "Low"
                            : root.priority === "high" ? "High" : "Med"
                        color: root.priority === "high" ? Theme.danger
                            : root.priority === "low" ? Theme.secondaryLabel : Theme.accent
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        font.weight: Font.Medium
                    }

                    HoverHandler {
                        id: priorityHover
                        cursorShape: Qt.PointingHandCursor
                    }

                    TapHandler {
                        onTapped: root._cyclePriority()
                    }
                    Keys.onPressed: (event) => {
                        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
                            root._cyclePriority()
                            event.accepted = true
                        }
                    }
                }

                IconButton {
                    objectName: "taskAttachBtn"
                    buttonSize: 26
                    iconSize: 15
                    iconSource: AppController.ui_controller.getAssetUri("ui/attach-icon.svg")
                    tooltipText: "Attach an image (or drop / paste one)"
                    accessibleName: "Attach an image to the task"
                    enabled: root.projectPath !== ""
                    onClicked: attachDialog.open()
                }

                Item { Layout.fillWidth: true }

                Text {
                    Layout.maximumWidth: 130
                    text: root.errorText !== "" ? root.errorText : "Ctrl+Enter to add"
                    color: root.errorText !== "" ? Theme.warning : Theme.secondaryLabel
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                    elide: Text.ElideRight
                    visible: root.width >= 280
                }

                ActionButton {
                    objectName: "taskComposerAddBtn"
                    role: "primary"
                    labelText: "Add"
                    accessibleName: "Add task"
                    buttonHeight: 26
                    enabled: root.canSubmit
                    onClicked: root._submit()
                }
            }
        }
    }

    // Drop an image file straight onto the composer.
    DropArea {
        anchors.fill: parent
        onEntered: (drag) => drag.acceptProposedAction()
        onDropped: (drop) => {
            if (!drop.hasUrls) return
            for (var i = 0; i < drop.urls.length; i++) {
                root._attachFromUrl(drop.urls[i])
            }
            drop.acceptProposedAction()
        }
    }

    FileDialog {
        id: attachDialog
        title: "Attach an image"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"]
        onAccepted: root._attachFromUrl(selectedFile)
    }
}
