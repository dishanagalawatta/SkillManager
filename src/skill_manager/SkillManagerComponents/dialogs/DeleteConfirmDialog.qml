/**
 * Purpose: A modern "Solid Matte" confirmation dialog for deletion actions.
 * Usage:
 * DeleteConfirmDialog {
 *     id: deleteDialog
 *     onAccepted: () => console.log("Deletion confirmed")
 * }
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import ".."
import App 1.0

Dialog {
    id: root
    
    property string message: "Are you sure you want to delete this item?"
    property string itemTitle: ""
    property var currentCallback: null
    
    onAccepted: {
        if (currentCallback) {
            currentCallback()
            currentCallback = null
        }
    }
    
    onRejected: {
        currentCallback = null
    }
    
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: 440
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

    function confirmSingle(title, callback) {
        root.itemTitle = title
        root.message = "Are you sure you want to delete this skill?"
        root.currentCallback = callback
        root.open()
        cancelBtn.forceActiveFocus()
    }

    function confirmBulk(count, callback) {
        root.itemTitle = count + " Selected Items"
        root.message = "Are you sure you want to delete " + count + " selected skills?"
        root.currentCallback = callback
        root.open()
        cancelBtn.forceActiveFocus()
    }

    contentItem: ColumnLayout {
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
                    text: "⚠️"
                    font.pixelSize: 20
                }
                
                Text {
                    text: "Confirm Deletion"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }
                
                IconButton {
                    text: "✕"
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
        
        // Content
        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 24
            spacing: 12
            
            Text {
                text: root.message
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                visible: root.itemTitle !== ""
                color: Theme.glassHover
                radius: Theme.radiusSmall
                border.color: Theme.glassBorder
                
                Text {
                    anchors.centerIn: parent
                    text: root.itemTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Font.DemiBold
                    color: Theme.danger
                    elide: Text.ElideMiddle
                    width: parent.width - 32
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            Text {
                text: "This action cannot be undone."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeMetadata
                color: Theme.secondaryLabel
                Layout.fillWidth: true
            }
        }
        
        // Footer
        Rectangle {
            Layout.fillWidth: true
            height: 80
            color: "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 12
                
                Item { Layout.fillWidth: true }
                
                ActionButton {
                    id: cancelBtn
                    text: "Cancel"
                    Layout.preferredWidth: 100
                    Layout.preferredHeight: 40
                    onClicked: root.reject()
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.glassBorder
                        border.width: parent.activeFocus ? 2 : 1
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Medium
                        color: Theme.label
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                ActionButton {
                    id: deleteBtn
                    text: "Delete"
                    Layout.preferredWidth: 100
                    Layout.preferredHeight: 40
                    
                    onClicked: root.accept()
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.down ? Theme.danger : (parent.hovered ? Theme.alpha(Theme.danger, 0.93) : Theme.danger)
                        border.color: parent.activeFocus ? Theme.label : "transparent"
                        border.width: 2
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
