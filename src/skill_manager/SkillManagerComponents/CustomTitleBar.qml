import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root
    height: 32
    color: "transparent"

    property var window: Window.window

    TapHandler {
        onDoubleTapped: {
            if (window.visibility === Window.Maximized)
                window.showNormal()
            else
                window.showMaximized()
        }
    }

    DragHandler {
        target: null
        onActiveChanged: {
            if (active) {
                window.startSystemMove()
            }
        }
    }

    // --- Left Side: Icon and Title ---
    RowLayout {
        id: leftGroup
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        Image {
            source: (typeof AppController !== "undefined" && AppController) ? AppController.logoSource : ""
            Layout.preferredWidth: 18
            Layout.preferredHeight: 18
            fillMode: Image.PreserveAspectFit
            opacity: 0.9
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            text: "Skill Manager"
            font.family: Theme.fontFamily
            font.pixelSize: 12
            font.weight: Font.DemiBold
            color: Theme.label
            opacity: 0.8
            Layout.alignment: Qt.AlignVCenter
        }
    }

    // --- Right Side: Controls ---
    RowLayout {
        id: rightGroup
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        // Custom Button: Theme Toggle
        TitleBarButton {
            text: Theme.darkMode ? "☀️" : "🌙"
            tooltipText: "Toggle Theme"
            onClicked: Theme.darkMode = !Theme.darkMode
            hoverColor: Theme.glassHover
        }

        // Standard: Minimize
        TitleBarButton {
            text: "—"
            tooltipText: "Minimize Window"
            onClicked: window.showMinimized()
            hoverColor: Theme.glassHover
        }

        // Standard: Maximize/Restore
        TitleBarButton {
            text: window.visibility === Window.Maximized ? "❐" : "⬜"
            tooltipText: window.visibility === Window.Maximized ? "Restore Window" : "Maximize Window"
            onClicked: {
                if (window.visibility === Window.Maximized)
                    window.showNormal()
                else
                    window.showMaximized()
            }
            hoverColor: Theme.glassHover
        }

        // Standard: Close
        TitleBarButton {
            text: "✕"
            tooltipText: "Close Window"
            onClicked: window.close()
            hoverColor: Theme.danger
            textColor: hovered ? "white" : Theme.label
        }
    }

    // --- Sub-component for buttons ---
    component TitleBarButton: AbstractButton {
        id: btn
        property color hoverColor: Theme.glassHover
        property color textColor: Theme.label
        property real btnSize: 28
        property string tooltipText: ""
        
        Layout.preferredWidth: btnSize + 8 // Padding for spacing
        Layout.preferredHeight: btnSize
        Layout.alignment: Qt.AlignVCenter
        
        contentItem: Text {
            text: btn.text
            font.pixelSize: 11
            color: btn.textColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            anchors.centerIn: parent
        }

        background: Rectangle {
            width: btn.btnSize
            height: btn.btnSize
            anchors.centerIn: parent
            radius: width / 2
            color: btn.hovered ? btn.hoverColor : "transparent"
            border.width: btn.hovered ? 1 : 0
            border.color: Theme.glassBorder
            
            Behavior on color { ColorAnimation { duration: 150 } }
        }

        ToolTip.text: btn.tooltipText
        ToolTip.visible: btn.hovered && btn.tooltipText !== ""
        ToolTip.delay: 400

        Accessible.role: Accessible.Button
        Accessible.name: btn.tooltipText
        Accessible.description: btn.tooltipText
    }
}
