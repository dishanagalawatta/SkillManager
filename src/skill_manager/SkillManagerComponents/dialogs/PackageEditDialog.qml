/**
 * Purpose: A comprehensive "Solid Matte" dialog for adding and editing skill packages.
 * Usage:
 * PackageEditDialog {
 *     id: packageDialog
 *     onAccepted: (data) => console.log(data)
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
    
    property int editIndex: -1
    property bool isEdit: editIndex !== -1
    
    x: Math.round((parent.width - width) / 2)
    y: Math.round(Math.max(10, (parent.height - height) / 2))
    width: 650
    height: Math.min(parent.height - 20, 850)
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
            verticalOffset: 12
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
            tokenInput.text = ""
            verificationStatus.text = ""
        }
    }

    function loadPackage(data) {
        nameInput.text = data.name || ""
        let types = ["npm", "git", "custom"]
        let idx = types.indexOf(data.source_type)
        typeCombo.currentIndex = idx !== -1 ? idx : 0
        
        packageInput.text = data.package_name || ""
        repoInput.text = data.repository_url || ""
        tokenInput.text = data.github_token || ""
        pathInput.text = data.package_path || data.local_path || ""
        argsInput.text = data.package_args || data.install_args || ""
        cmdInput.text = data.update_command || ""
        currentVerCmdInput.text = data.current_version_command || ""
        latestVerCmdInput.text = data.latest_version_command || ""
        verificationStatus.text = ""
    }

    contentItem: ColumnLayout {
        spacing: 0
        clip: true
        
        // Compact Header Section
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 16
                spacing: 12
                
                Rectangle {
                    width: 36
                    height: 36
                    radius: 18
                    color: Theme.alpha(Theme.accent, 0.07)
                    Text {
                        anchors.centerIn: parent
                        text: "📦"
                        font.pixelSize: 20
                    }
                }
                
                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true
                    Text {
                        text: root.isEdit ? "Edit Skill Package" : "Add Skill Package"
                        font.family: Theme.fontFamily
                        font.pixelSize: 18
                        font.weight: Font.Bold
                        color: Theme.label
                    }
                    Text {
                        text: "Configure where your skills are fetched and updated from."
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        color: Theme.secondaryLabel
                    }
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
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 48
                height: 1
                color: Theme.separator
            }
        }
        
        // Scrollable Form Content
        ScrollView {
            id: formScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AlwaysOn
                width: 8
                active: true
            }

            Pane {
                id: formPane
                width: formScroll.availableWidth
                padding: 24
                topPadding: 12
                bottomPadding: 32
                background: null
                
                contentItem: ColumnLayout {
                    spacing: 20
                    
                    // Section 1: Identity
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        
                        RowLayout {
                            spacing: 8
                            Rectangle { width: 4; height: 16; radius: 2; color: Theme.accent }
                            Text {
                                text: "Package Identity"
                                font.family: Theme.fontFamily
                                font.pixelSize: 15
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
                                Text { text: "Display Name"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
                                TextField { 
                                    id: nameInput
                                    placeholderText: "e.g. Community Skills"
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: "Display Name"
                                    Layout.fillWidth: true
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    padding: 12
                                    color: Theme.label
                                    placeholderTextColor: Theme.secondaryLabel
                                    background: Rectangle { 
                                        radius: Theme.radiusField
                                        color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                        border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                        border.width: 1
                                    }
                                }
                            }
                            
                            ColumnLayout {
                                Layout.preferredWidth: 160
                                spacing: 6
                                Text { text: "Protocol"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
                                ComboBox { 
                                    id: typeCombo
                                    model: ListModel {
                                        ListElement { text: "NPM Package"; value: "npm" }
                                        ListElement { text: "GitHub Repository"; value: "git" }
                                        ListElement { text: "Custom Script"; value: "custom" }
                                    }
                                    textRole: "text"
                                    valueRole: "value"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 40
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    
                                    background: Rectangle {
                                        radius: Theme.radiusField
                                        color: Theme.glassHover
                                        border.color: Theme.glassBorder
                                        border.width: 1
                                    }

                                    contentItem: Text {
                                        text: typeCombo.currentText
                                        color: Theme.label
                                        font: typeCombo.font
                                        verticalAlignment: Text.AlignVCenter
                                        leftPadding: 12
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
                                font.pixelSize: 15
                                font.weight: Font.Bold
                                color: Theme.label
                            }
                        }
                        
                        // NPM specific
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: typeCombo.currentValue === "npm"
                            
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text { text: "Package Name"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
                                TextField { 
                                    id: packageInput
                                    placeholderText: "@my-org/skill-package"
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: "Package Name"
                                    Layout.fillWidth: true
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    padding: 12
                                    color: Theme.label
                                    placeholderTextColor: Theme.secondaryLabel
                                    background: Rectangle { 
                                        radius: Theme.radiusField
                                        color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                        border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                    }
                                }
                            }
                            
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text { text: "Installation Arguments"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
                                TextField { 
                                    id: argsInput
                                    placeholderText: "--force --no-cache"
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: "Installation Arguments"
                                    Layout.fillWidth: true
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    padding: 12
                                    color: Theme.label
                                    placeholderTextColor: Theme.secondaryLabel
                                    background: Rectangle { 
                                        radius: Theme.radiusField
                                        color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                        border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                    }
                                }
                            }
                        }
                        
                        // Custom specific
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: typeCombo.currentValue === "custom"
                            Text { text: "Shell Command"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
                            TextField { 
                                id: cmdInput
                                placeholderText: "bash ./update-skills.sh"
                                Accessible.role: Accessible.EditableText
                                Accessible.name: "Shell Command"
                                Layout.fillWidth: true
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                                padding: 12
                                color: Theme.label
                                placeholderTextColor: Theme.secondaryLabel
                                background: Rectangle { 
                                    radius: Theme.radiusField
                                    color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                    border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                }
                            }
                        }
                        
                        // Version Tracking (Unified for Git and NPM)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: typeCombo.currentValue === "git" || typeCombo.currentValue === "npm"
                            
                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                                Layout.topMargin: 4
                                Layout.bottomMargin: 4
                            }

                            ColumnLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                
                                RowLayout {
                                    spacing: 8
                                    Text { 
                                        text: "🔗 Version Checking & Sync" 
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 13
                                        font.weight: Font.Bold
                                        color: Theme.label
                                    }
                                }

                                Text { 
                                    text: typeCombo.currentValue === "git" 
                                        ? "Main repository URL for cloning and fetching updates."
                                        : "Optional: Link an upstream GitHub repository to track latest versions." 
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    color: Theme.secondaryLabel
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                            
                            RowLayout {
                                spacing: 12
                                TextField { 
                                    id: repoInput
                                    placeholderText: "https://github.com/user/skills.git"
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: "Repository URL"
                                    Layout.fillWidth: true
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    padding: 12
                                    color: Theme.label
                                    placeholderTextColor: Theme.secondaryLabel
                                    background: Rectangle { 
                                        radius: Theme.radiusField
                                        color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                        border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                        border.width: 1
                                    }
                                }
                                ActionButton {
                                    text: "🔍 Verify"
                                    enabled: repoInput.text.length > 0
                                    Layout.preferredHeight: 40
                                    Layout.preferredWidth: 100
                                    onClicked: {
                                        verificationStatus.text = "Validating..."
                                        let tag = AppController.verifyGitPackage(repoInput.text, tokenInput.text)
                                        if (tag) {
                                            verificationStatus.text = "✓ Connection Successful (Latest: " + tag + ")"
                                        } else {
                                            verificationStatus.text = "✗ Connection Failed"
                                        }
                                    }
                                    background: Rectangle {
                                        radius: Theme.radiusSmall
                                        color: parent.hovered ? Theme.glassHover : Theme.glassPill
                                        border.color: parent.hovered ? Theme.accent : Theme.glassBorder
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 12
                                        font.weight: Font.Bold
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                Text { 
                                    text: "Authentication Token (Optional)"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    color: Theme.secondaryLabel 
                                }
                                TextField { 
                                    id: tokenInput
                                    placeholderText: "ghp_xxxxxxxxxxxx"
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: "Authentication Token (Optional)"
                                    echoMode: TextInput.Password
                                    Layout.fillWidth: true
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    padding: 12
                                    color: Theme.label
                                    placeholderTextColor: Theme.secondaryLabel
                                    background: Rectangle { 
                                        radius: Theme.radiusField
                                        color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                        border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                        border.width: 1
                                    }
                                }
                            }
                            
                            // Advanced Version Commands
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                
                                RowLayout {
                                    spacing: 8
                                    Text { 
                                        text: "Advanced Versioning Commands" 
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 12
                                        font.weight: Font.Bold
                                        color: Theme.secondaryLabel
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Text { text: "Detect Local Version"; font.family: Theme.fontFamily; font.pixelSize: 10; color: Theme.secondaryLabel }
                                        TextField {
                                            id: currentVerCmdInput
                                            placeholderText: "e.g. npm list -g @org/skills --json"
                                            Accessible.role: Accessible.EditableText
                                            Accessible.name: "Detect Local Version"
                                            Layout.fillWidth: true
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 12
                                            color: Theme.label
                                            placeholderTextColor: Theme.secondaryLabel
                                            background: Rectangle { radius: Theme.radiusField; color: Theme.glassHover; border.color: Theme.glassBorder; border.width: 1 }
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Text { text: "Detect Latest Version"; font.family: Theme.fontFamily; font.pixelSize: 10; color: Theme.secondaryLabel }
                                        TextField {
                                            id: latestVerCmdInput
                                            placeholderText: "e.g. npm show @org/skills version"
                                            Accessible.role: Accessible.EditableText
                                            Accessible.name: "Detect Latest Version"
                                            Layout.fillWidth: true
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 12
                                            color: Theme.label
                                            placeholderTextColor: Theme.secondaryLabel
                                            background: Rectangle { radius: Theme.radiusField; color: Theme.glassHover; border.color: Theme.glassBorder; border.width: 1 }
                                        }
                                    }
                                }
                            }

                            Text { 
                                id: verificationStatus
                                text: ""
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.Medium
                                color: text.includes("✓") ? "#4dff88" : (text.includes("✗") ? "#ff4d4d" : Theme.accent)
                                visible: text !== ""
                            }
                        }
                    }
                    
                    // Section 3: Local Configuration
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        
                        RowLayout {
                            spacing: 8
                            Rectangle { width: 4; height: 16; radius: 2; color: Theme.accent }
                            Text {
                                text: "Local Installation"
                                font.family: Theme.fontFamily
                                font.pixelSize: 15
                                font.weight: Font.Bold
                                color: Theme.label
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "Package Path"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
                            RowLayout {
                                spacing: 12
                                TextField { 
                                    id: pathInput
                                    placeholderText: "Select folder where skills will be stored..."
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: "Package Path"
                                    Layout.fillWidth: true
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    padding: 12
                                    color: Theme.label
                                    placeholderTextColor: Theme.secondaryLabel
                                    background: Rectangle { 
                                        radius: Theme.radiusField
                                        color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                        border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                    }
                                }
                                IconButton {
                                    text: "📁"
                                    Layout.preferredWidth: 44
                                    Layout.preferredHeight: 44
                                    onClicked: folderPicker.open()
                                    background: Rectangle {
                                        radius: Theme.radiusSmall
                                        color: parent.hovered ? Theme.glassHover : "transparent"
                                        border.color: Theme.glassBorder
                                        border.width: 1
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        font.pixelSize: 18
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                            Text {
                                text: "The relative or absolute path where skills will be extracted/installed."
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                color: Theme.secondaryLabel
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
        
        // Compact Footer Actions
        Rectangle {
            Layout.fillWidth: true
            height: 64
            color: "transparent"
            
            Rectangle {
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 40
                height: 1
                color: Theme.separator
            }
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                
                Item { Layout.fillWidth: true }
                
                ActionButton {
                    text: "Cancel"
                    Layout.preferredWidth: 90
                    Layout.preferredHeight: 36
                    onClicked: root.reject()
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: parent.hovered ? Theme.glassHover : "transparent"
                        border.color: Theme.glassBorder
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                        color: Theme.label
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                ActionButton {
                    text: root.isEdit ? "Save Changes" : "Create Package"
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 36
                    enabled: nameInput.text !== "" && (packageInput.text !== "" || repoInput.text !== "" || cmdInput.text !== "")
                    
                    onClicked: {
                        let data = {
                            "name": nameInput.text,
                            "source_type": typeCombo.currentValue,
                            "package_name": packageInput.text,
                            "repository_url": repoInput.text,
                            "github_token": tokenInput.text,
                            "package_path": pathInput.text,
                            "package_args": argsInput.text,
                            "update_command": cmdInput.text,
                            "current_version_command": currentVerCmdInput.text,
                            "latest_version_command": latestVerCmdInput.text
                        }
                        if (root.isEdit) {
                            AppController.updateUpdatePackage(root.editIndex, data)
                        } else {
                            AppController.addSkillPackage(data)
                        }
                        root.accept()
                    }
                    
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: !parent.enabled ? Theme.secondaryLabel : (parent.down ? Theme.accent : (parent.hovered ? Theme.alpha(Theme.accent, 0.93) : Theme.accent))
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
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
