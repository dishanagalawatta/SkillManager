with open(
    "src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml", encoding="utf-8"
) as f:
    content = f.read()

# 1. Extract qcv_selectionControls contents (we'll rewrite them anyway so we can just delete)
# We know it starts at `RowLayout {\n                        id: qcv_selectionControls`
start_idx = content.find(
    "                    RowLayout {\n                        id: qcv_selectionControls"
)

# It goes until just before `// Edit Collection Mode`
end_idx = content.find("                    // Edit Collection Mode", start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + content[end_idx:]

# 2. Remove one extra closing brace that was balancing the unclosed qcv_selectionControls
# Before `// Filter Group` there are multiple closing braces.
filter_idx = content.find("                    // Filter Group")
brace_idx = content.rfind("                    }", 0, filter_idx)
if brace_idx != -1:
    content = content[:brace_idx] + content[brace_idx + 22 :]  # remove `                    }\n`

# 3. Insert the new buttons into `Filter Group`
# We'll insert them right after `spacing: 12` inside `Filter Group`
insert_target = "                    // Filter Group\n                    RowLayout {\n                        spacing: 12\n"

new_buttons = """                        
                        IconButton {
                            id: qcv_toggleAllBtn
                            buttonSize: 32
                            tooltipText: AppController.quickCopyModel.isAllExpanded ? "Collapse All" : "Expand All"
                            onClicked: (mouse) => AppController.quickCopyModel.toggleAll()
                            contentItem: Image {
                                source: AppController.quickCopyModel.isAllExpanded ?
                                        AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/collapse-arrow-icon-dark.svg" : "ui/collapse-arrow-icon-light.svg") :
                                        AppController.ui_controller.getAssetUri(Theme.darkMode ? "ui/expand-arrow-icon-dark.svg" : "ui/expand-arrow-icon-light.svg")
                                width: 16
                                height: 16
                                sourceSize.width: 16
                                sourceSize.height: 16
                                fillMode: Image.PreserveAspectFit
                                opacity: qcv_toggleAllBtn.hovered ? 1.0 : 0.7
                                horizontalAlignment: Image.AlignHCenter
                                verticalAlignment: Image.AlignVCenter
                            }
                            background: Rectangle {
                                radius: width / 2
                                color: qcv_toggleAllBtn.hovered ? Theme.glassHover : "transparent"
                                border.color: qcv_toggleAllBtn.hovered ? Theme.glassBorder : "transparent"
                                border.width: 1
                            }
                        }

                        GlassCheckBox {
                            id: qcv_selectCheck
                            Layout.preferredWidth: 24
                            Layout.preferredHeight: 24
                            Layout.alignment: Qt.AlignVCenter
                            
                            checkState: {
                                let count = AppController.quickCopyModel.visibleSelectedCount;
                                let total = AppController.quickCopyModel.visibleSelectableCount;
                                if (count === 0) return Qt.Unchecked;
                                if (count >= total && total > 0) return Qt.Checked;
                                return Qt.PartiallyChecked;
                            }

                            onToggled: {
                                if (checkState === Qt.Unchecked) {
                                    AppController.quickCopyModel.selectAll();
                                } else {
                                    AppController.quickCopyModel.clearSelection();
                                }
                            }
                        }

                        RowLayout {
                            id: qcv_infoGroup
                            spacing: 12
                            visible: AppController.quickCopyModel.selectedCount > 0
                            
                            Rectangle {
                                Layout.preferredWidth: Math.max(24, qcvCountText.implicitWidth + 16)
                                Layout.preferredHeight: 24
                                radius: height / 2
                                color: Theme.accent
                                Text {
                                    id: qcvCountText
                                    anchors.centerIn: parent
                                    text: AppController.quickCopyModel.selectedCount.toString()
                                    color: "white"
                                    font.family: Theme.fontFamily
                                    font.weight: Font.Bold
                                    font.pixelSize: 11
                                }
                            }

                            Text {
                                text: AppController.quickCopyModel.selectedCount === 1 ? "Skill selected" : "Skills selected"
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                color: Theme.label
                                font.weight: Font.Medium
                            }
                        }

                        Rectangle {
                            width: 1
                            height: 16
                            color: Theme.separator
                            Layout.leftMargin: 4
                            Layout.rightMargin: 4
                        }

                        IconButton {
                            id: barDeleteBtn
                            buttonSize: 32
                            iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
                            tooltipText: "Delete Selected Skills"
                            role: "destructive"
                            flat: true
                            enabled: AppController.quickCopyModel.selectedCount > 0
                            onClicked: (mouse) => AppController.ops_controller.deleteSelectedSkills()
                        }

                        IconButton {
                            id: barAddCombinedBtn
                            buttonSize: 32
                            iconSource: AppController.ui_controller.getAssetUri("ui/plus-icon.svg")
                            tooltipText: "Add Selected Skills..."
                            enabled: AppController.quickCopyModel.selectedCount > 0
                            onClicked: (mouse) => qcv_addMenu.open(mouse.x, mouse.y + 4)
                        }

                        GlassMenu {
                            id: qcv_addMenu
                            GlassMenuItem {
                                text: "Add to Collection"
                                iconSource: AppController.ui_controller.getAssetUri("ui/collection-icon.svg")
                                onTriggered: {
                                    qcv_root.isEditingCollection = true
                                    qcv_root.editingCollectionName = ""
                                    qcv_root.editingCollectionProjects = []
                                }
                            }
                            GlassMenuItem {
                                text: "Add to Agent Command"
                                iconSource: AppController.ui_controller.getAssetUri("ui/command-icon.svg")
                                onTriggered: {
                                    // Not implemented
                                }
                            }
                        }

"""

content = content.replace(insert_target, insert_target + new_buttons)

with open(
    "src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml", "w", encoding="utf-8"
) as f:
    f.write(content)

print("Modifications done.")
