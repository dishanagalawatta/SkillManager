import QtQuick
import QtQuick.Controls
import App 1.0

TextField {
    id: rootSearchField
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
        border.color: rootSearchField.activeFocus ? Theme.accent : Theme.glassBorder
        border.width: rootSearchField.activeFocus ? 2 : 1

        Behavior on border.color { ColorAnimation { duration: 200 } }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "🔍"
            font.pixelSize: 13
            font.family: Theme.fontFamily
            color: Theme.secondaryLabel
        }
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
        visible: rootSearchField.text !== ""

        onClicked: {
            rootSearchField.text = ""
            rootSearchField.forceActiveFocus()
        }
    }

    leftPadding: 36
    rightPadding: rootSearchField.text === "" ? 12 : 36

    Accessible.role: Accessible.EditableText
    Accessible.name: "Search skills"
}
