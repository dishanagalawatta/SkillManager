/**
 * Purpose: A modern "Solid Matte" dialog for renaming project targets.
 * Usage:
 * ProjectRenameDialog {
 *     id: renameDialog
 *     targetPath: "c:/path/to/project"
 *     currentName: "My Project"
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
    
    property string targetPath: ""
    property string currentName: ""
    
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: 400
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
    
    onOpened: renameInput.text = currentName
    
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
                    text: "✏️"
                    font.pixelSize: 20
                }
                
                Text {
                    text: "Rename Target Project"
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
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 12
            Layout.margins: 24
            
            Text { 
                text: "Display Name for:\n" + root.targetPath
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeCaption
                color: Theme.secondaryLabel
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            
            TextField {
                id: renameInput
                placeholderText: "Project Name"
                Layout.fillWidth: true
                selectByMouse: true
                font.family: Theme.fontFamily
                verticalAlignment: TextInput.AlignVCenter
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
                    text: "Save"
                    Layout.preferredWidth: 100
                    Layout.preferredHeight: 40
                    onClicked: {
                        AppController.setTargetAlias(root.targetPath, renameInput.text)
                        root.accept()
                    }
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "EE" : Theme.accent)
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
