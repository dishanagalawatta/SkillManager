import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Item {
    id: root

    property var model: []
    property var selectedValues: []
    property string placeholderText: "Select clients..."
    property string allLabel: "All Clients"

    property string displayText: {
        if (selectedValues.length === 0) return placeholderText
        if (selectedValues.length === model.length && model.length > 1) return allLabel
        return selectedValues.join(", ")
    }

    property bool allSelected: selectedValues.length === model.length && model.length > 1

    signal selectionChanged()

    implicitWidth: 160
    implicitHeight: 36

    activeFocusOnTab: true
    Accessible.role: Accessible.ComboBox
    Accessible.name: root.displayText

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            popup.opened ? popup.close() : popup.open()
            event.accepted = true
        }
    }

    function toggleAll(checked) {
        selectedValues = checked ? model.slice() : []
        selectionChanged()
    }

    function toggleItem(value) {
        var arr = selectedValues.slice()
        var idx = arr.indexOf(value)
        if (idx >= 0) {
            arr.splice(idx, 1)
        } else {
            arr.push(value)
        }
        selectedValues = arr
        selectionChanged()
    }

    Rectangle {
        id: trigger
        anchors.fill: parent
        radius: Theme.radiusPill
        color: mouseArea.containsMouse ? Theme.glassHover : Theme.glassPill
        border.color: root.activeFocus || popup.opened ? Theme.accent : Theme.glassBorder
        border.width: root.activeFocus || popup.opened ? 2 : 1

        Behavior on color { ColorAnimation { duration: 200 } }
        Behavior on border.color { ColorAnimation { duration: 200 } }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: popup.opened ? popup.close() : popup.open()
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 8
            spacing: 4

            Text {
                Layout.fillWidth: true
                text: displayText
                font.family: Theme.fontFamily
                font.pixelSize: 13
                color: selectedValues.length > 0 ? Theme.label : Theme.secondaryLabel
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            Canvas {
                id: arrowCanvas
                Layout.preferredWidth: 12
                Layout.preferredHeight: 8
                contextType: "2d"

                onAvailableChanged: {
                    if (available) requestPaint()
                }

                onPaint: {
                    if (!context) return
                    context.reset()
                    context.moveTo(0, 0)
                    context.lineTo(width, 0)
                    context.lineTo(width / 2, height)
                    context.closePath()
                    context.fillStyle = Theme.secondaryLabel
                    context.fill()
                }

                Connections {
                    target: Theme
                    function onSecondaryLabelChanged() { arrowCanvas.requestPaint() }
                }
            }
        }
    }

    Popup {
        id: popup
        y: root.height + 4
        width: Math.max(root.width, 180)
        padding: 5

        implicitHeight: Math.min(listContent.implicitHeight + topPadding + bottomPadding, 300)

        contentItem: ScrollView {
            id: scrollView
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical: AppScrollBar { }

            ColumnLayout {
                id: listContent
                width: scrollView.width
                spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                color: allHover.containsMouse ? Theme.glassHover : "transparent"
                visible: root.model.length > 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8

                    GlassCheckBox {
                        id: allCheck
                        Layout.preferredWidth: 20
                        Layout.preferredHeight: 20
                        checkState: allSelected ? Qt.Checked : Qt.Unchecked
                        iconSize: 9
                        onToggled: root.toggleAll(checkState !== Qt.Checked)
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.allLabel
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                        color: Theme.label
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                MouseArea {
                    id: allHover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: allCheck.toggled()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 8
                Layout.rightMargin: 8
                Layout.preferredHeight: 1
                color: Theme.separator
                visible: root.model.length > 1
            }

            Repeater {
                model: root.model

                delegate: Rectangle {
                    required property string modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    color: itemHover.containsMouse ? Theme.glassHover : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        GlassCheckBox {
                            id: itemCheck
                            Layout.preferredWidth: 20
                            Layout.preferredHeight: 20
                            checkState: root.selectedValues.indexOf(modelData) >= 0 ? Qt.Checked : Qt.Unchecked
                            iconSize: 9
                            onToggled: root.toggleItem(modelData)
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                            color: Theme.label
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    MouseArea {
                        id: itemHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: itemCheck.toggled()
                    }
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
}
