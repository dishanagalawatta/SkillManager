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

        Item {
            Layout.preferredWidth: 18
            Layout.preferredHeight: 18
            Layout.alignment: Qt.AlignVCenter
            
            Image {
                id: titleLogoImg
                anchors.fill: parent
                source: (typeof AppController !== "undefined" && AppController) ? AppController.logoSource : ""
                fillMode: Image.PreserveAspectFit
                opacity: 0.9
                visible: !(typeof AppController !== "undefined" && AppController && AppController.ui_controller && AppController.ui_controller.isMonochromeLogo(AppController.clientFormat))
            }

            ColorOverlay {
                anchors.fill: titleLogoImg
                source: titleLogoImg
                color: Theme.iconLabel
                visible: (typeof AppController !== "undefined" && AppController && AppController.ui_controller && AppController.ui_controller.isMonochromeLogo(AppController.clientFormat))
                opacity: 0.9
            }
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
            iconSource: Theme.darkMode ? AppController.ui_controller.getAssetUri("ui/sun-icon.svg") : AppController.ui_controller.getAssetUri("ui/moon-icon.svg")
            tooltipText: "Toggle Theme"
            onClicked: AppController.ui_controller.darkMode = !AppController.ui_controller.darkMode
            hoverColor: Theme.glassHover
        }

        // Standard: Minimize
        TitleBarButton {
            iconSource: AppController.ui_controller.getAssetUri("ui/minimize-icon.svg")
            tooltipText: "Minimize Window"
            onClicked: window.showMinimized()
            hoverColor: Theme.glassHover
        }

        // Standard: Maximize/Restore
        TitleBarButton {
            iconSource: window.visibility === Window.Maximized
                ? AppController.ui_controller.getAssetUri("ui/restore-icon.svg")
                : AppController.ui_controller.getAssetUri("ui/maximize-icon.svg")
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
            iconSource: AppController.ui_controller.getAssetUri("ui/close-icon.svg")
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
        property color textColor: Theme.iconLabel
        property real btnSize: 28
        property real iconSize: 18
        property string tooltipText: ""
        property string iconSource: ""
        
        Layout.preferredWidth: btnSize + 8 // Padding for spacing
        Layout.preferredHeight: btnSize
        Layout.alignment: Qt.AlignVCenter
        
        contentItem: Item {
            anchors.fill: parent

            Text {
                visible: btn.iconSource === ""
                text: btn.text
                font.family: btn.font.family
                font.pixelSize: btn.font.pixelSize > 0 ? btn.font.pixelSize : 11
                color: btn.textColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                anchors.centerIn: parent
            }

            Image {
                id: iconImg
                visible: btn.iconSource !== ""
                source: btn.iconSource
                width: btn.iconSize
                height: btn.iconSize
                sourceSize.width: btn.iconSize
                sourceSize.height: btn.iconSize
                fillMode: Image.PreserveAspectFit
                anchors.centerIn: parent
                smooth: true
            }

            DuotoneColorOverlay {
                sourceItem: iconImg
                primaryColor: btn.textColor
                secondaryColor: Theme.darkMode ? Qt.rgba(1, 1, 1, 0.35) : "#E2E8F0"
                visible: btn.iconSource !== ""
            }
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

        SleekToolTip {
            id: btnToolTip
            text: btn.tooltipText
            visible: (btn.hovered || btn.visualFocus) && btn.tooltipText !== ""
        }

        Accessible.role: Accessible.Button
        Accessible.name: btn.tooltipText
    }
}

