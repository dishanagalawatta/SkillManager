import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0
import SkillManagerComponents 1.0

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
            
            Image {
                source: appController.logoSource
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                fillMode: Image.PreserveAspectFit
                
                MouseArea {
                    anchors.fill: parent
                    onClicked: (mouse) => root.isCollapsed = !root.isCollapsed
                    cursorShape: Qt.PointingHandCursor
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
            iconText: "⚡"
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
            iconText: "📚"
            labelText: "Library"
            collapsed: root.isCollapsed
            active: root.currentView === "Library"
            onClicked: (mouse) => { 
                root.currentView = "Library"
                AppController.setViewFilter("all", "")
                root.navigationChanged("Library") 
            }
        }

        SidebarButton {
            iconText: "🔄"
            labelText: "Updates"
            collapsed: root.isCollapsed
            active: root.currentView === "Updates"
            onClicked: (mouse) => { root.currentView = "Updates"; root.navigationChanged("Updates") }
        }

        SidebarButton {
            iconText: "⚙️"
            labelText: "Settings"
            collapsed: root.isCollapsed
            active: root.currentView === "Settings"
            onClicked: (mouse) => { root.currentView = "Settings"; root.navigationChanged("Settings") }
        }
    }
}
