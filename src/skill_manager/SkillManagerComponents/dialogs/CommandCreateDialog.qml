/**
 * Purpose: A modern "Solid Matte" dialog for creating custom commands.
 * Usage:
 * CommandCreateDialog {
 *     id: commandDialog
 *     onAccepted: () => console.log("Command created")
 * }
 */
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import App 1.0
import SkillManagerComponents 1.0

Dialog {
    id: root
    
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: 520
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

    function openWithContext(project, client) {
        // Reset fields
        cmdNameInput.text = ""
        cmdCategoryInput.text = ""
        cmdBodyInput.text = ""
        
        // Set defaults from context
        let projIdx = AppController.projects.indexOf(project)
        projectDrop.currentIndex = Math.max(0, projIdx)
        
        let clientIdx = AppController.clientFormats.indexOf(client)
        clientDrop.currentIndex = Math.max(0, clientIdx)
        
        open()
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
                    text: "⌨️"
                    font.pixelSize: 20
                }
                
                Text {
                    text: "Create Custom Command"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }
                
                Button {
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
            spacing: 20
            
            // Name and Category
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Command Name"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                    TextField { 
                        id: cmdNameInput
                        placeholderText: "e.g. PR Template"
                        Layout.fillWidth: true
                        selectByMouse: true
                        font.family: Theme.fontFamily
                        leftPadding: 16
                        rightPadding: 16
                        topPadding: 12
                        bottomPadding: 12
                        background: Rectangle { 
                            radius: Theme.radiusField
                            color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                            border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                            border.width: parent.activeFocus ? 2 : 1
                        }
                    }
                }
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Category"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                    TextField { 
                        id: cmdCategoryInput
                        placeholderText: "e.g. Git, Dev"
                        Layout.fillWidth: true
                        selectByMouse: true
                        font.family: Theme.fontFamily
                        leftPadding: 16
                        rightPadding: 16
                        topPadding: 12
                        bottomPadding: 12
                        background: Rectangle { 
                            radius: Theme.radiusField
                            color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                            border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                            border.width: parent.activeFocus ? 2 : 1
                        }
                    }
                }
            }
            
            // Project and Client
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Target Project"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                    GlassDropdown {
                        id: projectDrop
                        Layout.fillWidth: true
                        model: AppController.projects
                    }
                }
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Client Format"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                    GlassDropdown {
                        id: clientDrop
                        Layout.fillWidth: true
                        model: AppController.clientFormats
                    }
                }
            }
            
            // Command Body
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 4
                Text { text: "Command Content"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; color: Theme.secondaryLabel }
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    radius: Theme.radiusField
                    color: Theme.glassHover
                    border.color: cmdBodyInput.activeFocus ? Theme.accent : Theme.glassBorder
                    border.width: cmdBodyInput.activeFocus ? 2 : 1
                    
                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 12
                        clip: true
                        
                        TextArea {
                            id: cmdBodyInput
                            placeholderText: "Paste your command or system prompt here..."
                            color: Theme.label
                            font.family: "Consolas", "Monospace", "monospace"
                            font.pixelSize: 13
                            wrapMode: TextArea.Wrap
                            selectByMouse: true
                            background: null
                        }
                    }
                }
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
                
                Button {
                    text: "Cancel"
                    Layout.preferredWidth: 100
                    Layout.preferredHeight: 40
                    onClicked: root.reject()
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.glassBorder
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
                
                Button {
                    id: createBtn
                    text: "Create Command"
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 40
                    enabled: cmdNameInput.text !== "" && cmdBodyInput.text !== ""
                    
                    onClicked: {
                        AppController.createCustomCommand(
                            cmdNameInput.text, 
                            clientDrop.currentText, 
                            cmdBodyInput.text, 
                            projectDrop.currentText, 
                            cmdCategoryInput.text
                        )
                        root.accept()
                    }
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: !parent.enabled ? Theme.secondaryLabel : (parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "EE" : Theme.accent))
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
