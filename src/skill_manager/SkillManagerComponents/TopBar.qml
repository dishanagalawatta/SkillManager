import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0
import SkillManagerComponents 1.0

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
                iconText: "⚡"
                labelText: "Quick Copy"
                active: root.currentView === "Quick Copy" || root.currentView === "QuickCopy"
                onClicked: { 
                    root.currentView = "Quick Copy"; 
                    root.navigationChanged("Quick Copy") 
                }
            }

            TopBarButton {
                iconText: "📚"
                labelText: "Library"
                active: root.currentView === "Library"
                onClicked: { 
                    root.currentView = "Library"
                    root.navigationChanged("Library") 
                }
            }

            TopBarButton {
                iconText: "🔄"
                labelText: "Updates"
                active: root.currentView === "Updates"
                onClicked: { root.currentView = "Updates"; root.navigationChanged("Updates") }
            }

            TopBarButton {
                iconText: "⚙️"
                labelText: "Settings"
                active: root.currentView === "Settings"
                onClicked: { root.currentView = "Settings"; root.navigationChanged("Settings") }
            }
            
            Item { Layout.fillWidth: true }
        }
        
        // Right side
        Item {
            Layout.preferredWidth: 250
            Layout.fillHeight: true
            
            Text {
                id: statusText
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: AppController.statusMessage
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeMetadata
                color: Theme.secondaryLabel
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideLeft
                width: parent.width
                
                Behavior on opacity { NumberAnimation { duration: 300 } }
            }

            Connections {
                target: AppController
                function onStatusMessageChanged() {
                    statusText.opacity = 1
                    statusTimer.restart()
                }
            }

            Timer {
                id: statusTimer
                interval: 5000
                onTriggered: statusText.opacity = 0
            }
        }
    }
}
