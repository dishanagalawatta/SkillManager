import QtQuick
import App 1.0

/*!
    \qmltype PanelResizeHandle
    \inqmlmodule SkillManagerComponents
    \brief Left-edge drag grip shared by every right-anchored side panel.

    The side panels all sit against the right edge of their host, so the only
    usable resize edge is their left one. This component owns that drag maths
    exactly once: the owning panel supplies its current ``panelWidth`` plus the
    clamp range and receives ``widthEdited`` while dragging and
    ``widthCommitted`` on release (so the caller can debounce persistence).

    Pointer-only: the OS/AT surface is the panel's own close button and
    keyboard focus order. Screen readers must not stop on a decorative grip,
    hence ``Accessible.ignored``.
*/
Item {
    id: root

    property int panelWidth: 0
    property int minimumPanelWidth: 280
    property real maximumPanelWidth: 100000

    signal widthEdited(int width)
    signal widthCommitted(int width)

    implicitWidth: 8
    implicitHeight: 0
    z: 11

    Accessible.ignored: true

    function _clamp(candidate) {
        var lower = Math.max(0, root.minimumPanelWidth)
        var upper = Math.max(lower, root.maximumPanelWidth)
        return Math.round(Math.min(upper, Math.max(lower, candidate)))
    }

    Rectangle {
        id: grip
        anchors.centerIn: parent
        width: 2
        height: Math.min(parent.height * 0.6, 160)
        radius: 1
        color: Theme.glassBorder
        opacity: (drag.pressed || drag.containsMouse) ? 1.0 : 0.0

        Behavior on opacity {
            enabled: !(AppController && AppController.ui_controller
                       && AppController.ui_controller.reducedMotion)
            NumberAnimation { duration: 120 }
        }
    }

    MouseArea {
        id: drag
        anchors.fill: parent
        anchors.leftMargin: -4
        anchors.rightMargin: -4
        hoverEnabled: true
        cursorShape: Qt.SizeHorCursor

        property int pressX: 0
        property int pressWidth: 0

        onPressed: (mouse) => {
            drag.pressX = drag.mapToGlobal(mouse.x, 0).x
            drag.pressWidth = root.panelWidth
        }

        onPositionChanged: (mouse) => {
            if (!pressed) return
            var delta = drag.mapToGlobal(mouse.x, 0).x - drag.pressX
            root.widthEdited(root._clamp(drag.pressWidth - delta))
        }

        onReleased: root.widthCommitted(root.panelWidth)
    }
}
