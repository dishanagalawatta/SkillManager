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

    // ── Top-bar client selectors ─────────────────────────────────────
    // The bar always shows at least two client formats and accepts at most
    // four; the two defaults cannot be removed from the settings list.
    function _setTopBarClient(index, format) {
        if (!AppController.config_controller || !format) return
        var arr = AppController.config_controller.topBarClients.slice()
        if (index < 0 || index >= arr.length) return
        arr[index] = format
        AppController.config_controller.topBarClients = arr
    }

    function _addTopBarClient() {
        if (!AppController.config_controller) return
        var arr = AppController.config_controller.topBarClients.slice()
        if (arr.length >= 4) return
        var available = AppController.config_controller.availableClientFormats
        var next = ""
        for (var i = 0; i < available.length; i++) {
            if (arr.indexOf(available[i]) === -1) { next = available[i]; break }
        }
        if (next === "") next = available[arr.length % available.length]
        arr.push(next)
        AppController.config_controller.topBarClients = arr
    }

    function _removeTopBarClient(index) {
        if (!AppController.config_controller) return
        var arr = AppController.config_controller.topBarClients.slice()
        if (index < 2 || index >= arr.length) return
        arr.splice(index, 1)
        AppController.config_controller.topBarClients = arr
    }

    component SettingsRow: RowLayout {
        id: sr
        property string titleText
        property string descriptionText: ""
        default property alias controlContent: controlContainer.data
        
        Layout.fillWidth: true
        spacing: sr.width < 450 ? 8 : 16
        
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


        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: 24

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
                    // AT matrix: mutually-exclusive settings tab => PageTab role + checked (click selects, never toggles off).
                    Accessible.role: Accessible.PageTab
                    Accessible.checkable: true
                    Accessible.checked: settingsTab === 0
                    Accessible.name: "General"
                    Accessible.onPressAction: generalTab.clicked()
                    Accessible.onToggleAction: generalTab.clicked()
                    
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
                        radius: 20
                    }
                }
                TabButton {
                    id: shortcutsTab
                    text: "Shortcuts"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    checked: settingsTab === 1
                    onClicked: settingsTab = 1
                    // AT matrix: mutually-exclusive settings tab => PageTab role + checked (click selects, never toggles off).
                    Accessible.role: Accessible.PageTab
                    Accessible.checkable: true
                    Accessible.checked: settingsTab === 1
                    Accessible.name: "Shortcuts"
                    Accessible.onPressAction: shortcutsTab.clicked()
                    Accessible.onToggleAction: shortcutsTab.clicked()
                    
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
                        radius: 20
                    }
                }
                TabButton {
                    id: aboutTab
                    text: "About"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    checked: settingsTab === 2
                    onClicked: settingsTab = 2
                    // AT matrix: mutually-exclusive settings tab => PageTab role + checked (click selects, never toggles off).
                    Accessible.role: Accessible.PageTab
                    Accessible.checkable: true
                    Accessible.checked: settingsTab === 2
                    Accessible.name: "About"
                    Accessible.onPressAction: aboutTab.clicked()
                    Accessible.onToggleAction: aboutTab.clicked()
                    
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
                        radius: 20
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
                objectName: "settingsScroll"
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
                                    titleText: "Scroll Speed"
                                    descriptionText: "Multiplier: " + (scrollSpeedSlider.value ? scrollSpeedSlider.value.toFixed(1) : "1.0") + "x"
                                    GlassSlider {
                                        id: scrollSpeedSlider
                                        width: 150
                                        from: 0.5
                                        to: 5.0
                                        stepSize: 0.1
                                        value: AppController.config_controller ? AppController.config_controller.scrollSpeedMultiplier : 1.0
                                        onMoved: if (AppController.config_controller) AppController.config_controller.scrollSpeedMultiplier = value
                                        Binding on value {
                                            value: AppController.config_controller ? AppController.config_controller.scrollSpeedMultiplier : 1.0
                                            restoreMode: Binding.RestoreBinding
                                        }
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

                                    Text {
                                        Layout.fillWidth: true
                                        text: "The client formats shown as buttons in the Workbench bar. "
                                            + "Two are shown by default - add up to two more."
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        color: Theme.secondaryLabel
                                        wrapMode: Text.WordWrap
                                    }

                                    // One dropdown per configured selector. The two
                                    // default selectors are permanent; the optional
                                    // ones can be removed again.
                                    Repeater {
                                        model: AppController.config_controller ? AppController.config_controller.topBarClients : []

                                        delegate: RowLayout {
                                            id: topClientRow
                                            required property var modelData
                                            required property int index
                                            Layout.fillWidth: true
                                            spacing: 8

                                            GlassDropdown {
                                                Layout.fillWidth: true
                                                model: AppController.config_controller
                                                    ? AppController.config_controller.availableClientFormats : []
                                                currentIndex: Math.max(0, model.indexOf(topClientRow.modelData))
                                                onActivated: (index) => sv_root._setTopBarClient(topClientRow.index, model[index])
                                            }

                                            IconButton {
                                                visible: topClientRow.index >= 2
                                                buttonSize: 28
                                                iconSize: 12
                                                iconSource: AppController.ui_controller.getAssetUri("ui/close-icon.svg")
                                                // Circular plate icon: no resting outline (see IconButton.showRing).
                                                showRing: false
                                                tooltipText: "Remove this selector"
                                                accessibleName: "Remove top bar selector " + (topClientRow.index + 1)
                                                onClicked: (mouse) => sv_root._removeTopBarClient(topClientRow.index)
                                            }
                                        }
                                    }

                                    ActionButton {
                                        objectName: "addTopBarClientBtn"
                                        visible: (AppController.config_controller ? AppController.config_controller.topBarClients.length : 2) < 4
                                        labelText: "+ Add selector"
                                        role: "secondary"
                                        tooltipText: "Show one more client format in the Workbench bar"
                                        onClicked: (mouse) => sv_root._addTopBarClient()
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
                                    titleText: "Auto-minimize on Snap"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.autoMinimizeOnSnap : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoMinimizeOnSnap = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Auto-minimize on Workbench"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.autoMinimizeOnQuickCopy : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoMinimizeOnQuickCopy = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Auto-select Snap in Workbench"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.autoSelectSnapInQuickCopy : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoSelectSnapInQuickCopy = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Copy Snap in Client Format"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.autoCopySnapClientFormat : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoCopySnapClientFormat = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Temporary Screenshots"
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.temporarySnaps : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.temporarySnaps = checked
                                    }
                                }
                                Separator {}
                                SettingsRow {
                                    titleText: "Startup View"
                                    GlassDropdown {
                                        width: 170
                                        // View keys stay "QuickCopy"/"Updates" — only
                                        // the labels were renamed to Workbench/Hub.
                                        model: ["Last Selected", "Library", "Workbench", "Hub", "Settings"]
                                        currentIndex: {
                                            let view = AppController.ui_controller ? AppController.ui_controller.startupView : "Library"
                                            if (view === "Quick Copy") view = "QuickCopy"
                                            if (view === "Updates") view = "Hub"
                                            return Math.max(0, model.indexOf(view))
                                        }
                                        onActivated: (index) => {
                                            if (!AppController.ui_controller) return
                                            let label = model[index]
                                            if (label === "Workbench") label = "QuickCopy"
                                            if (label === "Hub") label = "Updates"
                                            AppController.ui_controller.setStartupView(label)
                                        }
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
                                    titleText: "Auto Update"
                                    descriptionText: "Automatically install skill package updates in the background.\nWhen off, you will be notified when updates are available."
                                    GlassSwitch {
                                        checked: AppController.config_controller ? AppController.config_controller.skillPackageAutoUpdate : false
                                        onCheckedChanged: if (AppController.config_controller) AppController.config_controller.skillPackageAutoUpdate = checked
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
                                Separator {}
                                SettingsRow {
                                    titleText: "Share Anonymous Usage Data"
                                    descriptionText: "Sends anonymous feature-usage events and error reports.\nOnly active when analytics credentials are configured."
                                    GlassSwitch {
                                        checked: AppController.ui_controller ? AppController.ui_controller.telemetryEnabled : false
                                        onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.setTelemetryEnabled(checked)
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
                                        tooltipText: "Force a full re-scan from disk.\nClears all caches and reloads."
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
                                }

                                Item {
                                    Layout.fillWidth: true
                                }
                            }

                            // Application update lifecycle: check, download,
                            // verify and install all live on the controller.
                            AppUpdateCard {
                                objectName: "settingsAppUpdateCard"
                                compact: true
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

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Text {
                                    Layout.fillWidth: true
                                    text: "Found a bug? Export diagnostics and open a prefilled issue."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeBody
                                    color: Theme.secondaryLabel
                                    wrapMode: Text.WordWrap
                                }

                                ActionButton {
                                    objectName: "aboutReportIssueButton"
                                    Layout.preferredHeight: 32
                                    labelText: "Report Issue"
                                    role: "secondary"
                                    iconSource: AppController.ui_controller ? AppController.ui_controller.getAssetUri("ui/tool-external-link.svg") : ""
                                    tooltipText: "Expand diagnostics and open a prefilled issue"
                                    onClicked: {
                                        if (diagnosticsPane) diagnosticsPane.expanded = true
                                        if (AppController.config_controller) {
                                            var url = AppController.config_controller.getReportIssueUrl("", "")
                                            AppController.config_controller.openReportIssue(url)
                                        }
                                    }
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
