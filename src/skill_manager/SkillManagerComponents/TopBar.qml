import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root
    height: 64
    Layout.fillWidth: true
    Layout.minimumWidth: 200
    color: Theme.glassPill
    radius: 0 // Keep top flat or slightly rounded if desired, but following 'no feature change'
    clip: true // Prevent content overflow at narrow widths
    
    // Outer defining border
    border.width: 1
    border.color: Theme.glassOuterBorder

    // Inner highlight border (Removed for solid matte)
    Item {
        anchors.fill: parent
    }
    
    signal navigationChanged(string view)
    property string currentView: "QuickCopy"
    // --- Search expand state (future-proof, binding-safe) ---
    // When _topPhase >=1 the inline search collapses to an icon.
    // Clicking the icon sets searchExpanded=true which forces the
    // GlassSearchInput visible via declarative binding (no imperative
    // `visible = ...` that would break the QML binding).
    property bool searchExpanded: false
    function expandSearch() { searchExpanded = true; Qt.callLater(() => topSearchInput.forceActiveFocus()) }
    function collapseSearch() { searchExpanded = false }
    function focusSearch() {
        if (_topPhase >= 1 && !searchExpanded) expandSearch()
        else topSearchInput.forceActiveFocus()
    }
    on_TopPhaseChanged: if (_topPhase < 1 && searchExpanded) searchExpanded = false
    onSearchExpandedChanged: if (searchExpanded) Qt.callLater(() => topSearchInput.forceActiveFocus())

    Shortcut {
        sequence: "Escape"
        enabled: root.searchExpanded
        onActivated: root.collapseSearch()
    }

    // --- Dynamic Collapse Phases ---
    //   Phase 0: All expanded (nav labels + search bar + snap + refresh)
    //   Phase 1: Search bar → search icon
    //   Phase 2: Nav buttons → icon-only
    //   Phase 3: Snap + Settings → overflow

    readonly property int _wWorkbench: 126
    readonly property int _wLib: 93
    readonly property int _wHub: 76
    readonly property int _wSet: 103
    readonly property int _wNavIcon: 40
    readonly property int _wSnap: 32
    readonly property int _wRefresh: 32
    readonly property int _wSearchIcon: 28
    readonly property int _wOverflow: 32

    function _topCalcWidth(phase) {
        var m = 40      // 20 left + 20 right margin
        var os = 24     // spacing between nav and actions sections
        var ns = 4      // spacing between nav layout children
        var as = 8      // spacing between action items

        // Snap folds into the overflow menu at phase 3.
        var snapW = phase >= 3 ? 0 : _wSnap
        var navIcons = 4        // Workbench, Library, Hub, Settings
        var navWidth
        var navGaps
        if (phase >= 2) {
            var iconCount = phase >= 3 ? navIcons - 1 : navIcons
            navWidth = _wNavIcon * iconCount
            navGaps = iconCount        // icon buttons + the fill spacer
        } else {
            navWidth = _wWorkbench + _wLib + _wHub + _wSet
            navGaps = navIcons + 1     // labelled buttons + the fill spacer
        }
        var navW = navWidth + ns * navGaps

        if (phase === 0) {
            var searchW = Math.min(200, root.width * 0.3)
            var actW = snapW + _wRefresh + searchW + as * 2
            return m + navW + os + actW
        }
        if (phase === 1) {
            var actW1 = snapW + _wRefresh + _wSearchIcon + as * 2
            return m + navW + os + actW1
        }
        if (phase === 2) {
            var actW2 = snapW + _wRefresh + _wSearchIcon + as * 2
            return m + navW + os + actW2
        }
        // phase 3 — Snap and Settings live in the overflow menu
        var actW3 = _wOverflow + _wRefresh + _wSearchIcon + as * 2
        return m + navW + os + actW3
    }

    property int _topPhase: {
        if (_topCalcWidth(0) <= root.width) return 0
        if (_topCalcWidth(1) <= root.width) return 1
        if (_topCalcWidth(2) <= root.width) return 2
        return 3
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.width < 440 ? 12 : 20
        anchors.rightMargin: root.width < 440 ? 12 : 20
        spacing: root.width < 440 ? 12 : 24

        // Navigation
        RowLayout {
            id: navRow
            Layout.fillWidth: !root.searchExpanded
            visible: !root.searchExpanded
            opacity: root.searchExpanded ? 0 : 1
            spacing: 4
            Behavior on opacity { NumberAnimation { duration: 180 } }
            
            TopBarButton {
                objectName: "navWorkbench"
                iconSource: AppController.ui_controller.getAssetUri("ui/lightning-icon.svg")
                labelText: "Workbench"
                tooltipText: "Workbench — project skills and tasks"
                visible: true
                showLabel: root._topPhase < 2
                Layout.alignment: Qt.AlignVCenter
                active: root.currentView === "Quick Copy" || root.currentView === "QuickCopy"
                onClicked: (mouse) => { 
                    root.currentView = "Quick Copy"; 
                    root.navigationChanged("Quick Copy") 
                }
            }

            TopBarButton {
                objectName: "navLibrary"
                iconSource: AppController.ui_controller.getAssetUri("ui/library-icon.svg")
                labelText: "Library"
                visible: true
                showLabel: root._topPhase < 2
                Layout.alignment: Qt.AlignVCenter
                active: root.currentView === "Library"
                onClicked: (mouse) => { 
                    root.currentView = "Library"
                    root.navigationChanged("Library") 
                }
            }

            TopBarButton {
                objectName: "navUpdates"
                iconSource: AppController.ui_controller.getAssetUri("ui/folder-sync-icon.svg")
                labelText: "Hub"
                tooltipText: "Hub — installed packages and project sync"
                visible: true
                showLabel: root._topPhase < 2
                Layout.alignment: Qt.AlignVCenter
                active: root.currentView === "Updates"
                onClicked: (mouse) => { root.currentView = "Updates"; root.navigationChanged("Updates") }
            }

            TopBarButton {
                objectName: "navSettings"
                iconSource: AppController.ui_controller.getAssetUri("ui/settings-icon.svg")
                labelText: "Settings"
                visible: root._topPhase < 3
                showLabel: root._topPhase < 2
                Layout.alignment: Qt.AlignVCenter
                active: root.currentView === "Settings"
                onClicked: (mouse) => { root.currentView = "Settings"; root.navigationChanged("Settings") }
            }

            Item { Layout.fillWidth: true }
        }
        

        RowLayout {
            spacing: 8

            GlassPill {
                objectName: "topStatusPill"
                visible: false
                Layout.preferredHeight: 32
                Layout.preferredWidth: 80

                Text {
                    objectName: "topStatusText"
                    text: AppController.statusMessage
                }
            }

            IconButton {
                id: topSnapBtn
                objectName: "topSnapBtn"
                visible: root._topPhase < 3 && !root.searchExpanded
                buttonSize: 32
                iconSource: AppController.ui_controller.getAssetUri("ui/snap-icon.svg")
                tooltipText: "Take a snap"
                onClicked: (mouse) => AppController.snap_controller.takeSnap()
                background: Rectangle {
                    radius: 16
                    color: topSnapBtn.hovered ? Theme.glassHover : "transparent"
                    border.color: Theme.alpha(Theme.label, 0.15)
                    border.width: 1
                }
                Layout.alignment: Qt.AlignVCenter
            }

            IconButton {
                id: topRefreshBtn
                visible: root._topPhase < 3 && !root.searchExpanded
                buttonSize: 32
                iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                tooltipText: "Refresh skill library"
                onClicked: (mouse) => AppController.refreshSkills("manual-button", true)
                background: Rectangle {
                    radius: 16
                    color: topRefreshBtn.hovered ? Theme.glassHover : "transparent"
                    border.color: Theme.alpha(Theme.label, 0.15)
                    border.width: 1
                }
                Layout.alignment: Qt.AlignVCenter
            }

            IconButton {
                id: topOverflowBtn
                visible: root._topPhase >= 3 && !root.searchExpanded
                iconText: "⋮"
                iconSize: 24
                buttonSize: 32
                // AT matrix: overflow action => tooltipText "More actions" as Accessible name (never the bare glyph).
                tooltipText: "More actions"
                Layout.alignment: Qt.AlignVCenter
                background: Rectangle {
                    radius: 16
                    color: topOverflowBtn.hovered ? Theme.glassHover : "transparent"
                    border.color: Theme.alpha(Theme.label, 0.15)
                    border.width: 1
                }
                onClicked: topOverflowMenu.popup(topOverflowBtn, 0, topOverflowBtn.height + 4)

                GlassMenu {
                    id: topOverflowMenu
                    GlassMenuItem {
                        text: "Take Snap"
                        iconSource: AppController.ui_controller.getAssetUri("ui/snap-icon.svg")
                        onTriggered: AppController.snap_controller.takeSnap()
                    }
                    GlassMenuItem {
                        text: "Refresh"
                        iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                        onTriggered: AppController.refreshSkills("manual-button", true)
                    }
                    GlassMenuItem {
                        text: "Settings"
                        iconSource: AppController.ui_controller.getAssetUri("ui/settings-icon.svg")
                        visible: root.currentView !== "Settings"
                        onTriggered: { root.currentView = "Settings"; root.navigationChanged("Settings") }
                    }
                }
            }

            GlassSearchInput {
                id: topSearchInput
                objectName: "topSearchInput"
                visible: root._topPhase < 1 || root.searchExpanded
                Layout.fillWidth: true
                Layout.minimumWidth: root.searchExpanded ? 120 : 50
                Layout.maximumWidth: root.searchExpanded ? Math.min(420, root.width - 80) : Math.min(200, root.width * 0.3)
                Layout.alignment: Qt.AlignVCenter
                // Smooth width/opacity transition when expanding via searchExpanded
                Behavior on Layout.maximumWidth { NumberAnimation { duration: 220; easing.type: Easing.InOutQuad } }
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 160 } }

                Keys.onEscapePressed: (event) => { if (root.searchExpanded) { root.collapseSearch(); event.accepted = true } }
                onActiveFocusChanged: {
                    // Auto-collapse when focus lost and text empty in collapsed-phase mode
                    if (!activeFocus && root.searchExpanded && text === "" && root._topPhase >= 1) {
                        // delay allows clear-button clicks to fire before collapse
                        Qt.callLater(() => { if (!topSearchInput.activeFocus) root.collapseSearch() })
                    }
                }

                onDebouncedTextChanged: (text) => {
                    if (root.currentView === "Quick Copy" || root.currentView === "QuickCopy") {
                        AppController.quickCopyModel.filterText = text
                    } else if (root.currentView === "Library") {
                        AppController.libraryModel.filterText = text
                    }
                }
                
                Connections {
                    target: root
                    function onCurrentViewChanged() {
                        if (root.currentView === "Quick Copy" || root.currentView === "QuickCopy") {
                            topSearchInput.text = AppController.quickCopyModel.filterText
                        } else if (root.currentView === "Library") {
                            topSearchInput.text = AppController.libraryModel.filterText
                        } else {
                            topSearchInput.text = ""
                        }
                    }
                }
            }

            IconButton {
                id: topSearchIconBtn
                objectName: "topSearchIconBtn"
                visible: root._topPhase >= 1 && !root.searchExpanded
                buttonSize: 28
                iconSource: AppController.ui_controller.getAssetUri("ui/search-icon.svg")
                tooltipText: "Search skills"
                role: "ghost"
                Layout.alignment: Qt.AlignVCenter
                background: Rectangle {
                    radius: 14
                    color: topSearchIconBtn.hovered ? Theme.glassHover : "transparent"
                    border.color: Theme.alpha(Theme.label, 0.15)
                    border.width: 1
                }
                onClicked: (mouse) => root.expandSearch()
            }

            IconButton {
                objectName: "topSearchCloseBtn"
                visible: root.searchExpanded
                buttonSize: 28
                // Circular plate icon: no resting outline (see IconButton.showRing).
                showRing: false
                iconSource: AppController.ui_controller.getAssetUri("ui/close-icon.svg")
                tooltipText: "Close search"
                role: "ghost"
                Layout.alignment: Qt.AlignVCenter
                onClicked: (mouse) => root.collapseSearch()
            }
        }




    }
}
