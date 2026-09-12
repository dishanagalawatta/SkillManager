import QtQuick
import QtQuick.Controls
import App 1.0

ListView {
    id: root

    ScrollBar.vertical: AppScrollBar {
        interactive: true
    }

    cacheBuffer: Math.max(height * 2, 1000)

    // Perf: pool and recycle delegates instead of destroying/recreating them on
    // scroll, cutting allocation and GC overhead on long lists (Library, Updates, QuickCopy).
    reuseItems: true

    // Optimization: defer heavy layout generation while scrolling fast
    property bool isScrollingFast: false

    onMovementStarted: {
        isScrollingFast = true
    }

    onMovementEnded: {
        isScrollingFast = false
    }

    // ── Collapse/expand scroll preservation (opt-in) ─────────────
    // Set collapseModel to the SkillModel driving this view plus
    // preserveOnCollapse: true to keep the viewport stable when a
    // category section is collapsed/expanded. Filter/search passes never
    // emit collapsedCategoriesChanged, so they keep jump-to-top behavior.
    // All other SmoothListView users (dropdowns, font pickers, Updates)
    // leave the default off and are unaffected.
    property var collapseModel: null
    property bool preserveOnCollapse: false

    // No initializers: these are assigned imperatively by the machine below,
    // and an initializer would be reported as an overwritten binding.
    // Defaults (0/false/""/undefined) are exactly what the machine expects.
    property real savedScrollPos
    property bool _restoringScroll
    property bool _collapsePreserve
    property string _toggledSection
    property var _prevCollapsed
    // Above-viewport shift compensation: pre-toggle geometry of the toggled
    // section (measured, never assumed — delegate heights are QML-side).
    // _toggleTopY: y of the section's first row; _toggleP: end of section
    // content (insertion/removal point); _hBefore: contentHeight. -1 = unknown.
    property real _toggleTopY
    property real _toggleP
    property real _hBefore

    // Visual blink masks micro-jumps during background refresh only;
    // collapse/expand restores instantly with no flicker.
    opacity: (preserveOnCollapse && AppController.isLoading && _restoringScroll) ? 0.0 : 1.0
    Behavior on opacity { NumberAnimation { duration: 150 } }

    onCollapseModelChanged: _syncCollapsedBaseline()
    Component.onCompleted: _syncCollapsedBaseline()

    function _syncCollapsedBaseline() {
        if (!preserveOnCollapse || !collapseModel || !collapseModel.collapsedCategories) return
        _prevCollapsed = collapseModel.collapsedCategories.slice()
    }

    function _noteCollapseToggled() {
        if (!preserveOnCollapse || !collapseModel) return
        // collapsedCategoriesChanged carries no payload, so diff against
        // the baseline to identify the toggled section for header anchoring.
        // Multi-section changes (Collapse All / Expand All) skip anchoring
        // and keep the clamped absolute restore.
        var cur = collapseModel.collapsedCategories ? collapseModel.collapsedCategories.slice() : []
        var prev = _prevCollapsed || []
        var added = cur.filter(function (c) { return prev.indexOf(c) === -1 })
        var removed = prev.filter(function (c) { return cur.indexOf(c) === -1 })
        _toggledSection = (added.length + removed.length === 1)
            ? (added.length === 1 ? added[0] : removed[0])
            : ""
        _prevCollapsed = cur
        savedScrollPos = root.contentY
        _collapsePreserve = true
        // Snapshot the section's on-screen range before the layout pair
        // rebuilds the rows. itemAtIndex returns null for far-off rows —
        // then compensation is skipped and the clamped restore stands.
        _hBefore = root.contentHeight
        _toggleTopY = -1
        _toggleP = -1
        if (_toggledSection !== "") {
            var idx0 = collapseModel.firstVisibleRowForCategory(_toggledSection)
            if (idx0 >= 0) {
                var it0 = root.itemAtIndex(idx0)
                if (it0) {
                    _toggleTopY = it0.y
                    var n = collapseModel.visibleRowCountForCategory(_toggledSection)
                    if (n > 0) {
                        var itEnd = root.itemAtIndex(idx0 + n - 1)
                        if (itEnd) _toggleP = itEnd.y + itEnd.height
                    }
                }
            }
        }
    }

    function _noteLayoutAboutToChange() {
        if (!preserveOnCollapse) return
        savedScrollPos = root.contentY
        root.cacheBuffer = 0 // Safely abort active incubators
    }

    function _restoreCacheBuffer() {
        if (!preserveOnCollapse || !root.model) return
        var incubating = collapseModel ? collapseModel.incubating : false
        if (!incubating) root.cacheBuffer = Math.max(root.height * 2, 1000)
    }

    function _restoreScroll() {
        var shouldRestore = AppController.isLoading || _collapsePreserve
        if (!shouldRestore) return
        if (!(savedScrollPos > 0)) {
            _disarmCollapse()
            return
        }
        _restoringScroll = true

        // Force immediate layout to ensure contentHeight is valid for restore
        root.forceLayout()
        // Clamp: collapsing shrinks contentHeight, a stale offset must not overshoot.
        var maxY = Math.max(0, root.contentHeight - root.height)
        root.contentY = Math.min(savedScrollPos, maxY)

        // Second pass: ensure it stuck (sometimes required for large additions)
        Qt.callLater(function () {
            root.forceLayout()
            var maxY2 = Math.max(0, root.contentHeight - root.height)
            var finalY = _compensateShift(savedScrollPos, maxY2)
            if (Math.abs(root.contentY - finalY) > 1) root.contentY = finalY
            _anchorToggledHeader()
            _restoringScroll = false
            _disarmCollapse()
        })
    }

    function _disarmCollapse() {
        _collapsePreserve = false
        _toggledSection = ""
        _toggleTopY = -1
        _toggleP = -1
        _hBefore = 0
    }

    function _compensateShift(y0, maxY) {
        // Keep the content under the viewport stable when the toggled section
        // sits above it. Expand inserts g px at _toggleP (end of the collapsed
        // section): everything below shifts down. Collapse removes r px over
        // [_toggleTopY, _toggleP]: everything below shifts up; a viewport top
        // inside the removed range snaps to the section start. Unmeasurable
        // geometry (-1) keeps the clamped absolute restore. Single final clamp.
        var target = y0
        if (_collapsePreserve && _toggledSection !== "") {
            var g = root.contentHeight - _hBefore
            if (g > 0) {
                if (_toggleP >= 0 && _toggleP <= y0) target += g
            } else if (g < 0) {
                var r = -g
                if (_toggleP >= 0 && _toggleTopY >= 0) {
                    if (_toggleP <= y0) target -= r
                    else if (_toggleTopY < y0) target = _toggleTopY
                }
            }
        }
        return Math.max(0, Math.min(target, maxY))
    }

    function _anchorToggledHeader() {
        // Pin the toggled section header only when it is currently visible
        // (the user's focus context). Distant sections keep the absolute
        // restore so collapsing below the fold never yanks the viewport.
        // ListView.Contain moves the viewport only if the header is outside it.
        if (!_collapsePreserve || _toggledSection === "" || !collapseModel) return
        var idx = collapseModel.firstVisibleRowForCategory(_toggledSection)
        if (idx < 0) return
        var item = root.itemAtIndex(idx)
        if (!item) return
        var iy = item.y
        if (iy + item.height > root.contentY && iy < root.contentY + root.height) {
            root.positionViewAtIndex(idx, ListView.Contain)
        }
    }

    Connections {
        target: root.collapseModel
        enabled: root.preserveOnCollapse
        function onCollapsedCategoriesChanged() { root._noteCollapseToggled() }
        function onLayoutAboutToBeChanged() { root._noteLayoutAboutToChange() }
        function onLayoutChanged() { root._restoreCacheBuffer(); root._restoreScroll() }
        function onModelAboutToBeReset() { root._noteLayoutAboutToChange() }
        function onModelReset() { root._restoreCacheBuffer(); root._restoreScroll() }
        function onRowsAboutToBeRemoved() { root._noteLayoutAboutToChange() }
        function onRowsRemoved() { root._restoreCacheBuffer(); root._restoreScroll() }
        function onRowsAboutToBeInserted() { root._noteLayoutAboutToChange() }
        function onRowsInserted() { root._restoreCacheBuffer(); root._restoreScroll() }
        function onAboutToMutateStructure() { root._noteLayoutAboutToChange() }
        function onStructureMutated() { root._restoreCacheBuffer(); root._restoreScroll() }
        function onIncubatingChanged() {
            // Deferred restore while incubating: a layout reset mid-incubation
            // re-triggers a delegate burst racing the in-flight one
            // ("Object or context destroyed during incubation").
            if (!root.collapseModel) return
            if (!root.collapseModel.incubating) {
                root.collapseModel.onIncubationReady()
                if (root.model) {
                    root.cacheBuffer = Math.max(root.height * 2, 1000)
                    root._restoreScroll()
                }
            } else {
                root.cacheBuffer = 0
            }
        }
    }

    WheelHandler {
        target: root
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: (event) => {
            let config = AppController.config_controller
            let multiplier = (config && typeof config.scrollSpeedMultiplier !== "undefined") ? config.scrollSpeedMultiplier : 1.0

            if (Math.abs(multiplier - 1.0) < 0.01) {
                event.accepted = false
                return
            }

            event.accepted = true

            if (event.pixelDelta.y !== 0) {
                let scrollAmount = event.pixelDelta.y * multiplier
                root.contentY = Math.max(root.originY,
                                         Math.min(root.contentY - scrollAmount,
                                                  root.originY + Math.max(0, root.contentHeight - root.height)))
                return
            }

            let scrollAmount = event.angleDelta.y * (multiplier * 0.5)
            root.contentY = Math.max(root.originY,
                                     Math.min(root.contentY - scrollAmount,
                                              root.originY + Math.max(0, root.contentHeight - root.height)))
        }
    }
}
