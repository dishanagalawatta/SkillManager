import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import "dialogs"

/*!
    Self-contained CommandInspector with its own ``CommandCreateDialog`` and
    ``CommandDeleteDialog``.  Used by ``SkillInspectorOverlay`` so the hosting
    views (LibraryView, QuickCopyView) do not need to manage these dialogs.

    Mirrored properties: ``skill``, ``overlayVisible``, ``x``, ``y``,
    ``width``, ``height``.

    Mirrored signals: ``widthChanged``, ``closed``.
 */
Item {
    id: root

    // ── Mirrored Properties ─────────────────────────────────────
    property var  skill: null
    property bool overlayVisible: false

    // ── Exposed Dialogs ─────────────────────────────────────────
    property alias cmdDeleteDialog: _cmdDeleteDialog

    // ── Forwarded Signals (renamed to avoid clashing with
    //    Item's built-in `widthChanged` / `closed`).          ─────
    signal widthChange()
    signal close()

    // ── CommandInspector ────────────────────────────────────────
    CommandInspector {
        id: _cmdInspector
        skill: root.skill
        editDialog: _commandDialog
        overlayVisible: root.overlayVisible
        x: 0; y: 0
        width: root.width
        height: root.height

        onDeleteRequested: (name, path, isCommand) => {
            var holders = AppController.commandProjectsForPath(path) || []
            if (holders.length === 0) holders = [AppController.currentProject || ""]
            _cmdDeleteDialog.openForCommand(name, holders)
        }
    }

    Connections {
        target: _cmdInspector
        function onWidthChanged() { root.widthChange() }
        function onClosed() { root.close() }
    }

    // ── Internal Dialogs ────────────────────────────────────────
    CommandCreateDialog {
        id: _commandDialog
    }

    CommandDeleteDialog {
        id: _cmdDeleteDialog
    }
}
