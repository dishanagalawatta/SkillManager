import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import App 1.0

Menu {
    id: root

    property alias blurRadius: frost.blurRadius

    topPadding: 6
    bottomPadding: 6
    leftPadding: 6
    rightPadding: 6

    background: Item {
        implicitWidth: 200
        implicitHeight: 40

        Rectangle {
            id: bgRect
            anchors.fill: parent
            color: Theme.alpha(Theme.glassPill, 0.8)
            radius: Theme.radiusCard
            border.width: 1
            border.color: Theme.glassBorder
            
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                horizontalOffset: 0
                verticalOffset: 4
                radius: 12
                samples: 25
                color: Theme.glassShadow
            }

            FrostOverlay {
                id: frost
                anchors.fill: parent
                radius: Theme.radiusCard
                blurRadius: 15
                opacity: 0.9
            }
        }
    }

    delegate: GlassMenuItem { }
}
