import QtQuick
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0

TextField {
    id: control
    placeholderText: "Search skills..."
    font.family: Theme.fontFamily
    font.pixelSize: Theme.sizeBody
    color: Theme.label
    placeholderTextColor: Theme.secondaryLabel

    background: Rectangle {
        implicitWidth: 300
        implicitHeight: 40
        radius: Theme.radiusPill
        color: Theme.glassPill
        border.color: control.activeFocus ? Theme.accent : Theme.glassBorder
        border.width: control.activeFocus ? 2 : 1

        Behavior on border.color { ColorAnimation { duration: 200 } }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "Search"
            font.pixelSize: 11
            font.family: Theme.fontFamily
            font.weight: Font.DemiBold
            color: Theme.secondaryLabel
            visible: control.text === ""
        }

        IconButton {
            id: clearButton
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            buttonSize: 24
            iconSize: 14
            iconText: "x"
            role: "ghost"
            tooltipText: "Clear search"
            visible: control.text !== ""

            onClicked: {
                control.text = ""
                control.forceActiveFocus()
            }
        }
    }

    leftPadding: text === "" ? 56 : 12
    rightPadding: control.text === "" ? 12 : 36

    Accessible.role: Accessible.EditableText
    Accessible.name: "Search skills"
}
