import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0

ScrollView {
    id: root
    contentWidth: availableWidth
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

                Text {
                    text: "Keyboard Shortcuts"
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

                GridLayout {
                    columns: 2
                    rowSpacing: 15
                    columnSpacing: 20
                    Layout.fillWidth: true

                    // Search
                    Text { text: "Search"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutSearch
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("search", seq)
                    }

                    // Copy
                    Text { text: "Copy Selection"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutCopy
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("copy", seq)
                    }

                    // Archive
                    Text { text: "Archive Selected"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutArchive
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("archive", seq)
                    }

                    // Delete
                    Text { text: "Delete Selected"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutDelete
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("delete", seq)
                    }

                    // Refresh
                    Text { text: "Refresh Library"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutRefresh
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("refresh", seq)
                    }

                    // Expand All
                    Text { text: "Expand All Categories"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutExpandAll
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("expand_all", seq)
                    }

                    // Collapse All
                    Text { text: "Collapse All Categories"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutCollapseAll
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("collapse_all", seq)
                    }

                    // Top of List
                    Text { text: "Scroll to Top"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutTopOfList
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("top_of_list", seq)
                    }

                    // Clear Selection
                    Text { text: "Clear Selection"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutClearSelection
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("clear_selection", seq)
                    }

                    // Theme Toggle
                    Text { text: "Toggle Theme"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutThemeToggle
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("theme_toggle", seq)
                    }

                    // Navigation
                    Text { text: "Quick Copy View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutQuickCopyView
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("quick_copy_view", seq)
                    }

                    Text { text: "Library View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutLibraryView
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("library_view", seq)
                    }

                    Text { text: "Updates View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutUpdatesView
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("updates_view", seq)
                    }

                    Text { text: "Settings View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.config_controller.shortcutSettingsView
                        onSequenceCaptured: (seq) => AppController.config_controller.setShortcut("settings_view", seq)
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.separator
                }

                ActionButton {
                    Layout.alignment: Qt.AlignRight
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
        }
    }
}
