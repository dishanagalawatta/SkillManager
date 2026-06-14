import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Rectangle {
    id: root
    property string sequence: ""
    property bool active: false
    signal sequenceCaptured(string sequence)

    radius: Theme.radiusButton
    color: active ? Theme.glassActive : (mouseArea.containsMouse ? Theme.glassHover : "transparent")
    border.color: (active || root.activeFocus) ? Theme.accent : Theme.glassBorder
    border.width: (active || root.activeFocus) ? 2 : 1
    height: 36
    Layout.fillWidth: true
    activeFocusOnTab: true

    Accessible.role: Accessible.Button
    Accessible.name: root.active ? "Recording shortcut, click outside to cancel" : (root.sequence || "Click to record shortcut")
    Accessible.description: "Press Enter or Space to start recording, click outside to cancel"

    focus: active
    onActiveChanged: {
        AppController.config_controller.isRecordingShortcut = active
        if (active) root.forceActiveFocus()
    }
    
    onActiveFocusChanged: {
        if (!activeFocus && active) {
            active = false
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12

        Text {
            Layout.fillWidth: true
            text: active ? "Recording... (Click outside to cancel)" : (sequence || "Click to record shortcut")
            color: active ? Theme.accent : (sequence ? Theme.label : Theme.secondaryLabel)
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: (sequence && !active) ? Font.Bold : Font.Normal
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.active = !root.active
            if (root.active) root.forceActiveFocus()
        }
    }

    Keys.onPressed: (event) => {
        if (!active) {
            if (event.key === Qt.Key_Space || event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                root.active = true
                root.forceActiveFocus()
                event.accepted = true
            }
            return
        }

        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            active = false
            event.accepted = true
            return
        }

        let modifiers = []
        if (event.modifiers & Qt.ControlModifier) modifiers.push("Ctrl")
        if (event.modifiers & Qt.ShiftModifier) modifiers.push("Shift")
        if (event.modifiers & Qt.AltModifier) modifiers.push("Alt")
        if (event.modifiers & Qt.MetaModifier) modifiers.push("Meta")

        let keyText = ""
        let isModifierOnly = false
        
        // Check if the key itself is a modifier
        if (event.key === Qt.Key_Control || event.key === Qt.Key_Shift || 
            event.key === Qt.Key_Alt || event.key === Qt.Key_Meta) {
            isModifierOnly = true
        }

        // Handle F-keys
        if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F12) {
            keyText = "F" + (event.key - Qt.Key_F1 + 1)
        } else if (event.key === Qt.Key_Escape) {
            keyText = "Escape"
        } else if (event.key === Qt.Key_Delete) {
            keyText = "Delete"
        } else if (event.key === Qt.Key_Home) {
            keyText = "Home"
        } else if (event.key === Qt.Key_End) {
            keyText = "End"
        } else if (event.key === Qt.Key_PageUp) {
            keyText = "PageUp"
        } else if (event.key === Qt.Key_PageDown) {
            keyText = "PageDown"
        } else if (event.key === Qt.Key_Insert) {
            keyText = "Insert"
        } else if (event.key === Qt.Key_Backspace) {
            keyText = "Backspace"
        } else if (event.key === Qt.Key_Tab) {
            keyText = "Tab"
        } else if (event.key === Qt.Key_Space) {
            keyText = "Space"
        } else if (event.key === Qt.Key_Left) {
            keyText = "Left"
        } else if (event.key === Qt.Key_Right) {
            keyText = "Right"
        } else if (event.key === Qt.Key_Up) {
            keyText = "Up"
        } else if (event.key === Qt.Key_Down) {
            keyText = "Down"
        } else if (event.key >= 0x20 && event.key <= 0x7E) {
            // Standard printable ASCII range (includes A-Z, 0-9, and punctuation)
            // Qt.Key values in this range match their ASCII counterparts.
            keyText = String.fromCharCode(event.key).toUpperCase()
        } else if (!isModifierOnly && event.text && event.text.charCodeAt(0) > 31 && event.text.charCodeAt(0) !== 127) {
            // Fallback for non-ASCII printable text (e.g., Unicode)
            keyText = event.text.toUpperCase()
        }

        if (keyText && !isModifierOnly) {
            let result = modifiers.join("+")
            if (result) result += "+"
            result += keyText
            root.sequence = result
            root.sequenceCaptured(result)
            active = false
        }
        event.accepted = true
    }
}
