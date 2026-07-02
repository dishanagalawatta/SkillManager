import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: control

    property string iconText: text
    property string iconSource: ""
    property string role: "secondary" // secondary, primary, destructive, ghost
    property string tooltipText: ""
    property string accessibleName: tooltipText !== "" ? tooltipText : iconText
    property int buttonSize: 32
    property int iconSize: 15

    Layout.preferredWidth: buttonSize
    Layout.preferredHeight: buttonSize
    implicitWidth: buttonSize
    implicitHeight: buttonSize
    padding: 0
    flat: true

    contentItem: Item {
        implicitWidth: control.buttonSize
        implicitHeight: control.buttonSize

        Text {
            anchors.centerIn: parent
            visible: control.iconSource === "" && control.iconText !== ""
            text: control.iconText
            font.family: Theme.fontFamily
            font.pixelSize: control.iconSize
            font.weight: control.role === "primary" ? Font.Bold : Font.DemiBold
            color: {
                if (!control.enabled) return Theme.secondaryLabel
                if (control.role === "primary") return "white"
                if (control.role === "destructive") return Theme.danger
                return control.hovered || control.down ? Theme.label : Theme.secondaryLabel
            }
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Image {
            id: iconImg
            anchors.centerIn: parent
            width: control.iconSize
            height: control.iconSize
            visible: control.iconSource !== ""
            source: control.iconSource
            sourceSize.width: control.iconSize
            sourceSize.height: control.iconSize
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        ColorOverlay {
            anchors.fill: iconImg
            source: iconImg
            color: {
                if (!control.enabled) return Theme.secondaryLabel
                if (control.role === "primary") return "white"
                if (control.role === "destructive") return Theme.danger
                return control.hovered || control.down ? Theme.label : Theme.secondaryLabel
            }
            visible: control.iconSource !== ""
        }
    }

    background: Rectangle {
        radius: Math.max(Theme.radiusSmall, control.buttonSize / 2)
        color: {
            if (!control.enabled) return Theme.disabledControl
            if (control.role === "primary") return control.down ? Theme.glassActive : Theme.accent
            if (control.role === "destructive") return control.hovered || control.down ? Theme.dangerHover : "transparent"
            if (control.role === "ghost") return control.hovered || control.down ? Theme.glassHover : "transparent"
            return control.down ? Theme.glassActive : (control.hovered ? Theme.glassHover : "transparent")
        }
        border.color: {
            if (control.visualFocus) return Theme.accent
            if (!control.enabled) return Theme.glassBorder
            if (control.role === "destructive") return control.hovered || control.down ? Theme.danger : "transparent"
            if (control.role === "primary") return "transparent"
            return control.hovered || control.down ? Theme.glassBorder : "transparent"
        }
        border.width: control.visualFocus ? 2 : (control.role === "primary" ? 0 : (control.hovered || !control.enabled ? 1 : 0))
        opacity: control.enabled ? 1.0 : 0.65
    }

    SleekToolTip {
        id: btnToolTip
        visible: (control.hovered || control.visualFocus) && control.tooltipText !== ""
        text: control.tooltipText
    }
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
