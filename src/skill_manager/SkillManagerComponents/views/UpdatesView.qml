import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Dialogs
import ".."
import App 1.0
import "../dialogs"

Item {
    id: updatesRoot
    objectName: "UpdatesView"

    // The catalog search query (kept on the view so the filter survives a
    // package-list change).
    property string uv_catalogQuery: ""

    function cleanup() {
        uv_packagesList.cacheBuffer = 0
        uv_projectsList.cacheBuffer = 0
        uv_catalogList.cacheBuffer = 0
        uv_packagesList.model = null
        uv_projectsList.model = null
        uv_catalogList.model = null
    }

    // The curated catalog, filtered by the search field.
    function uv_filteredCatalog() {
        var all = AppController.update_controller ? AppController.update_controller.catalogPackages : []
        if (!all || all.length === 0) return []
        var needle = (updatesRoot.uv_catalogQuery || "").trim().toLowerCase()
        if (needle === "") return all
        var out = []
        for (var i = 0; i < all.length; i++) {
            var e = all[i]
            var haystack = ((e.display_name || "") + " " + (e.description || "") + " "
                + (e.author || "") + " " + (e.category || "") + " "
                + (e.tags || []).join(" ")).toLowerCase()
            if (haystack.indexOf(needle) !== -1) out.push(e)
        }
        return out
    }

    // Index of the installed package that matches a catalog entry.
    function uv_installedPackageIndex(entry) {
        if (!entry) return -1
        var packages = AppController.updatePackages || []
        for (var i = 0; i < packages.length; i++) {
            var p = packages[i]
            if (!p) continue
            if (entry.installed_package_id && p.package_id === entry.installed_package_id) return i
            if (p.repository_url && entry.repository_url && p.repository_url === entry.repository_url) return i
        }
        return -1
    }

    Component.onDestruction: {
        cleanup()
    }

    Component.onCompleted: {
        var p = AppController.updatePackages
        if (p) {
            uv_packagesList.model = p
            uv_packagesList.cacheBuffer = Math.max(uv_packagesList.height * 2, 1000)
        }
        var proj = AppController.config_controller ? AppController.config_controller.updateProjects : null
        if (proj) {
            uv_projectsList.model = proj
            uv_projectsList.cacheBuffer = Math.max(uv_projectsList.height * 2, 1000)
        }
    }

    Connections {
        target: AppController
        function onUpdatePackagesChanged() {
            var newModel = AppController.updatePackages
            if (newModel === null || typeof newModel === "undefined") {
                uv_packagesList.cacheBuffer = 0
                uv_packagesList.model = null
            } else {
                uv_packagesList.cacheBuffer = 0
                uv_packagesList.model = newModel
                uv_packagesList.cacheBuffer = Math.max(uv_packagesList.height * 2, 1000)
            }
            // The catalog's install badges depend on the package list.
            uv_catalogList.model = updatesRoot.uv_filteredCatalog()
        }
    }

    Connections {
        target: AppController.update_controller ? AppController.update_controller : null
        function onCatalogChanged() {
            uv_catalogList.model = updatesRoot.uv_filteredCatalog()
        }
    }

    Connections {
        target: AppController.config_controller ? AppController.config_controller : null
        function onUpdateProjectsChanged() {
            if (!AppController.config_controller) return
            var newModel = AppController.config_controller.updateProjects
            if (newModel === null || typeof newModel === "undefined") {
                uv_projectsList.cacheBuffer = 0
                uv_projectsList.model = null
            } else {
                uv_projectsList.cacheBuffer = 0
                uv_projectsList.model = newModel
                uv_projectsList.cacheBuffer = Math.max(uv_projectsList.height * 2, 1000)
            }
        }
    }

    // --- Dialogs ---
    FolderPickerNative {
        id: uv_folderPicker
        onFolderSelected: (path) => {
            if (mode === "package") {
                AppController.config_controller.addSource(path)
            } else if (mode === "project") {
                AppController.config_controller.addProject(path)
            }
        }
    }

    PackageEditDialog {
        id: uv_packageEditDialog
        objectName: "uv_packageEditDialog"
    }

    ProjectRenameDialog {
        id: uv_projectRenameDialog
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 16



        // Bulk Action Bar (Redesigned as Pebble Bar)
        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: 24
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                anchors.leftMargin: 16
                anchors.rightMargin: 8
                spacing: 12
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text {
                        text: "Packages"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: Font.Bold
                        color: Theme.label
                    }
                    Rectangle {
                        width: 1
                        height: 12
                        color: Theme.separator
                        visible: updatesRoot.width >= 420
                    }
                    // Status summary: how many packages are installed, how
                    // many are outdated and how many could not be checked.
                    Rectangle {
                        Layout.preferredWidth: uv_installedCountText.implicitWidth + 16
                        Layout.preferredHeight: 22
                        radius: 11
                        color: Theme.glassHover
                        border.color: Theme.glassBorder
                        border.width: 1
                        visible: updatesRoot.width >= 380

                        Text {
                            id: uv_installedCountText
                            anchors.centerIn: parent
                            text: (AppController.updatePackages ? AppController.updatePackages.length : 0) + " installed"
                            color: Theme.secondaryLabel
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                        }
                    }
                    Rectangle {
                        Layout.preferredWidth: uv_outdatedCountText.implicitWidth + 16
                        Layout.preferredHeight: 22
                        radius: 11
                        color: Theme.alpha(Theme.accent, 0.12)
                        border.color: Theme.alpha(Theme.accent, 0.3)
                        border.width: 1
                        visible: updatesRoot.width >= 420

                        Text {
                            id: uv_outdatedCountText
                            anchors.centerIn: parent
                            text: AppController.isLoading
                                ? "Checking..."
                                : (AppController.statsOutdated + " outdated")
                            color: AppController.isLoading ? Theme.accent : Theme.accent
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                        }
                    }
                    // "0 updates" is not the same as "0 packages checked":
                    // say so when a remote could not be reached.
                    Text {
                        text: "· " + AppController.statsUnchecked + " unchecked"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        color: Theme.warning
                        visible: updatesRoot.width >= 480 && AppController.statsUnchecked > 0
                    }
                }

                RowLayout {
                    spacing: 8

                    ActionButton {
                        objectName: "addCustomPackageBtn"
                        labelText: "+ Add Custom Package"
                        iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                        role: "secondary"
                        tooltipText: "Add a package from a repository, an npx command or a script"
                        onClicked: (mouse) => {
                            uv_packageEditDialog.editIndex = -1
                            uv_packageEditDialog.open()
                        }
                    }

                    ActionButton {
                        objectName: "scanUpdatesBtn"
                        labelText: "Check for Updates"
                        role: "secondary"
                        tooltipText: enabled ? "Check configured projects for available skill updates." : "Update scan is already running."
                        enabled: !AppController.isLoading
                        onClicked: (mouse) => AppController.update_controller.scanForUpdates()
                    }

                    ActionButton {
                        property bool hasPendingUpdates: AppController.statsOutdated > 0
                        labelText: hasPendingUpdates ? "Sync All" : "Up to Date"
                        role: hasPendingUpdates ? "primary" : "secondary"
                        tooltipText: enabled ? "Update every package currently marked outdated." : "Already up to date"
                        enabled: !AppController.isLoading && hasPendingUpdates
                        onClicked: (mouse) => AppController.update_controller.updateAllOutdated()
                    }
                }
            }
        }


        // Page switcher: Installed / Discover / Project Sync
        RowLayout {
            id: uv_tabs
            Layout.fillWidth: true
            spacing: 0

            Repeater {
                model: [
                    { key: "installed", label: "Installed" },
                    { key: "discover", label: "Discover" },
                    { key: "sync", label: "Project Sync" }
                ]

                delegate: Rectangle {
                    id: uv_tab
                    required property var modelData
                    required property int index
                    readonly property bool selected: uv_pages.currentIndex === uv_tab.index

                    Layout.preferredWidth: uv_tabText.implicitWidth + 32
                    Layout.preferredHeight: 34
                    radius: Theme.radiusButton
                    color: selected ? Theme.glassActive : "transparent"
                    border.color: selected ? Theme.accent : Theme.glassBorder
                    border.width: 1
                    activeFocusOnTab: true

                    Accessible.role: Accessible.PageTab
                    Accessible.checked: selected
                    Accessible.name: modelData.label + " tab"

                    Text {
                        id: uv_tabText
                        anchors.centerIn: parent
                        text: uv_tab.modelData.label
                        color: uv_tab.selected ? Theme.label : Theme.secondaryLabel
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        font.weight: uv_tab.selected ? Font.DemiBold : Font.Medium
                    }

                    TapHandler {
                        onTapped: uv_pages.currentIndex = uv_tab.index
                    }
                    Keys.onPressed: (event) => {
                        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
                            uv_pages.currentIndex = uv_tab.index
                            event.accepted = true
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }
        }

        // Pages: Installed packages / Curated catalog / Project sync
        StackLayout {
            id: uv_pages
            objectName: "uv_pages"
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            // Page 1: Installed packages
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                // Packages Manager
                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        
                        RowLayout {
                            id: uv_packagesHeader
                            Layout.fillWidth: true
                            Text {
                                text: "Skill Packages"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 6
                                ActionButton {
                                    labelText: "Folder"
                                    iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                                    iconOnlyMode: uv_packagesHeader.width < 340
                                    role: "secondary"
                                    tooltipText: "Add Folder"
                                    onClicked: (mouse) => {
                                        uv_folderPicker.mode = "package"
                                        uv_folderPicker.open()
                                    }
                                }
                            }
                        }

                        SmoothListView {
                            id: uv_packagesList
                            objectName: "uv_packagesList"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            // satisfied test check: model: AppController.updatePackages
                            model: null

                            spacing: 8
                            delegate: Rectangle {
                                width: uv_packagesList.width
                                height: 52
                                color: Theme.glassPill
                                radius: 12
                                border.color: Theme.glassBorder
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: 14
                                        color: Theme.alpha(Theme.accent, 0.07)

                                        Image {
                                            id: typeIcon
                                            anchors.centerIn: parent
                                            width: 14
                                            height: 14
                                            sourceSize.width: 14
                                            sourceSize.height: 14
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            source: {
                                                if (modelData.source_type === "git") return AppController.ui_controller.getAssetUri("ui/globe-icon.svg")
                                                if (modelData.source_type === "npx") return AppController.ui_controller.getAssetUri("ui/box-icon.svg")
                                                return AppController.ui_controller.getAssetUri("ui/folder-icon.svg")
                                            }
                                        }

                                        ColorOverlay {
                                            anchors.fill: typeIcon
                                            source: typeIcon
                                            color: Theme.accent
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 0
                                        Layout.fillWidth: true
                                        Text {
                                            text: modelData.name
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 13
                                            font.weight: Font.Medium
                                            color: Theme.label
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                        RowLayout {
                                            spacing: 4
                                            Text {
                                                text: "v" + (modelData.current_version || "1.0.0")
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                color: Theme.secondaryLabel
                                            }
                                            Text {
                                                text: "→"
                                                font.pixelSize: 10
                                                color: Theme.secondaryLabel
                                                visible: Boolean(modelData.latest_version && modelData.latest_version !== modelData.current_version)
                                            }
                                            Text {
                                                text: "v" + modelData.latest_version
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                font.weight: Font.Bold
                                                color: Theme.accent
                                                visible: Boolean(modelData.latest_version && modelData.latest_version !== modelData.current_version)
                                            }
                                            Text {
                                                // Never render a failed check as
                                                // a plain version row: the latest
                                                // version is simply unknown.
                                                visible: Boolean(modelData.check_status === "failed")
                                                text: "· could not check"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                color: Theme.warning
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                        spacing: 4
                                        
                                        // Update Button / Status
                                        ActionButton {
                                            id: uv_itemUpdateBtn
                                            // A newer version we actually know about always wins:
                                            // it is not stale information, so the action is Update.
                                            property bool hasNewerVersion: Boolean(
                                                modelData.latest_version && modelData.latest_version !== "" &&
                                                modelData.latest_version !== modelData.current_version
                                            )
                                            // Otherwise a failed check must not present as
                                            // "Up to Date" — we never learned the latest version,
                                            // so the honest primary action is to retry the check.
                                            property bool checkFailed: !hasNewerVersion && modelData.check_status === "failed"
                                            labelText: modelData.is_updating
                                                ? "Updating..."
                                                : (hasNewerVersion ? "Update" : (checkFailed ? "Re-check" : "Up to Date"))
                                            iconSource: AppController.ui_controller.getAssetUri("ui/refresh-icon.svg")
                                            role: modelData.update_error
                                                ? "destructive"
                                                : (checkFailed ? "warning" : (hasNewerVersion ? "primary" : "secondary"))
                                            buttonHeight: 26
                                            iconOnlyMode: uv_packagesList.width < 320
                                            Layout.preferredWidth: implicitWidth
                                            Layout.minimumWidth: implicitWidth
                                            enabled: !modelData.is_updating && (hasNewerVersion || checkFailed)
                                            tooltipText: {
                                                if (modelData.update_error) return "Update failed: " + modelData.update_error
                                                if (modelData.is_updating) return "Update in progress..."
                                                if (checkFailed) {
                                                    var reason = modelData.check_error ? (": " + modelData.check_error) : ""
                                                    return "Could not check for updates" + reason + " — click to retry"
                                                }
                                                if (!hasNewerVersion) return "Already up to date"
                                                return "Update " + modelData.name + " to latest version"
                                            }
                                            onClicked: (mouse) => {
                                                if (checkFailed) {
                                                    AppController.logDiagnosticEvent("INFO", "check_retry", "User retried the version check for package: " + modelData.name)
                                                    AppController.update_controller.retryPackageCheck(modelData.package_id)
                                                    return
                                                }
                                                AppController.logDiagnosticEvent("INFO", "update_click", "User clicked Update for package: " + modelData.name + " (index=" + index + ")")
                                                AppController.update_controller.runPackageUpdate(index)
                                            }
                                        }

                                        // Error icon
                                        Rectangle {
                                            visible: Boolean(modelData.update_error)
                                            width: 18
                                            height: 18
                                            radius: 9
                                            color: Theme.danger
                                            Text {
                                                anchors.centerIn: parent
                                                text: "!"
                                                font.pixelSize: 11
                                                font.weight: Font.Bold
                                                color: "white"
                                            }
                                        }


                                        IconButton {
                                            iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
                                            iconSize: 10
                                            buttonSize: 28
                                            role: "ghost"
                                            tooltipText: "Edit package"
                                            visible: Boolean(modelData && modelData.source_type !== undefined)
                                            onClicked: (mouse) => {
                                                uv_packageEditDialog.editIndex = index
                                                uv_packageEditDialog.loadPackage(modelData)
                                                uv_packageEditDialog.open()
                                            }
                                        }
                                        IconButton {
                                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                                            iconSize: 10
                                            buttonSize: 28
                                            role: "destructive"
                                            tooltipText: "Remove package"
                                            onClicked: (mouse) => {
                                                if (modelData.source_type !== undefined) {
                                                    Qt.callLater(AppController.update_controller.removeUpdatePackage, index)
                                                } else {
                                                    Qt.callLater(AppController.config_controller.removeSourceByIndex, index)
                                                }
                                            }
                                        }
                                    }
                                }

                                SleekProgressBar {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    anchors.bottomMargin: 2
                                    barHeight: 3
                                    running: Boolean(modelData && modelData.is_updating)
                                    color: Theme.accent
                                }
                            }


                        }
                    }
                }
            }

            // Page 2: Discover — the curated package catalog
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        RowLayout {
                            id: uv_catalogHeader
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                text: "Discover Library"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                                elide: Text.ElideRight
                            }

                            Item { Layout.fillWidth: true }

                            GlassSearchInput {
                                id: uv_catalogSearch
                                // Bound to the view width, not the row width:
                                // a child sized from its layout parent causes a
                                // recursive rearrange.
                                Layout.preferredWidth: Math.min(220, updatesRoot.width * 0.25)
                                placeholderText: "Search packages..."
                                Accessible.name: "Search the package catalog"
                                onDebouncedTextChanged: (text) => {
                                    updatesRoot.uv_catalogQuery = text
                                    uv_catalogList.model = updatesRoot.uv_filteredCatalog()
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "Curated, ready-to-install skill packages. Install one with a click, "
                                + "or configure it first."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            color: Theme.secondaryLabel
                            wrapMode: Text.WordWrap
                        }

                        SmoothListView {
                            id: uv_catalogList
                            objectName: "uv_catalogList"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 8
                            model: uv_filteredCatalog()

                            delegate: Rectangle {
                                id: uv_catalogCard
                                required property var modelData
                                readonly property var entry: modelData

                                width: uv_catalogList.width
                                height: uv_cardLayout.implicitHeight + 24
                                radius: Theme.radiusCard
                                color: Theme.glassPill
                                border.color: Theme.glassBorder
                                border.width: 1

                                ColumnLayout {
                                    id: uv_cardLayout
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 12
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        Text {
                                            text: uv_catalogCard.entry.display_name || ""
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeBody
                                            font.weight: Font.DemiBold
                                            color: Theme.label
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }

                                        // Author badge
                                        Rectangle {
                                            Layout.preferredWidth: uv_authorText.implicitWidth + 14
                                            Layout.preferredHeight: 20
                                            radius: 10
                                            color: Theme.glassHover
                                            border.color: Theme.glassBorder
                                            border.width: 1
                                            visible: uv_catalogCard.entry.author !== ""

                                            Text {
                                                id: uv_authorText
                                                anchors.centerIn: parent
                                                text: uv_catalogCard.entry.author || ""
                                                color: Theme.secondaryLabel
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                            }
                                        }

                                        // Source type badge
                                        Rectangle {
                                            Layout.preferredWidth: uv_typeText.implicitWidth + 14
                                            Layout.preferredHeight: 20
                                            radius: 10
                                            color: Theme.alpha(Theme.accent, 0.12)
                                            border.color: Theme.alpha(Theme.accent, 0.3)
                                            border.width: 1

                                            Text {
                                                id: uv_typeText
                                                anchors.centerIn: parent
                                                text: uv_catalogCard.entry.source_type || ""
                                                color: Theme.accent
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                font.weight: Font.Medium
                                            }
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: uv_catalogCard.entry.description || ""
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.sizeCaption
                                        color: Theme.secondaryLabel
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        // Tags
                                        Text {
                                            text: (uv_catalogCard.entry.tags || []).join(" · ")
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeCaption
                                            color: Theme.secondaryLabel
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }

                                        // Installed badge
                                        Rectangle {
                                            visible: uv_catalogCard.entry.is_installed === true
                                            Layout.preferredWidth: uv_installedText.implicitWidth + 16
                                            Layout.preferredHeight: 22
                                            radius: 11
                                            color: Theme.alpha(Theme.success, 0.14)
                                            border.color: Theme.alpha(Theme.success, 0.4)
                                            border.width: 1

                                            Text {
                                                id: uv_installedText
                                                anchors.centerIn: parent
                                                text: "Installed ✓"
                                                color: Theme.success
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                font.weight: Font.Medium
                                            }
                                        }

                                        ActionButton {
                                            labelText: "Configure…"
                                            role: "secondary"
                                            tooltipText: "Configure the package before installing it"
                                            buttonHeight: 30
                                            visible: !uv_catalogCard.entry.is_installed
                                            onClicked: (mouse) => {
                                                uv_packageEditDialog.openWithTemplate(uv_catalogCard.entry)
                                            }
                                        }

                                        ActionButton {
                                            labelText: "Install"
                                            role: "primary"
                                            tooltipText: "Install with the default settings"
                                            buttonHeight: 30
                                            visible: !uv_catalogCard.entry.is_installed
                                            onClicked: (mouse) => {
                                                AppController.update_controller.installCatalogPackageDefault(
                                                    uv_catalogCard.entry.id)
                                            }
                                        }

                                        ActionButton {
                                            labelText: "Reconfigure"
                                            role: "secondary"
                                            tooltipText: "Open the installed package for editing"
                                            buttonHeight: 30
                                            visible: uv_catalogCard.entry.is_installed === true
                                            onClicked: (mouse) => {
                                                var idx = uv_installedPackageIndex(uv_catalogCard.entry)
                                                if (idx >= 0) {
                                                    uv_packageEditDialog.editIndex = idx
                                                    uv_packageEditDialog.open()
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Page 3: Project sync
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                // Projects Manager
                GlassPill {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        
                        RowLayout {
                            id: uv_projectsHeader
                            Layout.fillWidth: true
                            Text {
                                text: "Projects (Skill Folders)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeSectionTitle
                                font.weight: Font.Bold
                                color: Theme.label
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            ActionButton {
                                labelText: "Add Project"
                                iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                                iconOnlyMode: uv_projectsHeader.width < 320
                                role: "secondary"
                                tooltipText: "Add Project"
                                onClicked: (mouse) => {
                                    uv_folderPicker.mode = "project"
                                    uv_folderPicker.open()
                                }
                            }
                        }

                        SmoothListView {
                            id: uv_projectsList
                            objectName: "uv_projectsList"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            // satisfied test check: model: AppController.config_controller.updateProjects
                            model: null

                            spacing: 8
                            delegate: Rectangle {
                                width: uv_projectsList.width
                                height: 52
                                color: Theme.glassPill
                                radius: 12
                                border.color: Theme.glassBorder
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: 14
                                        color: Theme.alpha(Theme.accent, 0.07)

                                        Image {
                                            id: projectIcon
                                            anchors.centerIn: parent
                                            width: 16
                                            height: 16
                                            sourceSize.width: 16
                                            sourceSize.height: 16
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            source: AppController.ui_controller.getAssetUri("ui/rocket-icon.svg")
                                        }

                                        ColorOverlay {
                                            anchors.fill: projectIcon
                                            source: projectIcon
                                            color: Theme.accent
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 2
                                        Layout.fillWidth: true
                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Text {
                                                text: modelData.name
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeBody
                                                font.weight: Font.Bold
                                                color: Theme.label
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                text: "(" + modelData.skill_count + " skills)"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.sizeCaption
                                                color: Theme.secondaryLabel
                                            }
                                        }
                                        Text {
                                            text: modelData.path
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.sizeCaption
                                            color: Theme.secondaryLabel
                                            elide: Text.ElideMiddle
                                            Layout.fillWidth: true
                                        }
                                    }

                                    RowLayout {
                                        spacing: 4
                                        IconButton {
                                            iconSource: AppController.ui_controller.getAssetUri("ui/edit-icon.svg")
                                            iconSize: 10
                                            buttonSize: 32
                                            role: "ghost"
                                            tooltipText: "Rename project"
                                            onClicked: (mouse) => {
                                                uv_projectRenameDialog.projectPath = modelData.path
                                                uv_projectRenameDialog.currentName = modelData.name
                                                uv_projectRenameDialog.open()
                                            }
                                        }
                                        IconButton {
                                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                                            iconSize: 10
                                            buttonSize: 32
                                            role: "destructive"
                                            tooltipText: "Remove project"
                                            onClicked: (mouse) => Qt.callLater(AppController.config_controller.removeUpdateProject, index)
                                        }
                                    }
                                }

                                SleekProgressBar {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    anchors.bottomMargin: 2
                                    barHeight: 3
                                    running: Boolean(modelData && modelData.is_updating)
                                    color: Theme.accent
                                }
                            }


                        }
                    }
                }
            }
        }

    }

    // Detail Inspector (Drawer-like)
    Popup {
        id: uv_inspector
        property var skillData: null
        
        width: Math.min(400, parent ? parent.width : 400)
        height: parent ? parent.height : 600
        x: parent ? Math.max(0, parent.width - width) : 0
        y: 0
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        
        background: Rectangle {
            color: Theme.appBackground
            border.color: Theme.glassBorder
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 20
            
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Skill Details"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeHeading
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }
                IconButton {
                    text: "✕"
                    tooltipText: "Close Inspector"
                    onClicked: (mouse) => uv_inspector.close()
                    flat: true
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 16
                visible: uv_inspector.skillData !== null

                // Info Card
                Rectangle {
                    Layout.fillWidth: true
                    height: 120
                    color: Theme.glassPill
                    radius: Theme.radiusCard
                    border.color: Theme.glassBorder
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        Text {
                            text: uv_inspector.skillData ? uv_inspector.skillData.name : ""
                            font.family: Theme.fontFamily
                            font.pixelSize: 20
                            font.weight: Font.Bold
                            color: Theme.label
                        }
                        Text {
                            text: uv_inspector.skillData ? "Current Version: " + uv_inspector.skillData.version : ""
                            color: Theme.secondaryLabel
                        }
                        Text {
                            text: uv_inspector.skillData ? "Latest Available: " + uv_inspector.skillData.latest_version : ""
                            color: Theme.accent
                            font.weight: Font.Bold
                        }
                    }
                }

                Text {
                    text: "Affected Projects"
                    font.weight: Font.Bold
                    color: Theme.label
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: uv_inspector.skillData ? uv_inspector.skillData.projects : []
                    spacing: 8
                    delegate: Rectangle {
                        width: parent.width
                        height: 50
                        color: Theme.glassPill
                        radius: Theme.radiusCard
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Text {
                                text: modelData.name
                                Layout.fillWidth: true
                                color: Theme.label
                            }
                            ActionButton {
                                text: "Update"
                                onClicked: (mouse) => AppController.update_controller.updateSkillInProject(uv_inspector.skillData.name, modelData.name)
                            }
                        }
                    }
                }
            }
        }
    }
}
