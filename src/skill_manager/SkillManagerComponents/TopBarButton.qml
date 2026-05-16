import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0
import SkillManagerComponents 1.0

Button {
    id: control
    
    property bool active: false
    property string iconText: ""
    property string labelText: ""
    
    padding: 12
    background: null // We'll draw our own
    
    contentItem: RowLayout {
        spacing: 8
        
        Text {
            text: control.iconText
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: control.active ? Font.Bold : Font.Normal
            color: control.active ? Theme.label : Theme.secondaryLabel
            visible: control.iconText !== ""
        }
        
        Text {
            text: control.labelText
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: control.active ? Font.Bold : Font.Normal
            color: control.active ? Theme.label : Theme.secondaryLabel
            visible: control.labelText !== ""
        }
    }
    
    Rectangle {
        anchors.fill: parent
        color: control.active ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
        radius: Theme.radiusPill
        z: -1
        
        Rectangle {
            visible: control.active
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.6
            height: 3
            radius: Theme.radiusSmall
            color: Theme.accent
        }
    }
    Accessible.role: Accessible.Button
    Accessible.name: control.labelText

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
}
