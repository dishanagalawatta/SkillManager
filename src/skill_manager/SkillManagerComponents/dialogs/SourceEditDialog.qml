/**
 * Purpose: A comprehensive "Solid Matte" dialog for adding and editing skill sources.
 * Usage:
 * SourceEditDialog {
 *     id: sourceDialog
 *     onAccepted: (data) => console.log(data)
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
    
    property int editIndex: -1
    property bool isEdit: editIndex !== -1
    
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: 480
    modal: true
    padding: 0
    
    background: Rectangle {
        color: Theme.glassPill
        radius: Theme.radiusCard
        border.color: Theme.glassBorder
        border.width: 1
        
        layer.enabled: true
        layer.effect: DropShadow {
            radius: 24
            color: Theme.glassShadow
            verticalOffset: 12
            horizontalOffset: 0
            samples: 25
        }
    }

    onOpened: {
        if (!isEdit) {
            nameInput.text = ""
            typeCombo.currentIndex = 0
            packageInput.text = ""
            repoInput.text = ""
            pathInput.text = ""
            argsInput.text = ""
            cmdInput.text = ""
        }
    }

    function loadSource(data) {
        nameInput.text = data.name || ""
        let types = ["npm", "git", "custom"]
        let idx = types.indexOf(data.source_type)
        typeCombo.currentIndex = idx !== -1 ? idx : 0
        packageInput.text = data.package_name || ""
        repoInput.text = data.repository_url || ""
        pathInput.text = data.local_path || ""
        argsInput.text = data.install_args || ""
        cmdInput.text = data.update_command || ""
    }

    contentItem: ColumnLayout {
        spacing: 0
        
        // Header Section
        Rectangle {
            Layout.fillWidth: true
            height: 70
            color: "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 16
                spacing: 16
                
                Rectangle {
                    width: 40
                    height: 40
                    radius: 20
                    color: Theme.accent + "11"
                    Text {
                        anchors.centerIn: parent
                        text: "📦"
                        font.pixelSize: 22
                    }
                }
                
                ColumnLayout {
                    spacing: 0
                    Layout.fillWidth: true
                    Text {
                        text: root.isEdit ? "Edit Skill Source" : "Add Skill Source"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeLargeTitle
                        font.weight: Font.Bold
                        color: Theme.label
                    }
                    Text {
                        text: "Configure a new skill provider to keep your library updated."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeMetadata
                        color: Theme.secondaryLabel
                    }
                }
                
                Button {
                    text: "✕"
                    flat: true
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    onClicked: root.reject()
                    
                    background: Rectangle {
                        radius: 18
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        Behavior on color { ColorAnimation { duration: 200 } }
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 18
                        color: Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
            
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 48
                height: 1
                color: Theme.separator
            }
        }
        
        // Scrollable Form Content
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 400
            clip: true
            contentWidth: availableWidth
            
            ColumnLayout {
                width: parent.width
                spacing: 24
                Layout.margins: 24
                
                // Section 1: Identity
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    
                    RowLayout {
                        spacing: 8
                        Rectangle { width: 4; height: 16; radius: 2; color: Theme.accent }
                        Text {
                            text: "Source Identity"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeSectionTitle
                            font.weight: Font.Bold
                            color: Theme.label
                        }
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "Display Name"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; font.weight: Font.Medium; color: Theme.secondaryLabel }
                            TextField { 
                                id: nameInput
                                placeholderText: "e.g. Community Skills"
                                Layout.fillWidth: true
                                selectByMouse: true
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                color: Theme.label
                                leftPadding: 16
                                rightPadding: 16
                                topPadding: 12
                                bottomPadding: 12
                                background: Rectangle { 
                                    radius: Theme.radiusField
                                    color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                    border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                    border.width: parent.activeFocus ? 2 : 1
                                    Behavior on border.color { ColorAnimation { duration: 200 } }
                                }
                            }
                        }
                        
                        ColumnLayout {
                            Layout.preferredWidth: 140
                            spacing: 6
                            Text { text: "Protocol"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; font.weight: Font.Medium; color: Theme.secondaryLabel }
                            ComboBox { 
                                id: typeCombo
                                model: ["npm", "git", "custom"]
                                Layout.fillWidth: true
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                
                                delegate: ItemDelegate {
                                    width: typeCombo.width
                                    contentItem: Text {
                                        text: modelData.toUpperCase()
                                        color: Theme.label
                                        font: typeCombo.font
                                        elide: Text.ElideRight
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    highlighted: typeCombo.highlightedIndex === index
                                    background: Rectangle {
                                        color: highlighted ? Theme.glassHover : "transparent"
                                        radius: 8
                                        anchors.margins: 4
                                    }
                                }
                                
                                background: Rectangle {
                                    radius: Theme.radiusField
                                    color: Theme.glassHover
                                    border.color: Theme.glassBorder
                                    border.width: 1
                                }

                                contentItem: Text {
                                    text: typeCombo.displayText.toUpperCase()
                                    color: Theme.label
                                    font: typeCombo.font
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: 16
                                }
                            }
                        }
                    }
                }
                
                // Section 2: Technical Configuration
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    
                    RowLayout {
                        spacing: 8
                        Rectangle { width: 4; height: 16; radius: 2; color: Theme.accent }
                        Text {
                            text: "Technical Configuration"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeSectionTitle
                            font.weight: Font.Bold
                            color: Theme.label
                        }
                    }
                    
                    // NPM specific
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        visible: typeCombo.currentText === "npm"
                        
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "Package Name"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; font.weight: Font.Medium; color: Theme.secondaryLabel }
                            TextField { 
                                id: packageInput
                                placeholderText: "@my-org/skill-package"
                                Layout.fillWidth: true
                                selectByMouse: true
                                font.family: Theme.fontFamily
                                leftPadding: 16
                                padding: 12
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
                            spacing: 6
                            Text { text: "Installation Arguments"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; font.weight: Font.Medium; color: Theme.secondaryLabel }
                            TextField { 
                                id: argsInput
                                placeholderText: "--force --no-cache"
                                Layout.fillWidth: true
                                selectByMouse: true
                                font.family: Theme.fontFamily
                                leftPadding: 16
                                padding: 12
                                background: Rectangle { 
                                    radius: Theme.radiusField
                                    color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                    border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                    border.width: parent.activeFocus ? 2 : 1
                                }
                            }
                        }
                    }
                    
                    // Git specific
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: typeCombo.currentText === "git"
                        Text { text: "Git Repository URL"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; font.weight: Font.Medium; color: Theme.secondaryLabel }
                        TextField { 
                            id: repoInput
                            placeholderText: "https://github.com/user/skills.git"
                            Layout.fillWidth: true
                            selectByMouse: true
                            font.family: Theme.fontFamily
                            leftPadding: 16
                            padding: 12
                            background: Rectangle { 
                                radius: Theme.radiusField
                                color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                border.width: parent.activeFocus ? 2 : 1
                            }
                        }
                    }
                    
                    // Custom specific
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: typeCombo.currentText === "custom"
                        Text { text: "Shell Command"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; font.weight: Font.Medium; color: Theme.secondaryLabel }
                        TextField { 
                            id: cmdInput
                            placeholderText: "bash ./update-skills.sh"
                            Layout.fillWidth: true
                            selectByMouse: true
                            font.family: Theme.fontFamily
                            leftPadding: 16
                            padding: 12
                            background: Rectangle { 
                                radius: Theme.radiusField
                                color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                border.width: parent.activeFocus ? 2 : 1
                            }
                        }
                    }
                    
                    // Common Path
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: "Target Directory"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeMetadata; font.weight: Font.Medium; color: Theme.secondaryLabel }
                        RowLayout {
                            spacing: 12
                            TextField { 
                                id: pathInput
                                placeholderText: "Select folder for downloaded skills..."
                                Layout.fillWidth: true
                                selectByMouse: true
                                font.family: Theme.fontFamily
                                leftPadding: 16
                                padding: 12
                                background: Rectangle { 
                                    radius: Theme.radiusField
                                    color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                    border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                    border.width: parent.activeFocus ? 2 : 1
                                }
                            }
                            Button {
                                text: "📁"
                                Layout.preferredWidth: 46
                                Layout.preferredHeight: 46
                                onClicked: folderPicker.open()
                                background: Rectangle {
                                    radius: Theme.radiusSmall
                                    color: parent.hovered ? Theme.glassHover : "transparent"
                                    border.color: Theme.glassBorder
                                    border.width: 1
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // Footer Actions
        Rectangle {
            Layout.fillWidth: true
            height: 90
            color: "transparent"
            
            Rectangle {
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 48
                height: 1
                color: Theme.separator
            }
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 16
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: "Cancel"
                    Layout.preferredWidth: 110
                    Layout.preferredHeight: 44
                    onClicked: root.reject()
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.glassBorder
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 200 } }
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
                    text: root.isEdit ? "Save Changes" : "Create Source"
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 44
                    enabled: nameInput.text !== "" && (packageInput.text !== "" || repoInput.text !== "" || cmdInput.text !== "")
                    
                    onClicked: {
                        let data = {
                            "name": nameInput.text,
                            "source_type": typeCombo.currentText,
                            "package_name": packageInput.text,
                            "repository_url": repoInput.text,
                            "local_path": pathInput.text,
                            "install_args": argsInput.text,
                            "update_command": cmdInput.text
                        }
                        if (root.isEdit) {
                            AppController.updateUpdateSource(root.editIndex, data)
                        } else {
                            AppController.addSkillSource(data)
                        }
                        root.accept()
                    }
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: !parent.enabled ? Theme.secondaryLabel : (parent.down ? Theme.accent : (parent.hovered ? Theme.accent + "EE" : Theme.accent))
                        Behavior on color { ColorAnimation { duration: 200 } }
                        
                        layer.enabled: parent.enabled
                        layer.effect: DropShadow {
                            radius: 8
                            color: Theme.accent + "44"
                            verticalOffset: 2
                        }
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

    // Inner folder picker for the path input
    FolderPickerNative {
        id: folderPicker
        mode: "path"
        onFolderSelected: (path) => pathInput.text = path
    }
}
