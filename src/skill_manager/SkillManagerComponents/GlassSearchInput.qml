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
    }
    
    leftPadding: text === "" ? 40 : 12
    rightPadding: 12
}
