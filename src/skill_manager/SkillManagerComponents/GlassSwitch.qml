import QtQuick
import QtQuick.Effects
import App 1.0

// Custom toggle switch. Built on a bare Item + MouseArea instead of
// `Switch` from QtQuick.Controls because the Basic style's Switch.qml
// triggers Qt 6.11.1's "Cannot assign object of type X to list property
// 'data'; expected 'QObject'" bug at the indicator Rectangle.
Item {
    id: control

    property bool checked: false
    property alias text: label.text

    implicitWidth: 44
    implicitHeight: 24

    activeFocusOnTab: true

    Keys.onSpacePressed: { control.checked = !control.checked; event.accepted = true; }
    Keys.onReturnPressed: { control.checked = !control.checked; event.accepted = true; }
    Keys.onEnterPressed: { control.checked = !control.checked; event.accepted = true; }

    Rectangle {
        id: track
        anchors.fill: parent
        radius: height / 2
        color: control.checked ? Theme.accent : Theme.glassHover
        border.color: control.activeFocus ? Theme.accent : Theme.glassBorder
        border.width: control.activeFocus ? 2 : 1

        Behavior on color { ColorAnimation { duration: 200 } }
        Behavior on border.color { ColorAnimation { duration: 200 } }
    }

    Rectangle {
        id: handle
        x: control.checked ? parent.width - width - 4 : 4
        y: 4
        width: 16
        height: 16
        radius: 8
        color: Theme.darkMode ? "#E2E8F0" : "#FFFFFF"

        Behavior on x {
            NumberAnimation {
                duration: 250
                easing.type: Easing.OutQuint
            }
        }
    }

    Text {
        id: label
        visible: text !== ""
        anchors.left: handle.right
        anchors.leftMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        text: ""
        color: Theme.label
        font.family: Theme.fontFamily
        font.pixelSize: 12
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            control.forceActiveFocus();
            control.checked = !control.checked;
        }
    }

    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    Accessible.checkable: true
    Accessible.checked: checked
}
