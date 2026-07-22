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
    property bool iconOnlyMode: root.width < 880
    property bool compactMode: root.width < 600
    property bool narrowMode: root.width < 460

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.narrowMode ? 12 : 20
        anchors.rightMargin: root.narrowMode ? 12 : 20
        spacing: root.narrowMode ? 8 : (root.compactMode ? 16 : 32)

        // Navigation
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            
            TopBarButton {
                id: topSnapBtn
                objectName: "topSnapBtn"
                labelText: "Snap"
                visible: !root.compactMode
                iconSource: AppController.ui_controller.getAssetUri("ui/screenshot-icon.svg")
                showLabel: !root.iconOnlyMode
                Layout.alignment: Qt.AlignVCenter
                onClicked: (mouse) => AppController.screenshot_controller.takeScreenshot()
            }

            TopBarButton {
                objectName: "navQuickCopy"
                iconSource: AppController.ui_controller.getAssetUri("ui/lightning-icon.svg")
                labelText: "Quick Copy"
                visible: !root.compactMode || active
                showLabel: !root.iconOnlyMode
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
                visible: !root.compactMode || active
                showLabel: !root.iconOnlyMode
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
                visible: !root.compactMode || active
                showLabel: !root.iconOnlyMode
                Layout.alignment: Qt.AlignVCenter
                active: root.currentView === "Updates"
                onClicked: (mouse) => { root.currentView = "Updates"; root.navigationChanged("Updates") }
            }

            TopBarButton {
                objectName: "navSettings"
                iconSource: AppController.ui_controller.getAssetUri("ui/settings-icon.svg")
                labelText: "Settings"
                visible: !root.compactMode || active
                showLabel: !root.iconOnlyMode
                Layout.alignment: Qt.AlignVCenter
                active: root.currentView === "Settings"
                onClicked: (mouse) => { root.currentView = "Settings"; root.navigationChanged("Settings") }
            }


            IconButton {
                id: topOverflowBtn
                visible: root.compactMode
                iconText: "⋮"
                iconSize: 24
                buttonSize: 36
                onClicked: topOverflowMenu.popup(topOverflowBtn, 0, topOverflowBtn.height + 4)
            }

            GlassMenu {
                id: topOverflowMenu
                GlassMenuItem {
                    text: "Snap"
                    iconSource: AppController.ui_controller.getAssetUri("ui/screenshot-icon.svg")
                    onTriggered: AppController.screenshot_controller.takeScreenshot()
                }
                GlassMenuItem {
                    text: "Quick Copy"
                    iconSource: AppController.ui_controller.getAssetUri("ui/lightning-icon.svg")
                    visible: root.currentView !== "Quick Copy" && root.currentView !== "QuickCopy"
                    onTriggered: { 
                        root.currentView = "Quick Copy"; 
                        root.navigationChanged("Quick Copy") 
                    }
                }
                GlassMenuItem {
                    text: "Library"
                    iconSource: AppController.ui_controller.getAssetUri("ui/library-icon.svg")
                    visible: root.currentView !== "Library"
                    onTriggered: { 
                        root.currentView = "Library"
                        root.navigationChanged("Library") 
                    }
                }
                GlassMenuItem {
                    text: "Updates"
                    iconSource: AppController.ui_controller.getAssetUri("ui/folder-sync-icon.svg")
                    visible: root.currentView !== "Updates"
                    onTriggered: { root.currentView = "Updates"; root.navigationChanged("Updates") }
                }
                GlassMenuItem {
                    text: "Settings"
                    iconSource: AppController.ui_controller.getAssetUri("ui/settings-icon.svg")
                    visible: root.currentView !== "Settings"
                    onTriggered: { root.currentView = "Settings"; root.navigationChanged("Settings") }
                }
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
                buttonSize: root.narrowMode ? 28 : 32
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

            GlassSearchInput {
                id: topSearchInput
                objectName: "topSearchInput"
                visible: !root.narrowMode
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
                visible: root.narrowMode
                buttonSize: 28
                iconSource: AppController.ui_controller.getAssetUri("ui/search-icon.svg")
                tooltipText: "Search skills"
                role: "ghost"
                Layout.alignment: Qt.AlignVCenter
                onClicked: {
                    // In narrow mode, toggle a temporary search state
                    // or simply switch to compact search when clicked
                    topSearchInput.visible = !topSearchInput.visible
                    if (topSearchInput.visible) {
                        topSearchInput.forceActiveFocus()
                    }
                }
            }
        }




    }
}
