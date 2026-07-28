import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

/*!
    Self-contained ImageInspector wrapper.  Used by ``SkillInspectorOverlay``
    so the hosting views (LibraryView, QuickCopyView) do not need to
    reference ``ImageInspector`` directly.

    Mirrored properties: ``skill``, ``x``, ``y``, ``width``, ``height``.

    Forwarded signals: ``widthChange`` (from inner ``widthChanged``),
    ``close`` (from inner ``closed``).
 */
Item {
    id: root

    // ── Mirrored Properties ─────────────────────────────────────
    property var skill: AppController.selectedSkill
    property bool overlayVisible: false

    // ── Forwarded Signals (renamed to avoid clashing with
    //    Item's built-in `widthChanged` / `closed`).          ─────
    signal widthChange()
    signal close()

    // ── ImageInspector ───────────────────────────────────────────
    ImageInspector {
        id: _imageInspector
        skill: root.skill
        x: 0; y: 0
        width: root.width
        height: root.height
    }

    // Forward inner signals with renamed identifiers.
    Connections {
        target: _imageInspector
        function onWidthChanged() { root.widthChange() }
        function onClosed() { root.close() }
    }
}
