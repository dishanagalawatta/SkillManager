import QtQuick
import QtQuick.Controls
import App 1.0

Menu {
    id: root

    topPadding: 6
    bottomPadding: 6
    leftPadding: 6
    rightPadding: 6

    background: Item {
        implicitWidth: 200
        implicitHeight: 40

        // AT exposure for the menu surface: Menu itself is a Popup (not an
        // Item), so Qt forbids attaching Accessible to it directly. The
        // background Item fills the popup, making it the AT-visible host.
        Accessible.role: Accessible.PopupMenu
        Accessible.name: root.title !== "" ? root.title : "Menu"

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
                opacity: 0.9
            }
        }
    }

    delegate: GlassMenuItem { }
}
