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

    // --- Dynamic Collapse Phases ---
    //   Phase 0: All expanded (nav labels + search bar + refresh)
    //   Phase 1: Search bar → search icon
    //   Phase 2: Nav buttons → icon-only
    //   Phase 3: Refresh + Settings → overflow

    readonly property int _wSnap: 88
    readonly property int _wQC: 118
    readonly property int _wLib: 93
    readonly property int _wUpd: 98
    readonly property int _wSet: 103
    readonly property int _wNavIcon: 40
    readonly property int _wRefresh: 32
    readonly property int _wSearchIcon: 28
    readonly property int _wOverflow: 32

    function _topCalcWidth(phase) {
        var m = 40      // 20 left + 20 right margin
        var os = 24     // spacing between nav and actions sections
        var ns = 4      // spacing between nav layout children
        var as = 8      // spacing between action items

        if (phase === 0) {
            var searchW = Math.min(200, root.width * 0.3)
            var navW = _wSnap + _wQC + _wLib + _wUpd + _wSet + ns * 5   // 5 buttons + 1 spacer = 6 children
            var actW = _wRefresh + searchW + as
            return m + navW + os + actW
        }
        if (phase === 1) {
            var navW1 = _wSnap + _wQC + _wLib + _wUpd + _wSet + ns * 5
            var actW1 = _wRefresh + _wSearchIcon + as
            return m + navW1 + os + actW1
        }
        if (phase === 2) {
            var navW2 = _wNavIcon * 5 + ns * 5   // 5 icons + 1 spacer = 6 children
            var actW2 = _wRefresh + _wSearchIcon + as
            return m + navW2 + os + actW2
        }
        // phase 3 — Settings hidden, 4 icon-only buttons + 1 spacer = 5 children
        var navW3 = _wNavIcon * 4 + ns * 4
        var actW3 = _wOverflow + _wSearchIcon + as
        return m + navW3 + os + actW3
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
            Layout.fillWidth: true
            spacing: 4
            
            TopBarButton {
                id: topSnapBtn
                objectName: "topSnapBtn"
                labelText: "Snap"
                visible: true
                iconSource: AppController.ui_controller.getAssetUri("ui/snap-icon.svg")
                showLabel: root._topPhase < 2
                Layout.alignment: Qt.AlignVCenter
                onClicked: (mouse) => {
                    window.pendingSnap = true
                    AppController.snap_controller.takeSnap()
                }
            }

            TopBarButton {
                objectName: "navQuickCopy"
                iconSource: AppController.ui_controller.getAssetUri("ui/lightning-icon.svg")
                labelText: "Quick Copy"
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
                labelText: "Updates"
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
                id: topRefreshBtn
                visible: root._topPhase < 3
                buttonSize: 32
                iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                tooltipText: "Refresh skill library"
                onClicked: (mouse) => AppController.refreshSkills("manual-button", false)
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
                visible: root._topPhase >= 3
                iconText: "⋮"
                iconSize: 24
                buttonSize: 32
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
                        text: "Refresh"
                        iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                        onTriggered: AppController.refreshSkills("manual-button", false)
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
                visible: root._topPhase < 1
                Layout.fillWidth: true
                Layout.minimumWidth: 50
                Layout.maximumWidth: Math.min(200, root.width * 0.3)
                Layout.alignment: Qt.AlignVCenter
                
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
                visible: root._topPhase >= 1
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
            }
        }




    }
}
