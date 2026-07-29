import QtQuick
import Qt5Compat.GraphicalEffects
import "."

Item {
    id: root

    property Item sourceItem: null
    property color primaryColor: Theme.darkMode ? "#F3F4F6" : "#000000"
    property color secondaryColor: Theme.darkMode ? Qt.rgba(1, 1, 1, 0.35) : "#E2E8F0"

    anchors.fill: sourceItem
    visible: sourceItem !== null

    ColorOverlay {
        id: overlay
        anchors.fill: parent
        source: root.sourceItem
        color: root.primaryColor
        visible: root.sourceItem !== null
    }
}
