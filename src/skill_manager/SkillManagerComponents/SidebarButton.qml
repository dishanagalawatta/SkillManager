import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0
import SkillManagerComponents 1.0

Button {
    id: control
    
    property bool active: false
    property bool collapsed: false
    property string iconText: ""
    property string labelText: ""
    
    Layout.fillWidth: true
    Layout.preferredHeight: 40

    ToolTip.visible: control.hovered && control.collapsed
    ToolTip.text: control.labelText
    ToolTip.delay: 400
    
    contentItem: RowLayout {
        spacing: 12
        
        Text {
            text: control.iconText
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: control.active ? Font.Bold : Font.Normal
            color: control.active ? Theme.label : Theme.secondaryLabel
            visible: control.iconText !== ""
            Layout.leftMargin: 12
        }
        
        Text {
            text: control.labelText
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: control.active ? Font.Bold : Font.Normal
            color: control.active ? Theme.label : Theme.secondaryLabel
            Layout.fillWidth: true
            visible: !control.collapsed
            elide: Text.ElideRight
        }
    }
    
    background: Rectangle {
        color: control.active ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
        radius: Theme.radiusPill
        
        // Removed left accent bar for cleaner screenshot-parity look
    }
    Accessible.role: Accessible.Button
    Accessible.name: control.labelText

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
}
