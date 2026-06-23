import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

ScrollView {
    id: root
    contentWidth: width - leftPadding - rightPadding
    clip: true

    component ShortcutRow: RowLayout {
        id: sr
        property string titleText
        property string actionKey
        property var sequenceBinding
        property bool isEnabledBinding

        Layout.fillWidth: true
        spacing: 16

        Text { 
            text: sr.titleText
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            color: Theme.label
            Layout.fillWidth: true
            opacity: sr.isEnabledBinding ? 1.0 : 0.5
            Behavior on opacity { NumberAnimation { duration: 150 } }
        }

        KeySequenceCapture { 
            Layout.preferredWidth: 160
            Layout.fillWidth: false
            sequence: sr.sequenceBinding
            enabled: sr.isEnabledBinding
            opacity: sr.isEnabledBinding ? 1.0 : 0.4
            Behavior on opacity { NumberAnimation { duration: 150 } }
            onSequenceCaptured: (seq) => {
                if (AppController.config_controller) {
                    AppController.config_controller.setShortcut(sr.actionKey, seq);
                }
            }
        }

        GlassSwitch { 
            Layout.preferredWidth: 44
            checked: sr.isEnabledBinding
            onCheckedChanged: {
                if (AppController.config_controller) {
                    AppController.config_controller.setShortcutEnabled(sr.actionKey, checked);
                }
            }
        }
    }

    component ShortcutGroup: GlassPill {
        id: sg
        property string groupTitle
        default property alias content: innerLayout.data

        Layout.fillWidth: true
        Layout.preferredHeight: contentColumn.implicitHeight + 32
        radius: Theme.radiusCard

        ColumnLayout {
            id: contentColumn
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Text {
                text: sg.groupTitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeSectionTitle
                font.weight: Font.Bold
                color: Theme.label
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.separator
            }

            ColumnLayout {
                id: innerLayout
                Layout.fillWidth: true
                spacing: 12
            }
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
        anchors.margins: 4
        spacing: 24

        // Global Header & Reset Action
        RowLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: -8

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: "Keyboard Shortcuts"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeHeading
                    font.weight: Font.Bold
                    color: Theme.label
                }
                Text {
                    text: "Manage custom key bindings for actions across the app."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    color: Theme.secondaryLabel
                }
            }

            ActionButton {
                Layout.preferredHeight: 36
                text: "Reset to Defaults"
                onClicked: (mouse) => {
                    if (AppController.config_controller) {
                        AppController.config_controller.resetShortcuts();
                    }
                }
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

        // --- Find & Select ---
        ShortcutGroup {
            groupTitle: "Find & Select"

            ShortcutRow {
                titleText: "Search"
                actionKey: "search"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutSearch : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutSearchEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Select All"
                actionKey: "select_all"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutSelectAll : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutSelectAllEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Clear Selection"
                actionKey: "clear_selection"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutClearSelection : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutClearSelectionEnabled : false
            }
        }

        // --- Clipboard ---
        ShortcutGroup {
            groupTitle: "Clipboard"

            ShortcutRow {
                titleText: "Copy"
                actionKey: "copy"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutCopy : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutCopyEnabled : false
            }
        }

        // --- Skill Ops ---
        ShortcutGroup {
            groupTitle: "Skill Ops"

            ShortcutRow {
                titleText: "Refresh Library"
                actionKey: "refresh"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutRefresh : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutRefreshEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Archive"
                actionKey: "archive"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutArchive : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutArchiveEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Delete"
                actionKey: "delete"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutDelete : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutDeleteEnabled : false
            }
        }

        // --- Tree View ---
        ShortcutGroup {
            groupTitle: "Tree View"

            ShortcutRow {
                titleText: "Expand All Categories"
                actionKey: "expand_all"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutExpandAll : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutExpandAllEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Collapse All Categories"
                actionKey: "collapse_all"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutCollapseAll : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutCollapseAllEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Scroll to Top"
                actionKey: "top_of_list"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutTopOfList : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutTopOfListEnabled : false
            }
        }

        // --- Navigate ---
        ShortcutGroup {
            groupTitle: "Navigate"

            ShortcutRow {
                titleText: "Quick Copy View"
                actionKey: "quick_copy_view"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutQuickCopyView : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutQuickCopyViewEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Library View"
                actionKey: "library_view"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutLibraryView : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutLibraryViewEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Updates View"
                actionKey: "updates_view"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutUpdatesView : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutUpdatesViewEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Settings View"
                actionKey: "settings_view"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutSettingsView : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutSettingsViewEnabled : false
            }
        }

        // --- Tools ---
        ShortcutGroup {
            groupTitle: "Tools"

            ShortcutRow {
                titleText: "Toggle Theme"
                actionKey: "theme_toggle"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutThemeToggle : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutThemeToggleEnabled : false
            }
            Separator {}
            ShortcutRow {
                titleText: "Screenshot"
                actionKey: "screenshot"
                sequenceBinding: AppController.config_controller ? AppController.config_controller.shortcutScreenshot : ""
                isEnabledBinding: AppController.config_controller ? AppController.config_controller.shortcutScreenshotEnabled : false
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
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

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
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.separator
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Repeater {
                        model: AppController.customCollections || []
                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                Text {
                                    text: modelData
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.sizeBody
                                    color: Theme.label
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    opacity: AppController.config_controller && AppController.config_controller.getCollectionShortcutEnabled(modelData) ? 1.0 : 0.5
                                    Behavior on opacity { NumberAnimation { duration: 150 } }
                                }

                                KeySequenceCapture {
                                    Layout.preferredWidth: 160
                                    Layout.fillWidth: false
                                    sequence: AppController.config_controller ? AppController.config_controller.getCollectionShortcut(modelData) : ""
                                    enabled: AppController.config_controller ? AppController.config_controller.getCollectionShortcutEnabled(modelData) : false
                                    opacity: AppController.config_controller && AppController.config_controller.getCollectionShortcutEnabled(modelData) ? 1.0 : 0.4
                                    Behavior on opacity { NumberAnimation { duration: 150 } }
                                    onSequenceCaptured: (seq) => {
                                        if (AppController.config_controller) {
                                            AppController.config_controller.setCollectionShortcut(modelData, seq);
                                        }
                                    }
                                }

                                GlassSwitch {
                                    Layout.preferredWidth: 44
                                    checked: AppController.config_controller ? AppController.config_controller.getCollectionShortcutEnabled(modelData) : false
                                    onCheckedChanged: {
                                        if (AppController.config_controller) {
                                            AppController.config_controller.setCollectionShortcutEnabled(modelData, checked);
                                        }
                                    }
                                }
                            }
                            
                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                                opacity: 0.5
                                visible: index !== (AppController.customCollections.length - 1)
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
                        horizontalAlignment: Text.AlignHCenter
                        topPadding: 16
                        bottomPadding: 16
                    }
                }
            }
        }
    }
}
