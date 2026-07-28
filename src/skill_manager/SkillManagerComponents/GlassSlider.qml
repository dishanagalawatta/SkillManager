import QtQuick
import App 1.0

Item {
    id: control

    property real value: 1.0
    property real from: 0.0
    property real to: 1.0
    property real stepSize: 0.0

    signal moved()

    implicitWidth: 160
    implicitHeight: 24

    activeFocusOnTab: true

    readonly property real _range: control.to - control.from
    readonly property real _visualPosition: _range > 0 ? (control.value - control.from) / _range : 0

    function _quantize(val) {
        var clamped = Math.max(control.from, Math.min(control.to, val))
        if (control.stepSize > 0) {
            clamped = Math.round((clamped - control.from) / control.stepSize) * control.stepSize + control.from
            clamped = Math.max(control.from, Math.min(control.to, clamped))
        }
        return clamped
    }

    function _updateFromPos(mouseX) {
        var availWidth = control.width - handle.width
        if (availWidth <= 0) return
        var ratio = Math.max(0.0, Math.min(1.0, (mouseX - handle.width / 2) / availWidth))
        var rawVal = control.from + ratio * control._range
        var newVal = control._quantize(rawVal)
        if (Math.abs(control.value - newVal) > 0.0001) {
            control.value = newVal
            control.moved()
        }
    }

    Keys.onLeftPressed: (event) => {
        var step = control.stepSize > 0 ? control.stepSize : control._range / 10.0
        control.value = control._quantize(control.value - step)
        control.moved()
        event.accepted = true
    }
    Keys.onRightPressed: (event) => {
        var step = control.stepSize > 0 ? control.stepSize : control._range / 10.0
        control.value = control._quantize(control.value + step)
        control.moved()
        event.accepted = true
    }

    // Track Background
    Rectangle {
        id: trackBg
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        height: 6
        radius: 3
        color: Theme.glassHover
        border.color: control.activeFocus ? Theme.alpha(Theme.accent, 0.4) : Theme.glassBorder
        border.width: 1
    }

    // Track Filled Portion
    Rectangle {
        id: trackFilled
        anchors.left: trackBg.left
        anchors.verticalCenter: trackBg.verticalCenter
        height: 6
        width: Math.max(height, handle.x + handle.width / 2)
        radius: 3
        color: Theme.accent
    }

    // Slider Knob Handle
    Rectangle {
        id: handle
        x: Math.max(0, Math.min(control.width - width, control._visualPosition * (control.width - width)))
        anchors.verticalCenter: parent.verticalCenter
        width: 18
        height: 18
        radius: 9
        color: Theme.darkMode ? "#F3F4F6" : "#FFFFFF"
        border.color: control.activeFocus ? Theme.accent : (mouseArea.containsMouse || mouseArea.pressed ? Theme.accent : Theme.glassBorder)
        border.width: control.activeFocus || mouseArea.pressed ? 2 : 1

        scale: mouseArea.pressed ? 1.15 : (mouseArea.containsMouse ? 1.08 : 1.0)
        Behavior on scale { NumberAnimation { duration: 120 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true

        onPressed: (mouse) => control._updateFromPos(mouse.x)
        onPositionChanged: (mouse) => {
            if (pressed) control._updateFromPos(mouse.x)
        }
    }
}
