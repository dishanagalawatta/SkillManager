import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

/*!
    Shared inspector overlay used by both LibraryView and QuickCopyView.

    Encapsulates the three inspectors (CommandInspector, SkillInspector,
    ImageInspector), the popup/side-panel layout, the resize handle,
    and the ``onSelectedSkillChanged`` toggle logic.

    The hosting view passes:
    - ``isQuickCopy``      – forwarded to SkillInspector (changes header layout)
    - ``usePopupMode``     – true  → centred popup with backdrop
                             false → right-anchored side-panel with resize handle
    - ``selectedSkillValid`` – gates overlay visibility

    The ``CommandInspectorPanel`` inside handles its own ``CommandCreateDialog``
    and ``CommandDeleteDialog`` internally.  The dialogs are accessible via
    ``commandPanel.cmdDeleteDialog`` so the host view can open them from
    ``SkillItem.onDeleteRequested``.

    Exposes ``forceImageInspector()`` for ``SkillItem.onInspectImageRequested``.
 */
Item {
    id: root

    // ── Public Properties ────────────────────────────────────────
    property bool isQuickCopy: false
    property bool usePopupMode: false
    // Vertical top margin (dynamic offset from top of view so side-panels do not cover the header ribbon)
    property real topMargin: 0
    // Calculate internally so bindings update reliably even in
    // QQmlComponent test environments (cross-module bindings can stall).
    readonly property bool selectedSkillValid:
        AppController.selectedSkill
        && AppController.selectedSkill.local_path !== undefined
        && AppController.selectedSkill.local_path !== ""

    // Inspector visibility flags (read/write — the view or this component sets them)
    property bool showCommandInspector: false
    property bool showSkillInspector: false
    property bool showImageInspector: false

    // Exposed so the host view can open the delete dialog for list-item deletions.
    property alias cmdDeleteDialog: commandPanel.cmdDeleteDialog

    // ── Signals ─────────────────────────────────────────────────
    signal inspectorClosed()

    // ── Backdrop (popup mode only) ──────────────────────────────
    readonly property bool _anyInspectorVisible: root.selectedSkillValid && (root.showCommandInspector || root.showSkillInspector || root.showImageInspector)

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        visible: root.usePopupMode && root._anyInspectorVisible
        opacity: (root.usePopupMode && root._anyInspectorVisible) ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: 200 } }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.showCommandInspector = false
                root.showImageInspector = false
                root.showSkillInspector = false
                AppController.ui_controller.selectSkill(-1)
                root.inspectorClosed()
            }
        }
    }

    // ── Width / Positioning ─────────────────────────────────────
    // Side-panel (default): right-aligned, full height, draggable resize handle.
    // Popup mode: centred, sized to fit.
    readonly property int _popupW: Math.min(parent ? parent.width * 0.92 : root.width * 0.92, 560)
    readonly property int _popupH: Math.min(parent ? parent.height * 0.88 : root.height * 0.88, 700)
    readonly property int _popupX: Math.round(((parent ? parent.width : root.width) - _popupW) / 2)
    readonly property int _popupY: Math.round(((parent ? parent.height : root.height) - _popupH) / 2)

    // Side-panel geometry (usePopupMode = false)
    property int _savedPanelW: 0   // persisted, > 0 = user-set override
    property int _panelX: (parent ? parent.width : root.width) - _panelW
    property int _panelW: _savedPanelW > 0 ? _clampedUserW : _autoW
    property int _autoW: {
        var baseMin = root.showImageInspector ? 320
                    : root.showCommandInspector ? 300
                    : root.showSkillInspector ? 300
                    : 300
        return Math.max(baseMin, root.width * 0.5)
    }
    property int _clampedUserW: {
        var baseMin = root.showImageInspector ? 320
                    : root.showCommandInspector ? 300
                    : root.showSkillInspector ? 300
                    : 300
        var maxContainerW = parent ? parent.width : root.width
        return Math.max(baseMin, Math.min(maxContainerW * 0.85, _savedPanelW))
    }

    // Debouncer for persisting panel width to AppController.
    property int _debouncedWidth: 0
    Timer {
        id: _widthDebouncer
        interval: 150
        repeat: false
        onTriggered: {
            if (root._debouncedWidth > 0)
                AppController.ui_controller.setInspectorWidth(root._debouncedWidth)
        }
    }

    // Restore saved width on construction.
    Component.onCompleted: {
        var saved = AppController.ui_controller.inspectorWidth
        if (saved > 0) _savedPanelW = saved
    }

    // ── Resize Handle (side-panel mode only) ────────────────────
    Rectangle {
        id: resizeHandle
        x: root._panelX - width
        y: root.usePopupMode ? 0 : root.topMargin
        width: 6
        height: root.usePopupMode ? (parent ? parent.height : root.height) : (parent ? parent.height - root.topMargin : root.height - root.topMargin)
        z: 11
        visible: !root.usePopupMode && root._anyInspectorVisible

        color: resizeMouse.containsMouse || resizeMouse.pressed
               ? Qt.rgba(1, 1, 1, 0.25) : "transparent"

        Rectangle {
            anchors.centerIn: parent
            width: 2
            height: parent.height * 0.6
            color: Qt.rgba(1, 1, 1, (resizeMouse.containsMouse || resizeMouse.pressed) ? 0.15 : 0)
            radius: 1
        }

        MouseArea {
            id: resizeMouse
            anchors.fill: parent
            anchors.leftMargin: -4
            anchors.rightMargin: -4
            hoverEnabled: true
            cursorShape: Qt.SizeHorCursor

            property int pressScreenX: 0
            property int pressPanelW: 0

            onPressed: {
                pressScreenX = mapToGlobal(mouse.x, 0).x
                pressPanelW = root._panelW
            }
            onPositionChanged: {
                if (!pressed) return
                var curX = mapToGlobal(mouse.x, 0).x
                var delta = curX - pressScreenX
                var newW = pressPanelW - delta
                var baseMin = root.showImageInspector ? 320
                            : root.showCommandInspector ? 300
                            : 300
                var maxW = (parent && parent.parent ? parent.parent.width : root.width) * 0.85
                root._savedPanelW = Math.max(baseMin, Math.min(maxW, newW))
            }
            onReleased: {
                root._debouncedWidth = root._panelW
                _widthDebouncer.restart()
            }
        }
    }

    // ── CommandInspector (self-contained with its own dialogs) ──
    CommandInspectorPanel {
        id: commandPanel
        skill: AppController.selectedSkill
        overlayVisible: root.selectedSkillValid && root.showCommandInspector
        visible: root.selectedSkillValid && root.showCommandInspector
        x: root.usePopupMode ? root._popupX : root._panelX
        y: root.usePopupMode ? root._popupY : root.topMargin
        width:  root.usePopupMode ? root._popupW : root._panelW
        height: root.usePopupMode ? root._popupH : (parent ? parent.height - root.topMargin : root.height - root.topMargin)

        onWidthChange: {
            if (visible && width > 0 && !root.usePopupMode) {
                root._debouncedWidth = width
                _widthDebouncer.restart()
            }
        }
        onClose: {
            root.showCommandInspector = false
            AppController.ui_controller.selectSkill(-1)
            root.inspectorClosed()
        }
    }

    // ── SkillInspector ──────────────────────────────────────────
    SkillInspector {
        id: inspector
        skill: AppController.selectedSkill
        isQuickCopy: root.isQuickCopy
        overlayVisible: root.selectedSkillValid && root.showSkillInspector
        visible: root.selectedSkillValid && root.showSkillInspector
        x: root.usePopupMode ? root._popupX : root._panelX
        y: root.usePopupMode ? root._popupY : root.topMargin
        width:  root.usePopupMode ? root._popupW : root._panelW
        height: root.usePopupMode ? root._popupH : (parent ? parent.height - root.topMargin : root.height - root.topMargin)

        onWidthChanged: {
            if (visible && width > 0 && !root.usePopupMode) {
                root._debouncedWidth = width
                _widthDebouncer.restart()
            }
        }
        onClosed: {
            root.showSkillInspector = false
            AppController.ui_controller.selectSkill(-1)
            root.inspectorClosed()
        }
    }

    // ── ImageInspector (self-contained panel) ───────────────────
    ImageInspectorPanel {
        id: imagePanel
        skill: AppController.selectedSkill
        overlayVisible: root.selectedSkillValid && root.showImageInspector
        visible: root.selectedSkillValid && root.showImageInspector
        x: root.usePopupMode ? root._popupX : root._panelX
        y: root.usePopupMode ? root._popupY : root.topMargin
        width:  root.usePopupMode ? root._popupW : root._panelW
        height: root.usePopupMode ? root._popupH : (parent ? parent.height - root.topMargin : root.height - root.topMargin)

        onWidthChange: {
            if (visible && width > 0 && !root.usePopupMode) {
                root._debouncedWidth = width
                _widthDebouncer.restart()
            }
        }
        onClose: {
            root.showImageInspector = false
            AppController.ui_controller.selectSkill(-1)
            root.inspectorClosed()
        }
    }

    // ── Inspector Toggle Logic ──────────────────────────────────
    // When the selected skill changes, determine which inspector to show
    // and imperatively set visibility to bypass QML's binding staleness bug.
    Connections {
        target: AppController
        function onSelectedSkillChanged() {
            var skill = AppController.selectedSkill
            var isCommand = !!(skill && skill.is_command)
            var isSnap = !!(skill && skill.is_snap)
            // Calculate directly instead of reading via binding chain
            // to avoid staleness in the QQmlComponent test environment.
            var sv = !!(skill && skill.local_path !== undefined && skill.local_path !== "")
            var showSkill = !isCommand && !isSnap && sv

            // DIAG: log what QML sees for body_content
            var bc = (skill && skill.body_content) || ""
            console.log("INSPECTOR_DIAG: onSelectedSkillChanged"
                + " path=" + (skill ? (skill.local_path || "NONE") : "NONE")
                + " bcLen=" + bc.length
                + " bcPreview=" + (bc.length > 0 ? bc.substring(0, 60) : "(empty)")
                + " isCmd=" + isCommand + " isScr=" + isSnap
                + " sv=" + sv + " showSkill=" + showSkill)

            root.showCommandInspector = isCommand
            root.showImageInspector = isSnap
            root.showSkillInspector = showSkill

            // Imperative visible + overlayVisible to bypass QML binding staleness.
            commandPanel.visible = isCommand
            commandPanel.overlayVisible = isCommand
            imagePanel.visible = isSnap
            inspector.visible = showSkill
            inspector.overlayVisible = showSkill
        }
    }

    // ── Public Helpers ──────────────────────────────────────────
    function forceImageInspector() {
        root.showImageInspector = true
        root.showCommandInspector = false
        root.showSkillInspector = false
        commandPanel.visible = false
        commandPanel.overlayVisible = false
        inspector.visible = false
        inspector.overlayVisible = false
    }
}
