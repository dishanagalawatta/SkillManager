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
                iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
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
        
        Rectangle {
            id: statusPill
            objectName: "topStatusPill"
            Layout.preferredWidth: 270
            Layout.preferredHeight: 34
            Layout.alignment: Qt.AlignVCenter
            radius: Theme.radiusPill
            color: AppController.statusMessage !== "" ? Theme.glassActive : "transparent"
            border.color: AppController.statusMessage !== "" ? Theme.glassBorder : "transparent"
            border.width: AppController.statusMessage !== "" ? 1 : 0
            opacity: AppController.statusMessage !== "" ? 1 : 0

            Behavior on opacity { NumberAnimation { duration: 300 } }
            Behavior on color { ColorAnimation { duration: 150 } }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Rectangle {
                    width: 7
                    height: 7
                    radius: 4
                    color: AppController.isLoading ? Theme.selectedRowBorder : Theme.secondaryLabel
                    opacity: AppController.isLoading ? 1 : 0.75
                }

                Text {
                    id: statusText
                    objectName: "topStatusText"
                    Layout.fillWidth: true
                    text: AppController.statusMessage
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeMetadata
                    color: Theme.label
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideLeft
                }
            }

            Connections {
                target: AppController
                function onStatusMessageChanged() {
                    statusPill.opacity = 1
                    statusTimer.restart()
                }
            }

            Timer {
                id: statusTimer
                interval: 5000
                onTriggered: statusPill.opacity = 0
            }
        }


    }
}
