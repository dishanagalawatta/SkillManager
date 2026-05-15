import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

ComboBox {
    id: control
    
    signal collectionSelected(string name)
    signal editCollectionClicked(string name)

    model: ["All Collections"].concat(AppController.customCollections)
    
    delegate: ItemDelegate {
        width: control.width
        contentItem: RowLayout {
            spacing: 8
            Text {
                text: modelData
                color: Theme.label
                font.family: Theme.fontFamily
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
                Layout.fillWidth: true
            }
            
            // Edit Button (Pen Icon)
            Button {
                id: editBtn
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                flat: true
                visible: index > 0 // Only for custom collections
                hoverEnabled: true
                
                contentItem: Text {
                    text: "✎"
                    font.pixelSize: 14
                    color: editBtn.hovered ? Theme.accent : Theme.secondaryLabel
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                
                background: Rectangle {
                    color: editBtn.hovered ? Theme.glassPill : "transparent"
                    radius: Theme.radiusSmall
                }
                
                onClicked: {
                    control.popup.close()
                    control.editCollectionClicked(modelData)
                }
                
                ToolTip.visible: hovered
                ToolTip.text: "Edit Collection"
            }
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
        color: Theme.glassPill
        border.color: Theme.glassBorder
        border.width: 1
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 5
        implicitHeight: Math.min(dropdownList.contentHeight + 10, 250)

        contentItem: ListView {
            id: dropdownList
            clip: true
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            
            ScrollBar.vertical: ScrollBar {
                active: true
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

    onActivated: (index) => {
        if (index >= 0) {
            collectionSelected(currentText)
        }
    }
}
