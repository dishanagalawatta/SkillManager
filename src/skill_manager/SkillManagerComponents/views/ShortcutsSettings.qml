import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

ScrollView {
    id: root
    contentWidth: width - leftPadding - rightPadding
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 20

        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: shortcutsLayout.implicitHeight + 32
            radius: Theme.radiusCard

            ColumnLayout {
                id: shortcutsLayout
                anchors.fill: parent
                anchors.margins: 16
                spacing: 20

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: "Keyboard Shortcuts"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeSectionTitle
                        font.weight: Font.Bold
                        color: Theme.label
                        Layout.fillWidth: true
                    }

                    ActionButton {
                        Layout.preferredHeight: 36
                        text: "Reset to Defaults"
                        onClicked: (mouse) => AppController.config_controller.resetShortcuts()
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

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.separator
                }

                GridLayout {
                    columns: 3
                    rowSpacing: 12
                    columnSpacing: 16
                    Layout.fillWidth: true

                    // Column headers
                    Text { text: "Action"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeCaption; font.weight: Font.Bold; color: Theme.label }
                    Text { text: "Shortcut"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeCaption; font.weight: Font.Bold; color: Theme.label }
                    Text { text: "On"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeCaption; font.weight: Font.Bold; color: Theme.label; Layout.alignment: Qt.AlignHCenter }

                    // Search
                    Text { text: "Search"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutSearchEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutSearch; enabled: AppController.config_controller.shortcutSearchEnabled; opacity: AppController.config_controller.shortcutSearchEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("search", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutSearchEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("search", checked) }

                    // Copy
                    Text { text: "Copy"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutCopyEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutCopy; enabled: AppController.config_controller.shortcutCopyEnabled; opacity: AppController.config_controller.shortcutCopyEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("copy", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutCopyEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("copy", checked) }

                    // Archive
                    Text { text: "Archive"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutArchiveEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutArchive; enabled: AppController.config_controller.shortcutArchiveEnabled; opacity: AppController.config_controller.shortcutArchiveEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("archive", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutArchiveEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("archive", checked) }

                    // Delete
                    Text { text: "Delete"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutDeleteEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutDelete; enabled: AppController.config_controller.shortcutDeleteEnabled; opacity: AppController.config_controller.shortcutDeleteEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("delete", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutDeleteEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("delete", checked) }

                    // Refresh
                    Text { text: "Refresh Library"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutRefreshEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutRefresh; enabled: AppController.config_controller.shortcutRefreshEnabled; opacity: AppController.config_controller.shortcutRefreshEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("refresh", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutRefreshEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("refresh", checked) }

                    // Expand All
                    Text { text: "Expand All Categories"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutExpandAllEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutExpandAll; enabled: AppController.config_controller.shortcutExpandAllEnabled; opacity: AppController.config_controller.shortcutExpandAllEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("expand_all", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutExpandAllEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("expand_all", checked) }

                    // Collapse All
                    Text { text: "Collapse All Categories"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutCollapseAllEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutCollapseAll; enabled: AppController.config_controller.shortcutCollapseAllEnabled; opacity: AppController.config_controller.shortcutCollapseAllEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("collapse_all", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutCollapseAllEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("collapse_all", checked) }

                    // Top of List
                    Text { text: "Scroll to Top"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutTopOfListEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutTopOfList; enabled: AppController.config_controller.shortcutTopOfListEnabled; opacity: AppController.config_controller.shortcutTopOfListEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("top_of_list", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutTopOfListEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("top_of_list", checked) }

                    // Clear Selection
                    Text { text: "Clear Selection"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutClearSelectionEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutClearSelection; enabled: AppController.config_controller.shortcutClearSelectionEnabled; opacity: AppController.config_controller.shortcutClearSelectionEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("clear_selection", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutClearSelectionEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("clear_selection", checked) }

                    // Theme Toggle
                    Text { text: "Toggle Theme"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutThemeToggleEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutThemeToggle; enabled: AppController.config_controller.shortcutThemeToggleEnabled; opacity: AppController.config_controller.shortcutThemeToggleEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("theme_toggle", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutThemeToggleEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("theme_toggle", checked) }

                    // Quick Copy View
                    Text { text: "Quick Copy View"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutQuickCopyViewEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutQuickCopyView; enabled: AppController.config_controller.shortcutQuickCopyViewEnabled; opacity: AppController.config_controller.shortcutQuickCopyViewEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("quick_copy_view", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutQuickCopyViewEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("quick_copy_view", checked) }

                    // Library View
                    Text { text: "Library View"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutLibraryViewEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutLibraryView; enabled: AppController.config_controller.shortcutLibraryViewEnabled; opacity: AppController.config_controller.shortcutLibraryViewEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("library_view", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutLibraryViewEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("library_view", checked) }

                    // Updates View
                    Text { text: "Updates View"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutUpdatesViewEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutUpdatesView; enabled: AppController.config_controller.shortcutUpdatesViewEnabled; opacity: AppController.config_controller.shortcutUpdatesViewEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("updates_view", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutUpdatesViewEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("updates_view", checked) }

                    // Settings View
                    Text { text: "Settings View"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutSettingsViewEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutSettingsView; enabled: AppController.config_controller.shortcutSettingsViewEnabled; opacity: AppController.config_controller.shortcutSettingsViewEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("settings_view", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutSettingsViewEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("settings_view", checked) }

                    // Screenshot
                    Text { text: "Screenshot"; font.family: Theme.fontFamily; color: Theme.label; opacity: AppController.config_controller.shortcutScreenshotEnabled ? 1.0 : 0.5 }
                    KeySequenceCapture { sequence: AppController.config_controller.shortcutScreenshot; enabled: AppController.config_controller.shortcutScreenshotEnabled; opacity: AppController.config_controller.shortcutScreenshotEnabled ? 1.0 : 0.4; onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("screenshot", seq) }
                    GlassSwitch { checked: AppController.config_controller.shortcutScreenshotEnabled; onCheckedChanged: AppController.config_controller.setShortcutEnabled("screenshot", checked) }
                }


            }
        }

        // Collection Shortcuts
        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: collShortcutsLayout.implicitHeight + 32
            radius: Theme.radiusCard

            ColumnLayout {
                id: collShortcutsLayout
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "Collection Shortcuts"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeSectionTitle
                    font.weight: Font.Bold
                    color: Theme.label
                    Layout.fillWidth: true
                }

                Text {
                    text: "Bind a shortcut to instantly copy a collection's skills and paste into the focused field."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                    color: Theme.secondaryLabel
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.separator
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        Text { text: "Collection"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeCaption; font.weight: Font.Bold; color: Theme.label; Layout.preferredWidth: 160 }
                        Text { text: "Shortcut"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeCaption; font.weight: Font.Bold; color: Theme.label; Layout.fillWidth: true }
                        Text { text: "On"; font.family: Theme.fontFamily; font.pixelSize: Theme.sizeCaption; font.weight: Font.Bold; color: Theme.label; Layout.preferredWidth: 44; horizontalAlignment: Text.AlignHCenter }
                    }

                    Repeater {
                        model: AppController.customCollections || []
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 16

                            Text {
                                text: modelData
                                font.family: Theme.fontFamily
                                color: Theme.label
                                Layout.preferredWidth: 160
                                elide: Text.ElideRight
                            }

                            KeySequenceCapture {
                                Layout.fillWidth: true
                                sequence: AppController.config_controller.getCollectionShortcut(modelData)
                                enabled: AppController.config_controller.getCollectionShortcutEnabled(modelData)
                                opacity: AppController.config_controller.getCollectionShortcutEnabled(modelData) ? 1.0 : 0.4
                                onSequenceCaptured: (seq) => AppController.config_controller.setCollectionShortcut(modelData, seq)
                            }

                            GlassSwitch {
                                Layout.preferredWidth: 44
                                checked: AppController.config_controller.getCollectionShortcutEnabled(modelData)
                                onCheckedChanged: AppController.config_controller.setCollectionShortcutEnabled(modelData, checked)
                            }
                        }
                    }

                    // Empty state
                    Text {
                        visible: !AppController.customCollections || AppController.customCollections.length === 0
                        text: "No collections yet. Create one in Quick Copy view."
                        font.family: Theme.fontFamily
                        color: Theme.secondaryLabel
                        font.pixelSize: Theme.sizeCaption
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}
