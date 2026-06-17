import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

ComboBox {
    id: control
    property bool keyboardNavigated: false
    
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
            keyboardNavigated = true
        }
        event.accepted = false
    }

    signal collectionSelected(string name)
    signal editCollectionClicked(string name)

    function getFilteredCollections() {
        return AppController.customCollections || []
    }

    model: ["All Collections"].concat(getFilteredCollections())

    Connections {
        target: AppController
        function onCustomCollectionsChanged() {
            control.model = ["All Collections"].concat(control.getFilteredCollections())
        }
    }

    delegate: ItemDelegate {
        width: dropdownList.width
        height: 32 // FIX: Fixed height prevents list implicitHeight jitter which causes Flickable out-of-bounds jump
        padding: 0 // FIX: Remove default Qt padding which clips contentItem in fixed-height delegates
        hoverEnabled: true

        HoverHandler {
            onHoveredChanged: {
                if (hovered) {
                    control.keyboardNavigated = false
                }
            }
        }

        contentItem: RowLayout {
            spacing: 8
            Text {
                leftPadding: 10
                text: modelData !== undefined ? modelData : ""
                color: Theme.label
                font.family: Theme.fontFamily
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
                Layout.fillWidth: true
            }

            // Edit Button
            IconButton {
                id: editBtn
                buttonSize: 24
                iconSize: 10
                iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
                role: "ghost"
                tooltipText: "Edit Collection"
                visible: index > 0 // Only for custom collections
                Layout.rightMargin: 10

                onClicked: {
                    control.popup.close()
                    control.editCollectionClicked(modelData !== undefined ? modelData : "")
                }
            }
        }
        background: Rectangle {
            radius: 6
            color: (hovered || (control.keyboardNavigated && control.highlightedIndex === index)) ? Theme.glassHover : "transparent"
        }
    }

    indicator: Canvas {
        id: canvas
        x: control.width - width - control.rightPadding
        y: control.topPadding + ((control.height - control.topPadding - control.bottomPadding) - height) / 2
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
        padding: 6
        implicitHeight: Math.min(dropdownList.implicitHeight + topPadding + bottomPadding, 250)

        contentItem: SmoothListView {
            id: dropdownList
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            boundsBehavior: Flickable.StopAtBounds
            highlightRangeMode: ListView.NoHighlightRange
            highlightFollowsCurrentItem: false

            onContentYChanged: {
                appController.logDiagnosticEvent("DEBUG", "status_message", "GlassCollectionDropdown contentY: " + contentY + " (height=" + height + ", contentHeight=" + contentHeight + ")")
            }
            onContentHeightChanged: {
                appController.logDiagnosticEvent("DEBUG", "status_message", "GlassCollectionDropdown contentHeight changed: " + contentHeight)
            }

            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
                    control.keyboardNavigated = true
                }
                event.accepted = false
            }

            Connections {
                target: control
                function onHighlightedIndexChanged() {
                    if (control.popup.opened && control.keyboardNavigated) {
                        dropdownList.positionViewAtIndex(control.highlightedIndex, ListView.Contain)
                    }
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

    onActivated: (index) => {
        if (index >= 0) {
            collectionSelected(currentText)
        }
    }

    Accessible.role: Accessible.ComboBox
    Accessible.name: control.displayText
}
