import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root
    height: 64
    Layout.fillWidth: true
    color: Theme.glassPill
    radius: 0 // Keep top flat or slightly rounded if desired, but following 'no feature change'
    
    // Outer defining border
    border.width: 1
    border.color: Theme.glassOuterBorder

    // Inner highlight border (Removed for solid matte)
    Item {
        anchors.fill: parent
    }
    
    signal navigationChanged(string view)
    property string currentView: "QuickCopy"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 32

        // Navigation
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            
            TopBarButton {
                id: topSnapBtn
                objectName: "topSnapBtn"
                labelText: "Snap"
                iconSource: AppController.ui_controller.getAssetUri("ui/screenshot-icon.svg")
                onClicked: (mouse) => AppController.screenshot_controller.takeScreenshot()
            }

            TopBarButton {
                objectName: "navQuickCopy"
                iconSource: AppController.ui_controller.getAssetUri("ui/lightning-icon.svg")
                labelText: "Quick Copy"
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
                active: root.currentView === "Updates"
                onClicked: (mouse) => { root.currentView = "Updates"; root.navigationChanged("Updates") }
            }

            TopBarButton {
                objectName: "navSettings"
                iconSource: AppController.ui_controller.getAssetUri("ui/settings-icon.svg")
                labelText: "Settings"
                active: root.currentView === "Settings"
                onClicked: (mouse) => { root.currentView = "Settings"; root.navigationChanged("Settings") }
            }


            
            Item { Layout.fillWidth: true }
        }
        

        RowLayout {
            spacing: 8

            IconButton {
                id: topRefreshBtn
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

            GlassSearchInput {
                id: topSearchInput
                objectName: "topSearchInput"
                Layout.preferredWidth: 200
                
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
        }




    }
}
