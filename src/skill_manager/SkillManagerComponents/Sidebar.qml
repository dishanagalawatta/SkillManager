import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root
    width: isCollapsed ? 70 : 220
    Layout.preferredWidth: width
    Layout.fillHeight: true
    color: Theme.sidebarBackground
    
    // Outer defining border
    border.width: 1
    border.color: Theme.glassOuterBorder

    // Inner highlight border (Removed for solid matte)
    Item {
        anchors.fill: parent
    }
    
    Behavior on width {
        NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
    }
    
    signal navigationChanged(string view)
    property string currentView: "QuickCopy"
    property bool isCollapsed: false

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 12

        // App Logo/Title + Toggle
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            spacing: 12
            
            Item {
                id: logoBtn
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                activeFocusOnTab: true

                Accessible.role: Accessible.Button
                Accessible.name: sidebarToolTip.text

                Keys.onPressed: (event) => {
                    if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        root.isCollapsed = !root.isCollapsed
                        event.accepted = true
                    }
                }

                Image {
                    id: sidebarLogoImg
                    anchors.fill: parent
                    source: AppController.ui_controller.logoSource
                    fillMode: Image.PreserveAspectFit
                    visible: (typeof AppController !== "undefined" && AppController && AppController.clientFormat === "OpenCode") ? false : true
                }
                
                ColorOverlay {
                    anchors.fill: sidebarLogoImg
                    source: sidebarLogoImg
                    color: Theme.label
                    visible: (typeof AppController !== "undefined" && AppController && AppController.clientFormat === "OpenCode") ? true : false
                }
                
                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    border.color: Theme.accent
                    border.width: 2
                    visible: logoBtn.activeFocus
                }

                MouseArea {
                    id: logoMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: (mouse) => root.isCollapsed = !root.isCollapsed
                    cursorShape: Qt.PointingHandCursor

                    SleekToolTip {
                        id: sidebarToolTip
                        text: root.isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"
                        visible: parent.containsMouse || logoBtn.activeFocus
                    }
                }
            }
            
            Text {
                text: "Skill Manager"
                font.family: Theme.fontFamily
                font.pixelSize: 18
                font.weight: Font.Bold
                color: Theme.label
                visible: !root.isCollapsed
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 200 } }
            }
        }

        // Main Navigation
        SidebarButton {
            iconSource: AppController.ui_controller.getAssetUri("ui/lightning-icon.svg")
            labelText: "Quick Copy"
            collapsed: root.isCollapsed
            active: root.currentView === "Quick Copy"
            onClicked: (mouse) => { 
                console.log("Sidebar: Quick Copy clicked")
                root.currentView = "Quick Copy"; 
                root.navigationChanged("Quick Copy") 
            }
        }

        SidebarButton {
            iconSource: AppController.ui_controller.getAssetUri("ui/library-icon.svg")
            labelText: "Library"
            collapsed: root.isCollapsed
            active: root.currentView === "Library"
            onClicked: (mouse) => { 
                root.currentView = "Library"
                root.navigationChanged("Library") 
            }
        }

        SidebarButton {
            iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
            labelText: "Updates"
            collapsed: root.isCollapsed
            active: root.currentView === "Updates"
            onClicked: (mouse) => { root.currentView = "Updates"; root.navigationChanged("Updates") }
        }

        SidebarButton {
            iconSource: AppController.ui_controller.getAssetUri("ui/settings-icon.svg")
            labelText: "Settings"
            collapsed: root.isCollapsed
            active: root.currentView === "Settings"
            onClicked: (mouse) => { root.currentView = "Settings"; root.navigationChanged("Settings") }
        }
    }
}
