/**
 * Purpose: A dialog for reordering projects via drag-and-drop.
 * Usage:
 * ProjectReorderDialog {
 *     id: reorderDialog
 * }
 * reorderDialog.open()
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Dialog {
    id: root

    property var projectLabels: AppController.projectLabels
    property int dragSourceIndex: -1
    property int dragTargetIndex: -1
    property bool dropAbove: true

    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: 420
    height: Math.min(500, contentColumn.implicitHeight, parent ? parent.height - 40 : 500)
    modal: true
    padding: 0

    background: Rectangle {
        color: Theme.glassPill
        radius: Theme.radiusCard
        border.color: Theme.glassBorder
        border.width: 1

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 20
            color: Theme.glassShadow
            verticalOffset: 8
            horizontalOffset: 0
        }
    }

    contentItem: ColumnLayout {
        id: contentColumn
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 16
                spacing: 12

                Text {
                    text: "\u2630"
                    font.pixelSize: 20
                    color: Theme.secondaryLabel
                }

                Text {
                    text: "Reorder Projects"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }

                IconButton {
                    text: "\u2715"
                    flat: true
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    onClicked: root.reject()

                    background: Rectangle {
                        radius: 16
                        color: parent.hovered ? Theme.glassHover : "transparent"
                    }

                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 16
                        color: Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.separator
            }
        }

        // Subtitle
        Text {
            text: "Drag items to change the display order"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            color: Theme.secondaryLabel
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 16
            Layout.bottomMargin: 8
        }

        // Project list
        ListView {
            id: projectList
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: contentHeight
            Layout.maximumHeight: 400
            Layout.minimumHeight: 100
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            clip: true
            model: root.projectLabels
            spacing: 4
            boundsBehavior: Flickable.StopAtBounds

            delegate: Item {
                id: delegateWrapper
                required property int index
                required property string modelData

                width: projectList.width
                height: 44

                Rectangle {
                    id: delegateRoot
                    width: delegateWrapper.width
                    height: delegateWrapper.height
                    radius: 8
                    color: dragArea.containsDrag ? Theme.alpha(Theme.accent, 0.15) : Theme.glassHover
                    border.color: dragArea.containsDrag ? Theme.accent : "transparent"
                    border.width: dragArea.containsDrag ? 2 : 1

                    Behavior on color { ColorAnimation { duration: 150 } }
                    Behavior on border.color { ColorAnimation { duration: 150 } }

                    // Drag support
                    Drag.active: dragArea.drag.active
                    Drag.source: delegateRoot
                    Drag.hotSpot.x: width / 2
                    Drag.hotSpot.y: height / 2

                    states: State {
                        when: dragArea.drag.active
                        ParentChange {
                            target: delegateRoot
                            parent: projectList
                        }
                        PropertyChanges {
                            target: delegateRoot
                            z: 10
                            opacity: 0.85
                        }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        // Drag handle
                        Text {
                            text: "\u2630"
                            font.pixelSize: 16
                            color: Theme.secondaryLabel
                            Layout.preferredWidth: 20
                            horizontalAlignment: Text.AlignHCenter

                            MouseArea {
                                id: dragArea
                                anchors.fill: parent
                                cursorShape: Qt.DragMoveCursor
                                drag.target: delegateRoot
                                drag.axis: Drag.YAxis

                                onPressed: (mouse) => {
                                    root.dragSourceIndex = delegateWrapper.index
                                    root.dragTargetIndex = delegateWrapper.index
                                    root.dropAbove = true
                                }
                                onReleased: {
                                    var src = root.dragSourceIndex
                                    var tgt = root.dragTargetIndex
                                    var isValidDrop = (src >= 0 && tgt >= 0 && src !== tgt)
                                    var toIdx = tgt

                                    if (isValidDrop) {
                                        if (root.dropAbove) {
                                            toIdx = tgt - (src < tgt ? 1 : 0)
                                        } else {
                                            toIdx = tgt + 1 - (src <= tgt ? 1 : 0)
                                        }
                                    }

                                    // Reset visual/drag state before model mutation
                                    root.dragSourceIndex = -1
                                    root.dragTargetIndex = -1
                                    root.dropAbove = true
                                    delegateRoot.y = 0

                                    // Defer python call to avoid destroying delegate during script execution
                                    if (isValidDrop) {
                                        Qt.callLater(AppController.reorderProjects, src, toIdx)
                                    }
                                }
                            }
                        }

                        // Index badge
                        Rectangle {
                            Layout.preferredWidth: 24
                            Layout.preferredHeight: 24
                            radius: 12
                            color: Theme.alpha(Theme.accent, 0.15)

                            Text {
                                anchors.centerIn: parent
                                text: delegateWrapper.index + 1
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeMetadata
                                font.weight: Font.Bold
                                color: Theme.accent
                            }
                        }

                        // Project label
                        Text {
                            text: delegateWrapper.modelData
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeBody
                            color: Theme.label
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                }

                // Drop area for reordering (visual only — no model mutation)
                DropArea {
                    anchors.fill: parent
                    anchors.margins: -4

                    onEntered: (drag) => {
                        root.dragTargetIndex = delegateWrapper.index
                        root.dropAbove = drag.y < delegateWrapper.height / 2
                    }

                    onPositionChanged: (drag) => {
                        root.dragTargetIndex = delegateWrapper.index
                        root.dropAbove = drag.y < delegateWrapper.height / 2
                    }

                    onExited: {
                        try {
                            if (root.dragTargetIndex === delegateWrapper.index) {
                                root.dragTargetIndex = -1
                            }
                        } catch (e) {}
                    }
                }

                // Placeholder line indicating drop position
                Rectangle {
                    visible: root.dragSourceIndex >= 0
                             && root.dragTargetIndex === delegateWrapper.index
                             && root.dragSourceIndex !== delegateWrapper.index
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 32
                    height: 2
                    radius: 1
                    color: Theme.accent
                    y: root.dropAbove ? 0 : parent.height - height
                }
            }

            // Scrollbar
            ScrollBar.vertical: ScrollBar {
                policy: projectList.contentHeight > projectList.height ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                width: 6
                contentItem: Rectangle {
                    radius: 3
                    color: parent.pressed ? Theme.secondaryLabel : Theme.alpha(Theme.secondaryLabel, 0.4)
                }
            }
        }

        // Footer
        Rectangle {
            Layout.fillWidth: true
            height: 70
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12

                Item { Layout.fillWidth: true }

                ActionButton {
                    text: "Done"
                    Layout.preferredWidth: 100
                    Layout.preferredHeight: 40
                    onClicked: root.accept()

                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.down ? Theme.accent : (parent.hovered ? Theme.alpha(Theme.accent, 0.93) : Theme.accent)
                    }

                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Bold
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}
