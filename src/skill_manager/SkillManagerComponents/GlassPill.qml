import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import App 1.0
import SkillManagerComponents 1.0

Item {
    id: root
    
    property alias color: rect.color
    property alias radius: rect.radius
    default property alias content: container.data

    Rectangle {
        id: rect
        anchors.fill: parent
        color: Theme.glassPill
        radius: Theme.radiusPill
        
        // Outer defining border
        border.width: 1
        border.color: Theme.glassOuterBorder

        // Inner highlight border (Removed for solid matte look, kept empty for layout)
        Item {
            anchors.fill: parent
        }

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowBlur: 2.0
            shadowColor: Theme.glassShadow
            shadowVerticalOffset: 4
            shadowHorizontalOffset: 0
        }
        
        Item {
            id: container
            anchors.fill: parent
            anchors.margins: 1
        }
    }
}
