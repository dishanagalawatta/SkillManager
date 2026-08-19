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
import ".."
import App 1.0

Dialog {
    id: root
    
    property int editIndex: -1
    property bool isEdit: editIndex !== -1
    property string saveError: ""
    property bool showAdvancedOverrides: false
    property alias showNpxAdvanced: root.showAdvancedOverrides
    property bool userEditedName: false
    property bool userEditedProtocol: false
    property bool isInternalUpdating: false
    
    property real targetHeight: {
        if (typeCombo && typeCombo.currentValue === "custom") return 560
        if (root.showAdvancedOverrides) {
            return (typeCombo && typeCombo.currentValue === "npx") ? 720 : 620
        }
        return 440
    }

    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    width: Math.min(680, Overlay.overlay ? Overlay.overlay.width - 32 : 680)
    height: Math.min(targetHeight, Overlay.overlay ? Overlay.overlay.height - 32 : targetHeight)

    Behavior on height {
        NumberAnimation {
            duration: 250
            easing.type: Easing.OutCubic
        }
    }

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
            npxRepoInput.text = ""
            pathInput.text = ""
            argsInput.text = ""
            cmdInput.text = ""
            tokenInput.text = ""
            npxTokenInput.text = ""
            verificationStatus.text = ""
            npxVerificationStatus.text = ""
            root.saveError = ""
            root.showAdvancedOverrides = false
            root.userEditedName = false
            root.userEditedProtocol = false
            root.isInternalUpdating = false
        }
    }

    function handlePackageInputChanged(rawText) {
        if (root.isInternalUpdating || root.isEdit) return
        let text = rawText ? rawText.trim() : ""
        if (text === "") {
            if (!root.userEditedName) nameInput.text = ""
            return
        }

        try {
            let metaStr = AppController.detectPackageMetadata(text)
            let meta = JSON.parse(metaStr)

            // Auto-detect Display Name if user hasn't typed a custom one
            if (!root.userEditedName && meta.display_name) {
                nameInput.text = meta.display_name
            }

            // Auto-detect Protocol if user hasn't explicitly selected one
            if (!root.userEditedProtocol && meta.source_type) {
                let types = ["npx", "git", "custom"]
                let targetIdx = types.indexOf(meta.source_type)
                if (targetIdx !== -1 && targetIdx !== typeCombo.currentIndex) {
                    root.isInternalUpdating = true
                    typeCombo.currentIndex = targetIdx
                    if (meta.source_type === "git" && meta.repository_url) {
                        repoInput.text = meta.repository_url
                    } else if (meta.source_type === "npx" && meta.package_name) {
                        packageInput.text = meta.package_name
                    } else if (meta.source_type === "custom" && meta.update_command) {
                        cmdInput.text = meta.update_command
                    }
                    root.isInternalUpdating = false
                }
            }
        } catch (e) {
            console.log("Error in handlePackageInputChanged:", e)
        }
    }

    function loadPackage(data) {
        root.isInternalUpdating = true
        root.userEditedName = true
        root.userEditedProtocol = true
        nameInput.text = data.name || ""
        let types = ["npx", "git", "custom"]
        let idx = types.indexOf(data.source_type)
        typeCombo.currentIndex = idx !== -1 ? idx : 0
        
        packageInput.text = data.package_name || ""
        repoInput.text = data.repository_url || ""
        npxRepoInput.text = data.repository_url || ""
        tokenInput.text = data.github_token || ""
        npxTokenInput.text = data.github_token || ""
        pathInput.text = data.package_path || data.local_path || ""
        argsInput.text = data.package_args || data.install_args || ""
        cmdInput.text = data.update_command || ""
        currentVerCmdInput.text = data.current_version_command || ""
        latestVerCmdInput.text = data.latest_version_command || ""
        verificationStatus.text = ""
        npxVerificationStatus.text = ""
        root.saveError = ""
        root.showAdvancedOverrides = !!(
            (data.source_type === "npx" && (data.package_args || data.install_args || data.repository_url || data.github_token || data.current_version_command || data.latest_version_command)) ||
            (data.source_type === "git" && (data.github_token || data.current_version_command || data.latest_version_command))
        )
        root.isInternalUpdating = false
    }



    function setNpxAdvanced(val) {
        root.showAdvancedOverrides = val
    }

    function setAdvancedOverrides(val) {
        root.showAdvancedOverrides = val
    }

    function scrollDown(amt) {
        if (contentScroll && contentScroll.contentItem) {
            contentScroll.contentItem.contentY = amt
        }
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
        SmoothScrollView {
            id: contentScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Pane {
                id: formPane
                width: contentScroll.width - contentScroll.leftPadding - contentScroll.rightPadding
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
                                    onTextEdited: {
                                        if (!root.isInternalUpdating) {
                                            root.userEditedName = (nameInput.text.trim() !== "")
                                        }
                                    }
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
                                        ListElement { text: "NPX Package"; value: "npx" }
                                        ListElement { text: "GitHub Repository"; value: "git" }
                                        ListElement { text: "Custom Script"; value: "custom" }
                                    }
                                    textRole: "text"
                                    valueRole: "value"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 40
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    onActivated: (index) => {
                                        if (!root.isInternalUpdating) {
                                            root.userEditedProtocol = true
                                        }
                                    }

                                    indicator: Image {
                                        x: typeCombo.width - width - 12
                                        y: (typeCombo.height - height) / 2
                                        width: 14
                                        height: 14
                                        source: AppController.ui_controller.getAssetUri("ui/dropdown-arrow-icon.svg")
                                        sourceSize.width: 28
                                        sourceSize.height: 28
                                        fillMode: Image.PreserveAspectFit
                                        smooth: true
                                        opacity: 0.8
                                    }
                                    
                                    background: Rectangle {
                                        radius: Theme.radiusField
                                        color: parent.activeFocus ? Theme.glassActive : (typeCombo.hovered ? Theme.glassHover : Theme.glassPill)
                                        border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                        border.width: 1
                                    }

                                    contentItem: Text {
                                        text: typeCombo.currentText
                                        color: Theme.label
                                        font: typeCombo.font
                                        verticalAlignment: Text.AlignVCenter
                                        leftPadding: 12
                                        rightPadding: 28
                                        elide: Text.ElideRight
                                    }

                                    delegate: ItemDelegate {
                                        width: typeCombo.width
                                        height: 34
                                        padding: 0
                                        hoverEnabled: true
                                        contentItem: Text {
                                            leftPadding: 12
                                            rightPadding: 12
                                            text: model.text !== undefined ? model.text : (modelData !== undefined ? modelData : "")
                                            color: Theme.label
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 13
                                            elide: Text.ElideRight
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                        background: Rectangle {
                                            radius: 6
                                            color: (hovered || typeCombo.highlightedIndex === index) ? Theme.glassHover : "transparent"
                                        }
                                    }

                                    popup: Popup {
                                        y: typeCombo.height + 4
                                        width: typeCombo.width
                                        padding: 6
                                        implicitHeight: Math.min(contentItem.implicitHeight + topPadding + bottomPadding, 200)
                                        contentItem: ListView {
                                            clip: true
                                            implicitHeight: contentHeight
                                            model: typeCombo.delegateModel
                                            boundsBehavior: Flickable.StopAtBounds
                                        }
                                        background: Rectangle {
                                            radius: Theme.radiusField
                                            color: Theme.glassPill
                                            border.color: Theme.glassBorder
                                            border.width: 1
                                        }
                                    }
                                }

                            }
                        }
                        
                        // NPX specific
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: typeCombo.currentValue === "npx"
                            
                            Text { text: "NPM Package / Source"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
                            TextField { 
                                id: packageInput
                                placeholderText: "@my-org/skill-package or vercel-labs/skills"
                                Accessible.role: Accessible.EditableText
                                Accessible.name: "NPM Package / Source"
                                Layout.fillWidth: true
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                                padding: 12
                                rightPadding: 36
                                color: Theme.label
                                placeholderTextColor: Theme.secondaryLabel
                                onTextEdited: {
                                    root.handlePackageInputChanged(packageInput.text)
                                }
                                background: Rectangle { 
                                    radius: Theme.radiusField
                                    color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                    border.color: parent.activeFocus ? Theme.accent : (packageInput.text.trim().length > 0 ? Theme.alpha(Theme.success, 0.5) : Theme.glassBorder)
                                    border.width: 1

                                    Rectangle {
                                        anchors.right: parent.right
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 20
                                        height: 20
                                        radius: 10
                                        color: Theme.alpha(Theme.success, 0.15)
                                        border.color: Theme.success
                                        border.width: 1
                                        visible: packageInput.text.trim().length > 0

                                        Text {
                                            anchors.centerIn: parent
                                            text: "✓"
                                            font.pixelSize: 11
                                            font.weight: Font.Bold
                                            color: Theme.success
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Git specific
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: typeCombo.currentValue === "git"
                            
                            Text { text: "Repository URL"; font.family: Theme.fontFamily; font.pixelSize: 11; color: Theme.secondaryLabel }
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
                                    onTextEdited: {
                                        root.handlePackageInputChanged(repoInput.text)
                                    }
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

                            Text { 
                                id: verificationStatus
                                text: ""
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeMetadata
                                font.weight: Font.Medium
                                color: text.includes("✓") ? Theme.success : (text.includes("✗") ? Theme.danger : Theme.accent)
                                visible: text !== ""
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
                                onTextEdited: {
                                    root.handlePackageInputChanged(cmdInput.text)
                                }
                                background: Rectangle { 
                                    radius: Theme.radiusField
                                    color: parent.activeFocus ? Theme.glassActive : Theme.glassHover
                                    border.color: parent.activeFocus ? Theme.accent : Theme.glassBorder
                                    border.width: 1
                                }
                            }
                        }
                        // Package Path
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
                        }

                        // Advanced Overrides Toggle (NPX and Git)
                        ActionButton {
                            text: root.showAdvancedOverrides ? "▾ Hide Advanced Overrides" : "▸ Advanced Overrides (Optional)"
                            flat: true
                            Layout.preferredHeight: 26
                            visible: typeCombo.currentValue === "npx" || typeCombo.currentValue === "git"
                            onClicked: root.showAdvancedOverrides = !root.showAdvancedOverrides
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                color: Theme.accent
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        // Collapsible NPX Overrides
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: typeCombo.currentValue === "npx" && root.showAdvancedOverrides

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                Text { 
                                    text: "Installation Arguments (Optional)"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    color: Theme.secondaryLabel 
                                }
                                TextField { 
                                    id: argsInput
                                    placeholderText: "--force --no-cache"
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: "Installation Arguments (Optional)"
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
                                Layout.fillWidth: true
                                spacing: 4
                                Text { 
                                    text: "Upstream Repository URL (Optional Override)"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    color: Theme.secondaryLabel 
                                }
                                RowLayout {
                                    spacing: 12
                                    TextField { 
                                        id: npxRepoInput
                                        placeholderText: "https://github.com/user/skills.git"
                                        Accessible.role: Accessible.EditableText
                                        Accessible.name: "Upstream Repository URL"
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
                                        enabled: npxRepoInput.text.length > 0
                                        Layout.preferredHeight: 40
                                        Layout.preferredWidth: 100
                                        onClicked: {
                                            npxVerificationStatus.text = "Validating..."
                                            let tag = AppController.verifyGitPackage(npxRepoInput.text, npxTokenInput.text)
                                            if (tag) {
                                                npxVerificationStatus.text = "✓ Connection Successful (Latest: " + tag + ")"
                                            } else {
                                                npxVerificationStatus.text = "✗ Connection Failed"
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
                                Text { 
                                    id: npxVerificationStatus
                                    text: ""
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeMetadata
                                    font.weight: Font.Medium
                                    color: text.includes("✓") ? Theme.success : (text.includes("✗") ? Theme.danger : Theme.accent)
                                    visible: text !== ""
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
                                    id: npxTokenInput
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
                        }

                        // Collapsible Git Overrides
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: typeCombo.currentValue === "git" && root.showAdvancedOverrides

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
                        }

                        // Advanced Versioning Commands (Visible when Custom mode, or when Advanced Overrides is open for NPX/Git)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: typeCombo.currentValue === "custom" || root.showAdvancedOverrides
                            
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
                                        placeholderText: typeCombo.currentValue === "npx" ? "e.g. npx skills check" : (typeCombo.currentValue === "git" ? "e.g. git describe --tags" : "e.g. ./version.sh --current")
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
                                        placeholderText: typeCombo.currentValue === "npx" ? "e.g. npm view @org/skills version" : (typeCombo.currentValue === "git" ? "e.g. git ls-remote --tags" : "e.g. ./version.sh --latest")
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
                
                Text {
                    text: root.saveError
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeMetadata
                    font.weight: Font.Medium
                    color: Theme.danger
                    visible: root.saveError !== ""
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                }
                
                Item { Layout.fillWidth: true; visible: root.saveError === "" }
                
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
                    enabled: nameInput.text.trim() !== "" && (
                        (typeCombo.currentValue === "npx" && (packageInput.text.trim() !== "" || cmdInput.text.trim() !== "")) ||
                        (typeCombo.currentValue === "git" && repoInput.text.trim() !== "") ||
                        (typeCombo.currentValue === "custom" && cmdInput.text.trim() !== "")
                    )

                    
                    onClicked: {
                        let data = {
                            "name": nameInput.text,
                            "source_type": typeCombo.currentValue,
                            "package_name": packageInput.text,
                            "repository_url": typeCombo.currentValue === "git" ? repoInput.text : npxRepoInput.text,
                            "github_token": typeCombo.currentValue === "git" ? tokenInput.text : npxTokenInput.text,
                            "package_path": pathInput.text,
                            "package_args": argsInput.text,
                            "update_command": cmdInput.text,
                            "current_version_command": currentVerCmdInput.text,
                            "latest_version_command": latestVerCmdInput.text
                        }

                        if (root.isEdit) {
                            let editResult = JSON.parse(AppController.updateUpdatePackage(root.editIndex, data))
                            if (editResult.ok) {
                                root.accept()
                            } else {
                                root.saveError = editResult.error || "Unknown error occurred."
                            }
                        } else {
                            let result = JSON.parse(AppController.addSkillPackage(data))
                            if (result.ok) {
                                root.accept()
                            } else {
                                root.saveError = result.error || "Unknown error occurred."
                            }
                        }
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
