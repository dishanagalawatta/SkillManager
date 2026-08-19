import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."          // Theme, glass components
import "../dialogs"  // CommandCreateDialog, etc.
import App 1.0
import ".."

Item {
    id: lv_root
    objectName: "LibraryView"

    // A skill is "valid" when selectedSkill has a real local_path
    readonly property bool selectedSkillValid:
        AppController.selectedSkill
        && AppController.selectedSkill.local_path !== undefined
        && AppController.selectedSkill.local_path !== ""

    // ── Dynamic Collapse Phases (0 = fully expanded) ──────────────
    //   0: All expanded
    //   1: "selected" text → hidden
    //   2: Delete + Add → overflow (⋮ appears where Delete was)
    //   3: Category dropdown → icon-only
    //   4: Project dropdown → icon-only

    // Inspectors: when parent is ≤800px wide, show as centered popup instead of side panel
    readonly property bool _usePopupMode: lv_root.width <= 800
    //   5: Show Archived → overflow
    //   6: Archive → overflow
    //   7: ToggleAll → overflow
    //   8: Category icon → overflow
    //
    // Always visible: selectCheck, count badge, project (icon), tempCopy, copyBtn

    readonly property int _wToggle:      24
    readonly property int _wSelect:      24
    readonly property int _wDelete:      24
    readonly property int _wAdd:         24
    readonly property int _wOverflow:    32
    readonly property int _wDropFull:   140   // category/project full dropdown
    readonly property int _wDropIcon:    36   // category/project icon
    readonly property int _wArchive:     24
    readonly property int _wShowArchived: 24
    readonly property int _wDivider:      9   // 1px + 4+4 margins
    readonly property int _wTempCopy:    24
    readonly property int _wCopy:        24
    readonly property int _wSelectedText: 50

    property int _badgeWidth: {
        if (AppController.libraryModel.selectedCount === 0) return 0
        var str = AppController.libraryModel.selectedCount.toString()
        return Math.max(24, str.length * 10 + 16) + 4
    }

    function _calcLibWidth(phase) {
        var m = 24    // 16 left + 8 right margin
        var os = 12   // outer spacing between LEFT/CENTER/RIGHT
        var ls = 12   // LEFT group inner spacing
        var cs = 8    // CENTER group inner spacing
        var rs = 8    // RIGHT group inner spacing

        var lw = 0, ln = 0  // left group
        var cw = 0, cn = 0  // center group
        var rw = 0, rn = 0  // right group

        // LEFT
        if (phase < 7) { lw += _wToggle; ln++ }
        lw += _wSelect; ln++
        if (AppController.libraryModel.selectedCount > 0) { lw += _badgeWidth; ln++ }
        if (phase < 1 && AppController.libraryModel.selectedCount > 0) { lw += _wSelectedText; ln++ }
        if (phase < 2) { lw += _wDelete; ln++ }
        if (phase < 2) { lw += _wAdd; ln++ }
        if (phase >= 2) { lw += _wOverflow; ln++ }

        // CENTER
        if (phase < 8) {
            cw += (phase < 3) ? _wDropFull : _wDropIcon; cn++
        }
        if (phase < 6) { cw += _wArchive; cn++ }
        if (phase < 5) { cw += _wShowArchived; cn++ }

        // RIGHT
        rw += (phase < 4) ? _wDropFull : _wDropIcon; rn++
        rw += _wDivider; rn++
        rw += _wTempCopy; rn++
        rw += _wCopy; rn++

        // Spacing
        if (ln > 1) lw += (ln - 1) * ls
        if (cn > 1) cw += (cn - 1) * cs
        if (rn > 1) rw += (rn - 1) * rs

        return m + lw + os + cw + os + rw
    }

    property int _libPhase: {
        var avail = lv_root.width - 24  // 16 left + 8 right margins
        // Scan from most-expanded (0) up to most-collapsed (8)
        for (var p = 0; p <= 8; p++) {
            if (_calcLibWidth(p) <= avail) return p
        }
        return 8
    }

    // Full layout chain debug — logs every sizing layer from window down to content
    function dumpLayoutChain() {
        var win = window || (lv_root && lv_root.parent && lv_root.parent.parent && lv_root.parent.parent.parent ? lv_root.parent.parent.parent.parent : null)
        console.log("LAYOUT_CHAIN winW=" + (win ? win.width : -1)
            + " libW=" + lv_root.width
            + " overlayW=" + (lv_inspectorOverlay ? lv_inspectorOverlay.width : -1)
            + " panelW=" + (lv_inspectorOverlay ? lv_inspectorOverlay._panelW : -1)
            + " popupMode=" + lv_root._usePopupMode
            + " phase=" + lv_root._libPhase
            + " loaderW=" + (lv_root.parent ? lv_root.parent.width : -1))
    }

    onWidthChanged: {
        if (lv_root.width > 0) dumpLayoutChain()
    }
    function focusSearch() {
        // Handled globally in TopBar now
    }
    
    function scrollToTop() {
        lv_listView.positionViewAtBeginning()
    }

    function cleanup() {
        lv_listView.cacheBuffer = 0
        lv_listView.model = null
    }
    
    Component.onDestruction: {
        cleanup()
    }
    
    Component.onCompleted: {
        // Mode is handled by AppController currentView setter
        var m = AppController.libraryModel
        if (m) {
            lv_listView.model = m
            if (!m.incubating) {
                lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
            } else {
                lv_listView.cacheBuffer = 0
            }
        }
        Qt.callLater(dumpLayoutChain)
    }

    Connections {
        target: AppController
        function onSkillModelChanged() {
            var newModel = AppController.libraryModel
            if (newModel === null || typeof newModel === "undefined") {
                lv_listView.cacheBuffer = 0
                lv_listView.model = null
            } else {
                lv_listView.cacheBuffer = 0
                lv_listView.model = newModel
                if (!newModel.incubating) {
                    lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                }
            }
        }
    }

    // No forced reset on completion - use persistent state

    ColumnLayout {
        id: lv_mainLayout
        anchors.fill: parent
        spacing: 20

        // Header Section
        RowLayout {
            id: lv_headerRow
            Layout.fillWidth: true
            spacing: 20

            GlassPill {
                Layout.fillWidth: true
                Layout.minimumWidth: 200
                Layout.preferredHeight: 48
                radius: 24

                RowLayout {
                    id: headerControls
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 4
                    anchors.leftMargin: 16
                    anchors.rightMargin: 8
                    spacing: lv_root._libPhase >= 4 ? 6 : 12

                    // ── LEFT GROUP ────────────────────────────────────────
                    RowLayout {
                        spacing: lv_root._libPhase >= 4 ? 6 : 12

                    IconButton {
                        id: lv_toggleAllBtn
                        visible: lv_root._libPhase < 7
                        buttonSize: 24
                        role: "ghost"
                        tooltipText: AppController.libraryModel.isAllExpanded ? "Collapse All" : "Expand All"
                        onClicked: (mouse) => AppController.libraryModel.toggleAll()
                        iconSize: 18
                        iconSource: AppController.libraryModel.isAllExpanded ?
                                AppController.ui_controller.getAssetUri("ui/collapse-arrow-up-broken.svg") :
                                AppController.ui_controller.getAssetUri("ui/collapse-arrow-down-broken.svg")
                        background: Rectangle {
                            radius: 12
                            color: lv_toggleAllBtn.hovered ? Theme.glassHover : "transparent"
                            border.color: Theme.alpha(Theme.label, 0.15)
                            border.width: 1
                        }
                    }

                    GlassCheckBox {
                        id: lv_selectCheck
                        buttonSize: 24
                        Layout.preferredWidth: 24
                        Layout.preferredHeight: 24
                        isClearAction: true

                        checkState: {
                            let count = AppController.libraryModel.visibleSelectedCount;
                            let total = AppController.libraryModel.visibleSelectableCount;
                            if (count === 0) return Qt.Unchecked;
                            if (count >= total && total > 0) return Qt.Checked;
                            return Qt.PartiallyChecked;
                        }

                        onToggled: {
                            if (checkState === Qt.Unchecked) {
                                AppController.libraryModel.selectAll();
                            } else {
                                AppController.libraryModel.clearSelection();
                            }
                        }
                    }

                    // Selection Count
                    RowLayout {
                        spacing: 12
                        visible: AppController.libraryModel.selectedCount > 0

                        Rectangle {
                            Layout.preferredWidth: Math.max(24, libCountText.implicitWidth + 16)
                            Layout.preferredHeight: 24
                            radius: 12
                            color: Theme.glassPill
                            border.color: Theme.glassBorder
                            border.width: 1
                            Text {
                                id: libCountText
                                anchors.centerIn: parent
                                text: AppController.libraryModel.selectedCount.toString()
                                color: Theme.label
                                font.family: Theme.fontFamily
                                font.weight: Font.Bold
                                font.pixelSize: 11
                            }
                        }

                        Text {
                            text: "selected"
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            color: Theme.label
                            font.weight: Font.Medium
                            visible: lv_root._libPhase < 1
                        }
                    }

                    IconButton {
                        id: lv_deleteBtn
                        visible: lv_root._libPhase < 2
                        buttonSize: 24
                        iconSize: 18
                        iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                        tooltipText: "Delete Selected Skills"
                        role: "destructive"
                        flat: true
                        enabled: AppController.libraryModel.selectedCount > 0
                        onClicked: (mouse) => {
                            var selectedPaths = AppController.libraryModel.getSelectedPaths() || []
                            var allProjects = []
                            for (var i = 0; i < selectedPaths.length; i++) {
                                var path = selectedPaths[i]
                                var isCmd = path.endsWith(".md") || path.indexOf("/commands/") >= 0 || path.indexOf("\\commands\\") >= 0
                                var holders = isCmd ? (AppController.commandProjectsForPath(path) || []) : (AppController.skillProjectsForPath(path) || [])
                                for (var j = 0; j < holders.length; j++) {
                                    if (allProjects.indexOf(holders[j]) === -1) allProjects.push(holders[j])
                                }
                            }
                            if (allProjects.length === 0 && AppController.currentProject) {
                                allProjects.push(AppController.currentProject)
                            }
                            lv_inspectorOverlay.cmdDeleteDialog.openBulkSkill(AppController.libraryModel.selectedCount, allProjects, selectedPaths, AppController.libraryModel.getSelectedNames())
                        }
                    }

                    IconButton {
                        id: lv_addCommandBtn
                        visible: lv_root._libPhase < 2
                        buttonSize: 24
                        iconSize: 18
                        iconSource: AppController.ui_controller.getAssetUri("ui/layout-grid-add-icon.svg")
                        tooltipText: "Add Command"
                        onClicked: (mouse) => lv_commandDialog.openWithContext()
                    }

                    // Overflow (replaces Delete position)
                    IconButton {
                        id: lv_overflowBtn
                        visible: lv_root._libPhase >= 2
                        iconText: "⋮"
                        iconSize: 20
                        buttonSize: 28
                        role: "ghost"
                        background: Rectangle {
                            radius: 14
                            color: parent.hovered || parent.down ? Theme.glassHover : "transparent"
                            border.color: Theme.glassBorder
                            border.width: 1
                        }
                        onClicked: lv_overflowMenu.popup(lv_overflowBtn, 0, lv_overflowBtn.height + 4)
                    }
                    }

                    // ── SPACER ────────────────────────────────────────────
                    Item { Layout.fillWidth: true }

                    // ── CENTER GROUP ──────────────────────────────────────
                    RowLayout {
                        spacing: 8

                    GlassDropdown {
                        id: lv_categoryDrop
                        iconOnlyMode: lv_root._libPhase >= 3
                        visible: lv_root._libPhase < 8
                        Layout.minimumWidth: lv_root._libPhase >= 3 ? 36 : 100
                        Layout.maximumWidth: lv_root._libPhase >= 3 ? 36 : 160
                        iconSource: "ui/cosmetic-bold-duotone.svg"
                        model: ["All Categories"].concat(AppController.categories)
                        currentIndex: {
                            let idx = model.indexOf(AppController.libraryModel.categoryFilter);
                            return idx === -1 ? 0 : idx;
                        }
                        onActivated: (index) => {
                            let cat = index === 0 ? "" : currentText
                            AppController.ui_controller.setViewFilterForView("Library", "category", cat)
                        }
                    }

                    IconButton {
                        id: lv_archiveBtn
                        buttonSize: 24
                        iconSize: 18
                        visible: AppController.libraryModel.selectedCount > 0 && lv_root._libPhase < 6
                        iconSource: AppController.ui_controller.getAssetUri("ui/inbox-in-bold-duotone.svg")
                        tooltipText: "Archive"
                        onClicked: (mouse) => lv_archiveConfirmDialog.confirmBulk(AppController.libraryModel.selectedCount, () => AppController.ops_controller.archiveSelectedSkills())
                    }

                    IconButton {
                        id: lv_showArchived
                        buttonSize: 24
                        iconSize: 18
                        visible: lv_root._libPhase < 5
                        iconSource: AppController.libraryModel.showArchived ?
                            AppController.ui_controller.getAssetUri("ui/box-broken.svg") :
                            AppController.ui_controller.getAssetUri("ui/box-bold-duotone.svg")
                        tooltipText: AppController.libraryModel.showArchived ? "Hide Archived" : "Show Archived"
                        onClicked: (mouse) => AppController.libraryModel.showArchived = !AppController.libraryModel.showArchived
                    }
                    }

                    // ── SPACER ────────────────────────────────────────────
                    Item { Layout.fillWidth: true }

                    // ── RIGHT GROUP ───────────────────────────────────────
                    RowLayout {
                        spacing: lv_root._libPhase >= 4 ? 4 : 8
                        Layout.alignment: Qt.AlignRight

                    GlassDropdown {
                        id: lv_projectDrop
                        iconOnlyMode: lv_root._libPhase >= 4
                        Layout.minimumWidth: lv_root._libPhase >= 4 ? 36 : 70
                        Layout.maximumWidth: lv_root._libPhase >= 4 ? 36 : 180
                        iconSource: "ui/folder-security-bold.svg"
                        model: AppController.projectLabels
                        enabled: AppController.projects.length > 0
                        currentIndex: {
                            let idx = model.indexOf(AppController.currentProject);
                            return Math.max(0, idx);
                        }
                        onActivated: (index) => {
                            if (index >= 0 && index < AppController.projectLabels.length) {
                                AppController.setCurrentProject(AppController.projectLabels[index])
                            }
                        }
                    }

                    Rectangle {
                        objectName: "libraryDestructiveDivider"
                        width: 1
                        height: 16
                        color: Theme.separator
                        Layout.leftMargin: 4
                        Layout.rightMargin: 4
                    }

                    IconButton {
                        id: lv_tempCopyBtn
                        buttonSize: 24
                        iconSize: 18
                        role: "secondary"
                        iconSource: AppController.ui_controller.getAssetUri("ui/file-right-broken.svg")
                        enabled: AppController.projects.length > 0
                        tooltipText: enabled ? "Copy Temp" : "Add a project in Updates before copying skills."
                        onClicked: (mouse) => {
                            let path = AppController.config_controller.getProjectPath(AppController.currentProject)
                            if (path) {
                                AppController.ops_controller.copySelectedSkillsToProjectTemporarily(path)
                            }
                        }
                    }

                    IconButton {
                        id: lv_copyBtn
                        buttonSize: 24
                        iconSize: 18
                        role: "primary-outline"
                        iconSource: AppController.ui_controller.getAssetUri("ui/file-right-bold-duotone.svg")
                        enabled: AppController.projects.length > 0
                        tooltipText: enabled ? "Copy to Project" : "Add a project in Updates before copying skills."
                        onClicked: (mouse) => {
                            let path = AppController.config_controller.getProjectPath(AppController.currentProject)
                            if (path) {
                                AppController.ops_controller.copySelectedSkillsToProject(path)
                            }
                        }
                    }
                    }

                    GlassMenu {
                        id: lv_overflowMenu
                        GlassMenuItem {
                            text: "Delete Selected"
                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                            enabled: AppController.libraryModel.selectedCount > 0
                            onTriggered: lv_deleteBtn.clicked()
                        }
                        GlassMenuItem {
                            text: "Add Command"
                            iconSource: AppController.ui_controller.getAssetUri("ui/layout-grid-add-icon.svg")
                            onTriggered: lv_commandDialog.openWithContext()
                        }
                        GlassMenuItem {
                            text: "Show Archived"
                            iconSource: AppController.ui_controller.getAssetUri("ui/box-bold-duotone.svg")
                            onTriggered: { AppController.libraryModel.showArchived = !AppController.libraryModel.showArchived }
                        }
                        GlassMenuItem {
                            text: "Archive"
                            iconSource: AppController.ui_controller.getAssetUri("ui/inbox-in-bold-duotone.svg")
                            enabled: AppController.libraryModel.selectedCount > 0
                            onTriggered: lv_archiveConfirmDialog.confirmBulk(AppController.libraryModel.selectedCount, () => AppController.ops_controller.archiveSelectedSkills())
                        }
                        GlassMenuItem {
                            text: AppController.libraryModel.isAllExpanded ? "Collapse All" : "Expand All"
                            iconSource: AppController.ui_controller.getAssetUri("ui/collapse-arrow-down-broken.svg")
                            onTriggered: AppController.libraryModel.toggleAll()
                        }
                    }
            }
        }
        }

        // Skill List
        SmoothListView {
            id: lv_listView
            objectName: "libraryList"
            Layout.fillWidth: true
            Layout.fillHeight: true
                model: null
                clip: true
                spacing: 0
                
                // Visual Blink: Dips opacity slightly during background refresh to mask micro-jumps
                opacity: (AppController.isLoading && _restoringScroll) ? 0.0 : 1.0
                Behavior on opacity { NumberAnimation { duration: 150 } }

                property real savedScrollPos: 0
                property bool _restoringScroll: false

                function _restoreScroll() {
                    if (AppController.isLoading && savedScrollPos > 0) {
                        _restoringScroll = true
                        
                        // Force immediate layout to ensure contentHeight is valid for restore
                        lv_listView.forceLayout()
                        lv_listView.contentY = savedScrollPos
                        
                        // Second pass: Ensure it stuck (sometimes required for large additions)
                        Qt.callLater(() => {
                            if (lv_listView.contentY !== savedScrollPos) {
                                lv_listView.forceLayout()
                                lv_listView.contentY = savedScrollPos
                            }
                            _restoringScroll = false
                        })
                    }
                }

                Connections {
                    target: AppController.libraryModel
                    function onLayoutAboutToBeChanged() {
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0 // Safely abort active incubators
                    }
                    function onLayoutChanged() {
                        // Defer the restore while the model is still incubating:
                        // the reset fires mid-incubation, so restoring cacheBuffer
                        // here re-triggers a delegate burst that races the in-flight
                        // one ("Object or context destroyed during incubation").
                        // The restore is performed in onIncubatingChanged instead.
                        if (!AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                    function onModelAboutToBeReset() {
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0
                    }
                    function onModelReset() {
                        if (!AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                    function onRowsAboutToBeRemoved() {
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0
                    }
                    function onRowsRemoved() {
                        if (lv_listView.model && !AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                    function onRowsAboutToBeInserted() {
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0
                    }
                    function onRowsInserted() {
                        if (lv_listView.model && !AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                    function onAboutToMutateStructure() {
                        lv_listView.savedScrollPos = lv_listView.contentY
                        lv_listView.cacheBuffer = 0
                    }
                    function onStructureMutated() {
                        if (!AppController.libraryModel.incubating) {
                            lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                            lv_listView._restoreScroll()
                        }
                    }
                }

                // Incubation coordination: when incubating transitions to False,
                // tell the model to replay deferred layout signals.
                Connections {
                    target: AppController.libraryModel
                    function onIncubatingChanged() {
                        if (!AppController.libraryModel.incubating) {
                            AppController.libraryModel.onIncubationReady()
                            // Incubation finished: now safe to re-enable the
                            // off-screen cache buffer without racing live delegates.
                            if (lv_listView.model) {
                                lv_listView.cacheBuffer = Math.max(lv_listView.height * 2, 1000)
                                lv_listView._restoreScroll()
                            }
                        } else {
                            lv_listView.cacheBuffer = 0
                        }
                    }
                }

                section.property: "mainCategoryName"
                section.criteria: ViewSection.FullString
                section.delegate: CategoryHeader {
                    width: lv_listView.width
                    mainCatName: section
                }
                delegate: SkillItem {
                    width: lv_listView.width
                    isSelected: AppController.selectedSkill.local_path === model.path
                    showStarredIcon: false
                    showInlineDelete: false
                    onClicked: (mouse) => {
                        AppController.libraryModel.toggleSelection(index)
                    }
                    onDoubleClicked: (mouse) => {
                        AppController.ui_controller.selectSkill(index)
                    }
                    onRightClicked: {
                        if (AppController.selectedSkill && AppController.selectedSkill.local_path === model.path) {
                            AppController.ui_controller.selectSkill(-1)
                        } else {
                            AppController.ui_controller.selectSkill(index)
                        }
                    }
                    onDeleteRequested: (name, path, isCommand) => {
                        if (isCommand) {
                            var holders = AppController.commandProjectsForPath(path) || []
                            if (holders.length === 0) holders = [AppController.currentProject || ""]
                            lv_inspectorOverlay.cmdDeleteDialog.openForCommand(name, holders)
                        } else {
                            var holders = AppController.skillProjectsForPath(path) || []
                            if (holders.length === 0) holders = [AppController.currentProject || ""]
                            lv_inspectorOverlay.cmdDeleteDialog.openForSkill(name, holders, path)
                        }
                    }
                    onInspectImageRequested: {
                        lv_inspectorOverlay.forceImageInspector()
                    }
                }
            }

    }

    // ── Shared Inspector Overlay ─────────────────────────────────
    SkillInspectorOverlay {
        id: lv_inspectorOverlay
        anchors.fill: parent
        topMargin: lv_headerRow.height + lv_mainLayout.spacing
        usePopupMode: lv_root._usePopupMode
        z: 10
    }

    // Property aliases for test compatibility (forward to overlay).
    readonly property alias showSkillInspector:    lv_inspectorOverlay.showSkillInspector
    readonly property alias showCommandInspector:  lv_inspectorOverlay.showCommandInspector
    readonly property alias showImageInspector:    lv_inspectorOverlay.showImageInspector

    ArchiveConfirmDialog {
        id: lv_archiveConfirmDialog
    }

    CommandCreateDialog {
        id: lv_commandDialog
    }

    CommandCarrySkillsDialog {
        id: lv_carrySkillsDialog
        onCarryConfirmed: (confirmedSkills) => {
            AppController.confirmCommandSkillsCarry(
                lv_carrySkillsDialog.projectPath,
                JSON.stringify(lv_carrySkillsDialog.commandPaths),
                JSON.stringify(confirmedSkills)
            )
        }
    }

    Connections {
        target: AppController
        function onCommandSkillsCarryPrompt(commandPathsJson, projectPath, missingSkillsJson) {
            var cmdPaths = JSON.parse(commandPathsJson || "[]")
            var skills = JSON.parse(missingSkillsJson || "[]")
            lv_carrySkillsDialog.openWithContext(cmdPaths, projectPath, skills)
        }
    }

}

