import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control

    implicitWidth: 8
    policy: ScrollBar.AsNeeded
    interactive: true

    contentItem: Rectangle {
        implicitWidth: 6
        radius: 3
        color: Theme.secondaryLabel

        // Fully visible while scrolling / hovered / pressed, otherwise
        // fade out. The 200ms timer for the previous auto-hide behaviour
        // was removed because in Qt 6.11.1 any QML Timer child of a
        // control hits the "Cannot assign object of type X to list property
        // 'data'; expected 'QObject'" strict-type-check bug.
        opacity: (control.active || control.hovered || control.pressed) ? 0.8 : 0.0

        Behavior on opacity { NumberAnimation { duration: 250 } }
    }

    background: Item {
        implicitWidth: 8
    }
}
