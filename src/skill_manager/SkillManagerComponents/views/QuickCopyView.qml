import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import App 1.0
import SkillManagerComponents 1.0
import ".."
import "../dialogs"

Item {
    id: qcv_root
    
    property bool isEditingCollection: false
    property string editingCollectionName: ""
    property bool _isInternalSelectionChange: false

    Component.onCompleted: {
        // Mode is handled by AppController currentView setter
    }

    // No forced reset on completion - use persistent state

    ColumnLayout {
        anchors.fill: parent
        spacing: 20

        // Header Section
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            ColumnLayout {
                spacing: 4
                RowLayout {
                    spacing: 12
                    Text {
                        text: "Quick Copy"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeHeading
                        font.weight: Font.Bold
                        color: Theme.label
                    }
                    
                    Button {
                        id: addCommandBtn
                        Layout.preferredHeight: 28
                        flat: false
                        onClicked: {
                            qcv_commandDialog.openWithContext(AppController.skillModel.projectFilter, AppController.clientFormat)
                        }
                        contentItem: RowLayout {
                            spacing: 6
                            Text {
                                text: "+"
                                font.pixelSize: 16
                                color: "white"
                                font.weight: Font.Bold
                            }
                            Text {
                                text: "Add Command"
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                color: "white"
                            }
                        }
                        background: Rectangle {
                            radius: Theme.radiusPill
                            color: addCommandBtn.pressed ? Theme.accent : (addCommandBtn.hovered ? Theme.accent + "DD" : Theme.accent)
                        }
                        ToolTip.visible: hovered
                        ToolTip.text: "Create a new custom command for the selected project"
                    }
                }
                Text {
                    text: "Select and copy skills to your clipboard instantly."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.secondaryLabel
                }
            }

            Item { Layout.fillWidth: true }

            Flow {
                id: headerControls
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 12

                // Navigation Actions Group
                RowLayout {
                    spacing: 8
                    Button {
                        text: "Select All"
                        flat: true
                        visible: AppController.skillModel.selectedCount < AppController.skillModel.rowCount()
                        onClicked: AppController.skillModel.selectAll()
                        contentItem: Text {
                            text: parent.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            font.weight: Font.Medium
                            color: Theme.accent
                        }
                    }

                    Button {
                        text: "Clear"
                        flat: true
                        visible: AppController.skillModel.selectedCount > 0
                        onClicked: AppController.skillModel.clearSelection()
                        contentItem: Text {
                            text: parent.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            font.weight: Font.Medium
                            color: Theme.secondaryLabel
                        }
                    }

                    Button {
                        id: expandBtn
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        flat: true
                        onClicked: AppController.skillModel.toggleAll()
                        contentItem: Text {
                            font.pixelSize: 20
                            color: Theme.accent
                            text: AppController.skillModel.isAllExpanded ? "⌃" : "⌄"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.weight: Font.Bold
                        }
                        background: Rectangle {
                            radius: Theme.radiusSmall
                            color: expandBtn.hovered ? Theme.glassPill : "transparent"
                        }
                        ToolTip.visible: hovered
                        ToolTip.text: AppController.skillModel.isAllExpanded ? "Collapse All" : "Expand All"
                    }
                }

                // Filter Group
                RowLayout {
                    spacing: 12
                    
                    GlassCollectionDropdown {
                        id: qcv_collectionDrop
                        Layout.preferredWidth: 160
                        onCollectionSelected: {
                            if (name === "All Collections") {
                                qcv_root._isInternalSelectionChange = true
                                AppController.setViewFilter("collection", "")
                                AppController.skillModel.clearSelection()
                                qcv_root._isInternalSelectionChange = false
                            } else {
                                qcv_root._isInternalSelectionChange = true
                                AppController.applyCollectionSelection(name)
                                AppController.setViewFilter("collection", name)
                                qcv_root._isInternalSelectionChange = false
                            }
                        }
                        onEditCollectionClicked: {
                            qcv_root.isEditingCollection = true
                            qcv_root.editingCollectionName = name
                            qcv_root._isInternalSelectionChange = true
                            AppController.applyCollectionSelection(name)
                            AppController.setViewFilter("collection", name)
                            qcv_root._isInternalSelectionChange = false
                        }

                        Connections {
                            target: AppController.skillModel
                            function onUserSelectionChanged() {
                                if (!qcv_root.isEditingCollection && !qcv_root._isInternalSelectionChange) {
                                    if (qcv_collectionDrop.currentIndex !== 0) {
                                        qcv_collectionDrop.currentIndex = 0
                                    }
                                }
                            }
                        }
                    }

                    GlassDropdown {
                        id: qcv_categoryDrop
                        Layout.preferredWidth: 130
                        model: ["All Categories"].concat(AppController.categories)
                        currentIndex: {
                            let idx = model.indexOf(AppController.skillModel.categoryFilter);
                            return idx === -1 ? 0 : idx;
                        }
                        onActivated: {
                            let cat = currentIndex === 0 ? "" : currentText
                            AppController.setViewFilter("category", cat)
                        }
                    }

                    GlassDropdown {
                        id: qcv_projectDrop
                        Layout.preferredWidth: 150
                        model: ["All Projects"].concat(AppController.projects)
                        currentIndex: {
                            let idx = model.indexOf(AppController.skillModel.projectFilter);
                            return idx === -1 ? 0 : idx;
                        }
                        onActivated: {
                            let proj = currentIndex === 0 ? "" : currentText
                            AppController.setViewFilter("project", proj)
                        }
                    }
                }

                // Client Format Group
                RowLayout {
                    spacing: 8
                    Repeater {
                        model: AppController.clientFormats
                        delegate: Button {
                            id: clientBtn
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 32
                            flat: true
                            property bool isSelected: modelData === AppController.clientFormat
                            onClicked: AppController.setClientFormat(modelData)
                            contentItem: Text {
                                text: {
                                    if (modelData === "Codex") return "🚀"
                                    if (modelData === "Gemini CLI") return "✨"
                                    if (modelData === "Antigravity") return "🛸"
                                    if (modelData === "Plain Path") return "📄"
                                    return "❓"
                                }
                                font.pixelSize: 18
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                opacity: isSelected ? 1.0 : 0.4
                            }
                            background: Rectangle {
                                radius: Theme.radiusField
                                color: isSelected ? Theme.accent + "33" : "transparent"
                                border.color: isSelected ? Theme.accent : "transparent"
                                border.width: 1
                            }
                            ToolTip.visible: hovered
                            ToolTip.text: modelData
                        }
                    }
                }

                // Search Group
                GlassSearchInput {
                    Layout.preferredWidth: 180
                    Layout.fillWidth: false
                    onTextChanged: {
                        AppController.skillModel.filterText = text
                    }
                }
            }
        }

        // Selection Action Bar
        Rectangle {
            id: selectionBar
            Layout.fillWidth: true
            Layout.preferredHeight: (AppController.skillModel.selectedCount > 0 || qcv_root.isEditingCollection) ? qcv_selectionLayout.implicitHeight + 24 : 0
            visible: AppController.skillModel.selectedCount > 0 || qcv_root.isEditingCollection
            color: Theme.accent + "15"
            radius: Theme.radiusCard
            clip: true
            
            Behavior on Layout.preferredHeight {
                NumberAnimation { duration: 200; easing.type: Easing.OutQuad }
            }

            RowLayout {
                id: qcv_selectionLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 16

                RowLayout {
                    id: qcv_infoGroup
                    spacing: 12
                    visible: AppController.skillModel.selectedCount > 0 || !qcv_root.isEditingCollection
                    Rectangle {
                        width: 32
                        height: 32
                        radius: Theme.radiusPill
                        color: Theme.accent
                        Text {
                            anchors.centerIn: parent
                            text: AppController.skillModel.selectedCount
                            color: "white"
                            font.family: Theme.fontFamily
                            font.weight: Font.Bold
                            font.pixelSize: 12
                        }
                    }

                    Text {
                        text: "Skills selected and ready for copy"
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                        color: Theme.label
                        font.weight: Font.Medium
                    }
                }
                
                Item { 
                    Layout.fillWidth: true 
                    visible: qcv_infoGroup.visible
                }
                
                RowLayout {
                    id: qcv_buttonGroup
                    spacing: 12
                    
                    // Normal Mode
                    RowLayout {
                        spacing: 12
                        visible: !qcv_root.isEditingCollection
                        
                        Button {
                            text: "Add to Collection"
                            onClicked: {
                                qcv_root.isEditingCollection = true
                                qcv_root.editingCollectionName = ""
                            }
                            contentItem: Text {
                                text: parent.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                color: Theme.accent
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 140
                                implicitHeight: 36
                                radius: Theme.radiusField
                                color: "transparent"
                                border.color: Theme.accent
                                border.width: 1
                            }
                        }

                        Button {
                            text: "Copy Selected Skills"
                            onClicked: AppController.copySelectedSkillsToClipboard()
                            contentItem: Text {
                                text: parent.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.Bold
                                color: "white"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 140
                                implicitHeight: 36
                                radius: Theme.radiusField
                                color: parent.pressed ? Theme.accent : (parent.hovered ? Theme.accent + "EE" : Theme.accent)
                                
                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: Theme.radiusSmall
                                    color: Theme.accent + "44"
                                    verticalOffset: 2
                                }
                            }
                        }

                        Button {
                            text: "Delete Selected"
                            flat: true
                            onClicked: AppController.deleteSelectedSkills()
                            contentItem: RowLayout {
                                spacing: 4
                                Text {
                                    text: "🗑️"
                                    font.pixelSize: 12
                                }
                                Text {
                                    text: "Delete Selected"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 12
                                    color: "#FF4444"
                                    font.weight: Font.DemiBold
                                }
                            }
                            background: Rectangle {
                                implicitWidth: 120
                                implicitHeight: 36
                                radius: Theme.radiusField
                                color: parent.hovered ? "#22FF4444" : "transparent"
                                border.width: parent.hovered ? 1 : 0
                                border.color: "#33FF4444"
                            }
                        }
                        
                        Button {
                            text: "Clear Selection"
                            flat: true
                            onClicked: AppController.skillModel.clearSelection()
                            contentItem: Text {
                                text: parent.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                color: Theme.secondaryLabel
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }

                    // Edit Collection Mode
                    RowLayout {
                        spacing: 8
                        visible: qcv_root.isEditingCollection

                        TextField {
                            id: qcv_colNameField
                            Layout.preferredWidth: 180
                            placeholderText: "Collection Name"
                            text: qcv_root.editingCollectionName
                            color: Theme.label
                            background: Rectangle {
                                radius: Theme.radiusField
                                color: Theme.glassPill
                                border.color: Theme.glassBorder
                            }
                            onTextChanged: qcv_root.editingCollectionName = text
                        }

                        Button {
                            id: qcv_saveColBtn
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 32
                            flat: true
                            onClicked: {
                                AppController.saveCustomCollection(qcv_root.editingCollectionName, AppController.skillModel.getSelectedPaths())
                                qcv_root.isEditingCollection = false
                                qcv_root.editingCollectionName = ""
                            }
                            contentItem: Text {
                                text: "✔"
                                font.pixelSize: 18
                                color: "green"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            id: qcv_cancelColBtn
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 32
                            flat: true
                            onClicked: {
                                qcv_root.isEditingCollection = false
                                qcv_root.editingCollectionName = ""
                            }
                            contentItem: Text {
                                text: "✖"
                                font.pixelSize: 18
                                color: "red"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }
            }
        }

        // Main Content Area
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Skill List
            ListView {
                id: qcv_skillList
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: AppController.skillModel
                clip: true
                spacing: 2
                
                section.property: "sectionName"
                section.criteria: ViewSection.FullString
                section.delegate: CategoryHeader { 
                    sectionName: section
                    width: qcv_skillList.width
                }
                
                delegate: SkillItem {
                    width: qcv_skillList.width
                    showEssentialIcon: true
                    onClicked: {
                        AppController.skillModel.toggleSelection(index)
                    }
                    onDoubleClicked: {
                        AppController.selectSkill(index)
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }

            // Overlay Inspector
            SkillInspector {
                id: qcv_inspector
                Layout.fillHeight: true
                Layout.preferredWidth: qcv_inspector.targetWidth
                skill: AppController.selectedSkill
                isQuickCopy: true
                visible: qcv_inspector.targetWidth > 0
                
                Behavior on Layout.preferredWidth {
                    NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
                }

                onClosed: AppController.selectSkill(-1)
            }
        }
    }

    // Command Creation Dialog
    CommandCreateDialog {
        id: qcv_commandDialog
    }
}
