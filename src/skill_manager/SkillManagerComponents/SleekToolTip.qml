import QtQuick
import QtQuick.Controls
import QtQuick.Effects

ToolTip {
    id: control

    delay: 400
    timeout: 5000

    HoverHandler {
        id: hoverHandler
        parent: control.parent
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    }

    x: (typeof hoverHandler !== "undefined" && hoverHandler !== null && hoverHandler.hovered ? hoverHandler.point.position.x : 0) + 15
    y: (typeof hoverHandler !== "undefined" && hoverHandler !== null && hoverHandler.hovered ? hoverHandler.point.position.y : 0) + 15

    contentItem: Text {
        text: control.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeMetadata
        color: Theme.label
        wrapMode: Text.Wrap
        maximumLineCount: 3
    }

    background: Rectangle {
        color: Theme.glassPill
        radius: Theme.radiusSmall
        border.color: Theme.glassBorder
        border.width: 1
        
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.glassShadow
            shadowBlur: 0.5
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 4
        }
    }
}
