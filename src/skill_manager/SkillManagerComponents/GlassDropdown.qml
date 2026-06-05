import QtQuick
import QtQuick.Controls
import App 1.0

ComboBox {
    id: control
    
    model: ["All Categories"]
    
    delegate: ItemDelegate {
        width: control.width
        contentItem: Text {
            text: modelData !== undefined ? modelData : ""
            color: Theme.label
            font.family: Theme.fontFamily
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: highlighted ? Theme.glassHover : "transparent"
        }
    }

    indicator: Canvas {
        id: canvas
        x: control.width - width - control.rightPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        width: 12
        height: 8
        contextType: "2d"

        onPaint: {
            context.reset();
            context.moveTo(0, 0);
            context.lineTo(width, 0);
            context.lineTo(width / 2, height);
            context.closePath();
            context.fillStyle = Theme.secondaryLabel;
            context.fill();
        }

        Connections {
            target: Theme
            function onSecondaryLabelChanged() { canvas.requestPaint() }
        }
    }

    contentItem: Text {
        leftPadding: 12
        rightPadding: control.indicator.width + control.spacing
        text: control.displayText
        font.family: Theme.fontFamily
        font.pixelSize: 13
        color: Theme.label
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        implicitWidth: 160
        implicitHeight: 36
        radius: Theme.radiusPill
        color: control.hovered ? Theme.glassHover : Theme.glassPill
        border.color: control.visualFocus ? Theme.accent : Theme.glassBorder
        border.width: control.visualFocus ? 2 : 1

        Behavior on color { ColorAnimation { duration: 200 } }
        Behavior on border.color { ColorAnimation { duration: 200 } }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 5
        
        // Use contentHeight from ListView for the popup's implicitHeight
        implicitHeight: Math.min(dropdownList.contentHeight + (topPadding + bottomPadding), 250)

        contentItem: ListView {
            id: dropdownList
            clip: true
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            // Removed implicitHeight: contentHeight to avoid height mismatch with constrained Popup
            
            ScrollBar.vertical: ScrollBar {
                id: scrollBar
                active: control.popup.visible
                policy: ScrollBar.AsNeeded
                
                contentItem: Rectangle {
                    implicitWidth: 4
                    radius: Theme.radiusSmall
                    color: Theme.secondaryLabel
                    opacity: scrollBar.active || scrollBar.hovered ? 0.8 : 0.3
                    Behavior on opacity { NumberAnimation { duration: 200 } }
                }
                
                background: Rectangle {
                    implicitWidth: 4
                    color: "transparent"
                }
            }
        }

        background: Rectangle {
            radius: Theme.radiusCard
            color: Theme.glassPill
            border.color: Theme.glassBorder
            border.width: 1
            opacity: 0.95
        }
    }

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    Accessible.role: Accessible.ComboBox
    Accessible.name: control.displayText
}
