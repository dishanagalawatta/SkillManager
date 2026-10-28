import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

/*!
    \qmltype SidePanel
    \inqmlmodule SkillManagerComponents
    \brief Shared shell for every right-anchored side panel.

    The panel owns the parts that must never drift between panels: the matte
    surface, the header (title, optional counter badge, close button), the
    left-edge resize grip, width persistence and the open/close fade.

    Hosts only supply the content, by declaring children:

    \code
    SidePanel {
        anchors.fill: parent
        topMargin: headerRow.height
        open: AppController.ui_controller.somePanelOpen
        title: "Tasks"
        widthKey: "quickcopy.tasks"
        onCloseRequested: AppController.ui_controller.setSomePanelOpen(false)

        ColumnLayout { Layout.fillWidth: true; Layout.fillHeight: true }
    }
    \endcode

    The host must fill its parent; the shell positions itself against the right
    edge and offsets by \l topMargin so it never covers the header ribbon.
    Closing is reported through \l closeRequested so the owner stays the single
    source of truth for the open state.

    \property string title
        Header text. Empty renders a header-less panel (close button only).
    \property string badgeText
        Optional counter pill rendered after the title, e.g. "2 Open - 1 Done".
    \property string widthKey
        Persistence key for the user-set width, e.g. "quickcopy.tasks".
        Empty disables persistence.
    \property bool open
        Whether the panel is shown. Owned by the host.
    \property bool resizable
        Enables the left-edge drag grip.
    \property bool showClose
        Enables the header close button.
    \property int preferredWidth
        Width used until the user resizes the panel.
    \property int minimumPanelWidth
        Lower clamp for both the preferred and the user-set width.
    \property real topMargin
        Vertical offset from the host's top edge.
    \property alias content
        Default property; the panel body.
*/
Item {
    id: root

    // ── Content slot ────────────────────────────────────────────────
    default property alias content: body.data

    // ── Identity ────────────────────────────────────────────────────
    property string title: ""
    property string badgeText: ""
    property string widthKey: ""

    // ── Behaviour ───────────────────────────────────────────────────
    property bool open: false
    property bool resizable: true
    property bool showClose: true
    property int preferredWidth: 340
    property int minimumPanelWidth: 280
    property real topMargin: 8

    signal closeRequested()

    // Animations are decorative: the reduced-motion preference turns them off.
    readonly property bool _motion: !(AppController && AppController.ui_controller
                                      && AppController.ui_controller.reducedMotion)

    // 0 means "never resized"; fall back to the panel's own preferred width.
    property int _savedWidth: 0
    readonly property int panelWidth: root._savedWidth > 0
        ? Math.max(root.minimumPanelWidth, root._savedWidth)
        : Math.max(root.minimumPanelWidth, root.preferredWidth)

    // ── Surface + layout ────────────────────────────────────────────
    Rectangle {
        id: surface
        objectName: "sidePanelSurface"

        x: root.width - width
        y: root.topMargin
        width: root.panelWidth
        height: Math.max(0, root.height - root.topMargin)

        radius: Theme.radiusCard
        color: Theme.glassPill
        border.color: Theme.glassBorder
        border.width: 1
        clip: true

        visible: root.open || opacity > 0.001
        opacity: root.open ? 1.0 : 0.0

        Behavior on opacity {
            enabled: root._motion
            NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
        }

        ColumnLayout {
            id: shell
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            // ── Header ──────────────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: root.title
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    elide: Text.ElideRight
                    Accessible.role: Accessible.Heading
                    Accessible.name: root.title
                    Accessible.ignored: root.title === ""
                }

                Rectangle {
                    id: badge
                    visible: root.badgeText !== ""
                    Layout.preferredWidth: Math.max(24, badgeLabel.implicitWidth + 14)
                    Layout.preferredHeight: 22
                    radius: 11
                    color: Theme.glassHover
                    border.color: Theme.glassBorder
                    border.width: 1

                    Accessible.role: Accessible.StaticText
                    Accessible.name: root.badgeText

                    Text {
                        id: badgeLabel
                        anchors.centerIn: parent
                        text: root.badgeText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        color: Theme.secondaryLabel
                    }
                }

                IconButton {
                    objectName: "sidePanelClose"
                    visible: root.showClose
                    buttonSize: 28
                    iconSize: 18
                    // The icon is a circular plate; a resting outline would
                    // draw a second ring around it.
                    showRing: false
                    iconSource: AppController.ui_controller.getAssetUri("ui/close-icon.svg")
                    tooltipText: root.title !== "" ? ("Close " + root.title) : "Close panel"
                    onClicked: root.closeRequested()
                }
            }

            // ── Body ────────────────────────────────────────────────
            ColumnLayout {
                id: body
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10
            }
        }
    }

    // ── Resize grip ─────────────────────────────────────────────────
    PanelResizeHandle {
        objectName: "sidePanelResizeGrip"

        visible: root.resizable && root.open
        x: surface.x - width
        y: surface.y
        height: surface.height
        panelWidth: root.panelWidth
        minimumPanelWidth: root.minimumPanelWidth
        maximumPanelWidth: Math.max(root.minimumPanelWidth, root.width * 0.85)

        onWidthEdited: (w) => root._savedWidth = w
        onWidthCommitted: (w) => persistTimer.restart()
    }

    // ── Width persistence ───────────────────────────────────────────
    Timer {
        id: persistTimer
        interval: 150
        repeat: false
        onTriggered: {
            if (root.widthKey !== "" && root._savedWidth > 0)
                AppController.ui_controller.setPanelWidth(root.widthKey, root._savedWidth)
        }
    }

    Component.onCompleted: {
        if (root.widthKey === "") return
        var saved = AppController.ui_controller.getPanelWidth(root.widthKey)
        if (saved > 0) root._savedWidth = saved
    }
}
