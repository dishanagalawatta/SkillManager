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
            text: "🔍"
            font.pixelSize: 16
            color: Theme.secondaryLabel
            visible: control.text === ""
        }

        Button {
            id: clearButton
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 24
            height: 24
            visible: control.text !== ""
            flat: true
            padding: 0

            contentItem: Text {
                text: "×"
                font.pixelSize: 18
                color: Theme.secondaryLabel
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                opacity: clearButton.hovered ? 1.0 : 0.7
            }

            background: Rectangle {
                color: clearButton.hovered ? Theme.glassHover : "transparent"
                radius: width / 2
            }

            onClicked: {
                control.text = ""
                control.forceActiveFocus()
            }

            Accessible.role: Accessible.Button
            Accessible.name: "Clear search"
            ToolTip.text: "Clear search"
            ToolTip.visible: hovered

            HoverHandler {
                cursorShape: Qt.PointingHandCursor
            }
        }
    }
    
    leftPadding: text === "" ? 40 : 12
    rightPadding: control.text === "" ? 12 : 36

    Accessible.role: Accessible.EditableText
    Accessible.name: "Search skills"
}
