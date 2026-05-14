import QtQuick
import QtQuick.Controls
import App 1.0

Button {
    id: control
    
    property bool isActive: false
    property string iconText: ""
    
    contentItem: Row {
        spacing: 6
        Text {
            text: control.iconText
            font.pixelSize: 14
            verticalAlignment: Text.AlignVCenter
        }
        Text {
            text: control.text
            font.family: Theme.fontFamily
            font.pixelSize: 12
            font.weight: control.isActive ? Font.Bold : Font.Normal
            color: Theme.label
            verticalAlignment: Text.AlignVCenter
        }
    }

    background: Rectangle {
        implicitWidth: 100
        implicitHeight: 32
        radius: Theme.radiusPill
        color: control.isActive ? Theme.glassActive : Theme.glassPill
        border.color: control.isActive ? Theme.accent : Theme.glassBorder
        border.width: 1
        
        Behavior on color { ColorAnimation { duration: 200 } }
    }
    
    onClicked: isActive = !isActive
}
