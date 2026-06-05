import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
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

        Image {
            id: searchIcon
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            source: AppController.ui_controller.getAssetUri("ui/search-icon.svg")
            width: 14
            height: 14
            sourceSize.width: 14
            sourceSize.height: 14
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        ColorOverlay {
            anchors.fill: searchIcon
            source: searchIcon
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
        iconSource: AppController.ui_controller.getAssetUri("ui/close-icon.svg")
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

    signal debouncedTextChanged(string text)
    property int debounceDelay: 200

    Timer {
        id: debounceTimer
        interval: rootSearchField.debounceDelay
        repeat: false
        onTriggered: rootSearchField.debouncedTextChanged(rootSearchField.text)
    }

    onTextChanged: {
        debounceTimer.restart()
    }

    Accessible.role: Accessible.EditableText
    Accessible.name: "Search skills"
}
