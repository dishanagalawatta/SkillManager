import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import App 1.0

Rectangle {
    id: root

    property alias color: root.color
    property alias radius: root.radius
    default property alias content: root.data

    color: Theme.glassPill
    radius: Theme.radiusPill
    border.width: 1
    border.color: Theme.glassOuterBorder

    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowBlur: 2.0
        shadowColor: Theme.glassShadow
        shadowVerticalOffset: 4
        shadowHorizontalOffset: 0
    }
}
