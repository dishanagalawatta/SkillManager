import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import App 1.0
import SkillManagerComponents 1.0

/**
 * Purpose: A modernized, glass-styled toggle button for the Skill Manager.
 * Usage: 
 *   GlassToggleButton {
 *       text: "Show Archived"
 *       checked: model.showArchived
 *       onClicked: model.showArchived = !checked
 *   }
 */
Button {
    id: control
    
    property string iconInactive: "📁"
    property string iconActive: "📦"
    property string textInactive: text
    property string textActive: text
    
    checkable: true
    
    implicitWidth: contentLayout.implicitWidth + 32
    implicitHeight: 36

    contentItem: RowLayout {
        id: contentLayout
        spacing: 8
        
        Text {
            text: control.checked ? control.iconActive : control.iconInactive
            font.family: Theme.fontFamily
            font.pixelSize: 16
            color: control.checked ? Theme.accent : Theme.secondaryLabel
            
            Behavior on color { ColorAnimation { duration: 200 } }
        }
        
        Text {
            text: control.checked ? control.textActive : control.textInactive
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: control.checked ? Font.DemiBold : Font.Normal
            color: control.checked ? Theme.label : Theme.secondaryLabel
            
            Behavior on color { ColorAnimation { duration: 200 } }
        }
    }

    background: Item {
        Rectangle {
            id: bgRect
            anchors.fill: parent
            radius: Theme.radiusPill
            color: control.checked ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, Theme.darkMode ? 0.2 : 0.1) : Theme.glassPill
            border.color: control.checked ? Theme.accent : (control.hovered ? Theme.secondaryLabel : Theme.glassBorder)
            border.width: 1

            Behavior on color { ColorAnimation { duration: 200 } }
            Behavior on border.color { ColorAnimation { duration: 200 } }
            
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: control.hovered || control.checked
                shadowBlur: 0.5
                shadowColor: Theme.glassShadow
                shadowVerticalOffset: 2
            }
        }
    }
}
