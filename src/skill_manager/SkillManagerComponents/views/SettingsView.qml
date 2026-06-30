import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

Item {
    id: sv_root

    // Current settings sub-tab (General / Shortcuts / About). A plain int
    // property is used instead of a hidden TabBar because a TabBar with
    // height: 0 / visible: false may not allocate its TabButton children,
    // which leaves currentIndex at -1 and hides every StackLayout child.
    property int settingsTab: 0

    component SettingsRow: RowLayout {
        id: sr
        property string titleText
        property string descriptionText: ""
        default property alias controlContent: controlContainer.data
        
        Layout.fillWidth: true
        spacing: 16
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            
            Text {
                text: sr.titleText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.label
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Text {
                visible: sr.descriptionText !== ""
                text: sr.descriptionText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeCaption
                color: Theme.secondaryLabel
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }
        
        Item {
            id: controlContainer
            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
            implicitWidth: childrenRect.width
            implicitHeight: childrenRect.height
        }
    }
    
    component Separator: Rectangle {
        Layout.fillWidth: true
        height: 1
        color: Theme.separator
        opacity: 0.5
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 20

        // Header
        ColumnLayout {
            spacing: 4
            Text {
                text: "Settings"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeHeading
                font.weight: Font.Bold
                color: Theme.label
            }
            Text {
                text: "Configure application preferences and appearance."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeBody
                color: Theme.secondaryLabel
            }
        }

        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: Theme.radiusPill

            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 4

                TabButton {
                    id: generalTab
                    text: "General"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    checked: settingsTab === 0
                    onClicked: settingsTab = 0
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: parent.checked ? Font.Bold : Font.Normal
                        color: parent.checked ? Theme.accent : Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: generalTab.checked ? Theme.glassHover : "transparent"
                        radius: Theme.radiusPill - 4
                    }
                }
                TabButton {
                    id: shortcutsTab
                    text: "Shortcuts"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    checked: settingsTab === 1
                    onClicked: settingsTab = 1
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: parent.checked ? Font.Bold : Font.Normal
                        color: parent.checked ? Theme.accent : Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: shortcutsTab.checked ? Theme.glassHover : "transparent"
                        radius: Theme.radiusPill - 4
                    }
                }
                TabButton {
                    id: aboutTab
                    text: "About"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    checked: settingsTab === 2
                    onClicked: settingsTab = 2
                    
                    contentItem: Text {
                        text: parent.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: parent.checked ? Font.Bold : Font.Normal
                        color: parent.checked ? Theme.accent : Theme.secondaryLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: aboutTab.checked ? Theme.glassHover : "transparent"
                        radius: Theme.radiusPill - 4
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: settingsTab

            // Settings Content (General)
            SmoothScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: width - leftPadding - rightPadding

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 20

                    // Appearance Section
                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: appearanceLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: appearanceLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "Appearance"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                SettingsRow {
                                    titleText: "Dark Mode"
                                    GlassSwitch {
                                        checked: AppController.ui_controller ? AppController.ui_controller.darkMode : false
                                        onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.darkMode = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Reduced Motion"
                                    GlassSwitch {
                                        checked: AppController.ui_controller ? AppController.ui_controller.reducedMotion : false
                                        onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.setReducedMotion(checked)
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Compact List Rows"
                                    GlassSwitch {
                                        checked: AppController.ui_controller ? AppController.ui_controller.compactListRows : false
                                        onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.setCompactListRows(checked)
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Scroll Speed"
                                    descriptionText: "Multiplier: " + (AppController.config_controller ? AppController.config_controller.scrollSpeedMultiplier.toFixed(1) : "1.0") + "x"
                                    Slider {
                                        width: 150
                                        from: 0.5
                                        to: 5.0
                                        stepSize: 0.1
                                        value: AppController.config_controller ? AppController.config_controller.scrollSpeedMultiplier : 1.0
                                        onMoved: if (AppController.config_controller) AppController.config_controller.scrollSpeedMultiplier = value
                                    }
                                }
                            }
                        }
                    }

                    // Projects Section
                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: projectsSettingsLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: projectsSettingsLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "Projects"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    
                                    Text {
                                        text: "Top Bar Clients"
                                        font.family: Theme.fontFamily
                                        color: Theme.label
                                        font.pixelSize: Theme.sizeBody
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        
                                        GlassDropdown {
                                            Layout.fillWidth: true
                                            model: AppController.config_controller ? AppController.config_controller.availableClientFormats : []
                                            currentIndex: (AppController.config_controller && AppController.config_controller.topBarClients.length > 0) ? Math.max(0, model.indexOf(AppController.config_controller.topBarClients[0])) : 0
                                            onActivated: (index) => {
                                                if (AppController.config_controller) {
                                                    var arr = [];
                                                    var current = AppController.config_controller.topBarClients;
                                                    var available = AppController.config_controller.availableClientFormats;
                                                    for (var i = 0; i < 4; i++) {
                                                        arr.push(i < current.length ? current[i] : available[i % available.length]);
                                                    }
                                                    arr[0] = model[index];
                                                    AppController.config_controller.topBarClients = arr;
                                                }
                                            }
                                        }
                                        GlassDropdown {
                                            Layout.fillWidth: true
                                            model: AppController.config_controller ? AppController.config_controller.availableClientFormats : []
                                            currentIndex: (AppController.config_controller && AppController.config_controller.topBarClients.length > 1) ? Math.max(0, model.indexOf(AppController.config_controller.topBarClients[1])) : 1
                                            onActivated: (index) => {
                                                if (AppController.config_controller) {
                                                    var arr = [];
                                                    var current = AppController.config_controller.topBarClients;
                                                    var available = AppController.config_controller.availableClientFormats;
                                                    for (var i = 0; i < 4; i++) {
                                                        arr.push(i < current.length ? current[i] : available[i % available.length]);
                                                    }
                                                    arr[1] = model[index];
                                                    AppController.config_controller.topBarClients = arr;
                                                }
                                            }
                                        }
                                        GlassDropdown {
                                            Layout.fillWidth: true
                                            model: AppController.config_controller ? AppController.config_controller.availableClientFormats : []
                                            currentIndex: (AppController.config_controller && AppController.config_controller.topBarClients.length > 2) ? Math.max(0, model.indexOf(AppController.config_controller.topBarClients[2])) : 2
                                            onActivated: (index) => {
                                                if (AppController.config_controller) {
                                                    var arr = [];
                                                    var current = AppController.config_controller.topBarClients;
                                                    var available = AppController.config_controller.availableClientFormats;
                                                    for (var i = 0; i < 4; i++) {
                                                        arr.push(i < current.length ? current[i] : available[i % available.length]);
                                                    }
                                                    arr[2] = model[index];
                                                    AppController.config_controller.topBarClients = arr;
                                                }
                                            }
                                        }
                                        GlassDropdown {
                                            Layout.fillWidth: true
                                            model: AppController.config_controller ? AppController.config_controller.availableClientFormats : []
                                            currentIndex: (AppController.config_controller && AppController.config_controller.topBarClients.length > 3) ? Math.max(0, model.indexOf(AppController.config_controller.topBarClients[3])) : 3
                                            onActivated: (index) => {
                                                if (AppController.config_controller) {
                                                    var arr = [];
                                                    var current = AppController.config_controller.topBarClients;
                                                    var available = AppController.config_controller.availableClientFormats;
                                                    for (var i = 0; i < 4; i++) {
                                                        arr.push(i < current.length ? current[i] : available[i % available.length]);
                                                    }
                                                    arr[3] = model[index];
                                                    AppController.config_controller.topBarClients = arr;
                                                }
                                            }
                                        }
                                    }
                                }

                                Separator {}

                                SettingsRow {
                                    titleText: "Project Order"
                                    descriptionText: "Change the order projects appear in selectors"
                                    ActionButton {
                                        text: "Reorder..."
                                        width: 100
                                        height: 36
                                        enabled: AppController.projects.length > 1
                                        onClicked: sv_reorderDialog.open()

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
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Auto-minimize on Screenshot"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.autoMinimizeOnScreenshot : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoMinimizeOnScreenshot = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Auto-minimize on Quick Copy"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.autoMinimizeOnQuickCopy : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoMinimizeOnQuickCopy = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Temporary Screenshots"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.temporaryScreenshots : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.temporaryScreenshots = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Startup View"
                                    GlassDropdown {
                                        width: 170
                                        model: ["Last Selected", "Library", "QuickCopy", "Updates", "Settings"]
                                        currentIndex: AppController.ui_controller ? Math.max(0, model.indexOf(AppController.ui_controller.startupView)) : 0
                                        onActivated: (index) => { if (AppController.ui_controller) AppController.ui_controller.setStartupView(model[index]) }
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Default Client"
                                    GlassDropdown {
                                        width: 170
                                        model: {
                                            let fmts = ["Last Selected"];
                                            if (AppController.clientFormats) {
                                                fmts = fmts.concat(AppController.clientFormats);
                                            }
                                            return fmts;
                                        }
                                        currentIndex: AppController ? Math.max(0, model.indexOf(AppController.defaultClient)) : 0
                                        onActivated: (index) => { if (AppController) AppController.setDefaultClient(model[index]) }
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Remember Filters"
                                    GlassSwitch {
                                        checked: AppController.ui_controller ? AppController.ui_controller.rememberFilters : true
                                        onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.setRememberFilters(checked)
                                    }
                                }
                                
                                Item { Layout.preferredHeight: 4 }

                                ActionButton {
                                    Layout.preferredHeight: 36
                                    Layout.fillWidth: true
                                    text: "Reset UI State"
                                    onClicked: (mouse) => { if (AppController.ui_controller) AppController.ui_controller.resetUiState() }
                                    background: Rectangle {
                                        radius: Theme.radiusButton
                                        color: parent.hovered ? Theme.glassHover : "transparent"
                                        border.color: Theme.glassBorder
                                        border.width: 1
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        font.weight: Font.Bold
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }
                    }

                    // Skill Packages Section
                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: updatesSettingsLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: updatesSettingsLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "Skill Packages"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                SettingsRow {
                                    titleText: "Auto Update Mode"
                                    GlassDropdown {
                                        width: 100
                                        property var internalValues: ["off", "prompt", "silent"]
                                        model: ["Off", "Prompt", "Silent"]
                                        currentIndex: AppController.config_controller ? Math.max(0, internalValues.indexOf(AppController.config_controller.skillPackageAutoUpdateMode)) : 1
                                        onActivated: {
                                            if (AppController.config_controller) AppController.config_controller.skillPackageAutoUpdateMode = internalValues[index]
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Diagnostics Section
                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: diagnosticsSettingsLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: diagnosticsSettingsLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "Diagnostics"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                SettingsRow {
                                    titleText: "Enable Diagnostic Logging"
                                    descriptionText: "Records structured events to help troubleshoot issues.\nMay slightly impact performance when enabled."
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.diagnosticLogging : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.diagnosticLogging = checked
                                    }
                                }
                            }
                        }
                    }

                    // Maintenance Section
                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: maintenanceSettingsLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: maintenanceSettingsLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "Maintenance"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                SettingsRow {
                                    titleText: "Rebuild Skill Cache"
                                    descriptionText: "Clears all caches (index + granular) and forces a full re-scan from disk.\nUse if skills appear incorrectly, projects show wrong entries, or deleted skills still appear."
                                    ActionButton {
                                        id: rebuildCacheButton
                                        text: "Rebuild Cache"
                                        width: 120
                                        height: 36
                                        onClicked: AppController.rebuildCache()
                                        hoverEnabled: true

                                        background: Rectangle {
                                            radius: Theme.radiusButton
                                            color: parent.hovered ? Theme.glassHover : "transparent"
                                            border.color: Theme.glassBorder
                                            border.width: 1
                                        }

                                        contentItem: Text {
                                            text: parent.text
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeBody
                                            font.weight: Font.Medium
                                            color: Theme.accent
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }

                                        ToolTip {
                                            parent: rebuildCacheButton
                                            text: "Force a full re-scan from disk.\nClears all caches and reloads."
                                            delay: 500
                                            visible: rebuildCacheButton.hovered
                                        }
                                    }
                                }
                            }
                        }
                    }


                }
            }
            
            ShortcutsSettings {}

            // About Tab
            SmoothScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: width - leftPadding - rightPadding

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 20

                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: aboutLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: aboutLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 16
                            
                            RowLayout {
                                spacing: 16
                                Layout.fillWidth: true

                                Rectangle {
                                    width: 80
                                    height: 80
                                    radius: 16
                                    color: Theme.glassPill
                                    border.color: Theme.glassBorder
                                    border.width: 1
                                    
                                    Image {
                                        anchors.centerIn: parent
                                        width: 48
                                        height: 48
                                        source: AppController.ui_controller.getAssetUri("brand/logo.svg")
                                        fillMode: Image.PreserveAspectFit
                                    }
                                }
                                
                                ColumnLayout {
                                    spacing: 4
                                    Text {
                                        text: "SkillManager"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 24
                                        font.weight: Font.Bold
                                        color: Theme.label
                                    }
                                    Text {
                                        text: "Version " + AppController.app_update_controller.currentVersion
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeBody
                                        color: Theme.secondaryLabel
                                    }
                                }

                                Item {
                                    Layout.fillWidth: true
                                }

                                RowLayout {
                                    spacing: 8
                                    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight

                                    ActionButton {
                                        id: updateNowBtn
                                        visible: !AppController.app_update_controller.isCheckingForUpdates
                                        labelText: {
                                            if (AppController.app_update_controller.updateAvailable) return "Update Available"
                                            if (AppController.app_update_controller.hasCheckedForUpdates) return "Up to Date"
                                            return "Check for Updates"
                                        }
                                        role: (AppController.app_update_controller.updateAvailable) ? "primary" : "secondary"
                                        enabled: {
                                            if (AppController.app_update_controller.updateAvailable) return true
                                            if (AppController.app_update_controller.hasCheckedForUpdates) return false
                                            return true
                                        }
                                        onClicked: (mouse) => {
                                            if (AppController.app_update_controller.updateAvailable) {
                                                AppController.app_update_controller.openReleasesPage()
                                            } else {
                                                AppController.app_update_controller.checkForUpdates(true)
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            Text {
                                text: "The ultimate tool for managing and discovering AI coding skills. Automate your workflow, share patterns, and boost your productivity."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeBody
                                color: Theme.label
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            ColumnLayout {
                                spacing: 4
                                Text {
                                    text: "Credits"
                                    font.family: Theme.fontFamily
                                    font.weight: Font.Bold
                                    color: Theme.label
                                }
                                Text {
                                    text: "Developed by Dishan Agalawatta"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeCaption
                                    color: Theme.secondaryLabel
                                }
                                Text {
                                    text: "Powered by PySide6"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeCaption
                                    color: Theme.secondaryLabel
                                }
                            }

                        }
                    }

                    // Diagnostics card (separate from About card so its
                    // expanded body has room to render — see the
                    // test_diagnostics_pane_actually_renders_when_expanded
                    // regression test for the exact failure mode this prevents).
                    // Hidden when diagnostic logging is disabled in General settings.
                    GlassPill {
                        id: diagnosticsGlassPill
                        objectName: "diagnosticsGlassPill"
                        Layout.fillWidth: true
                        visible: AppController.config_controller ? AppController.config_controller.diagnosticLogging : false
                        Layout.preferredHeight: visible ? diagnosticsPane.implicitHeight : 0
                        radius: Theme.radiusCard

                        DiagnosticsPane {
                            id: diagnosticsPane
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                        }
                    }
                }
            }
        }
    }

    ProjectReorderDialog {
        id: sv_reorderDialog
    }
}
