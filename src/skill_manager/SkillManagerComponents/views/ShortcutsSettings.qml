import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0

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
                        sequence: AppController.shortcutSearch
                        onSequenceCaptured: (seq) => AppController.setShortcut("search", seq)
                    }

                    // Copy
                    Text { text: "Copy Selection"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutCopy
                        onSequenceCaptured: (seq) => AppController.setShortcut("copy", seq)
                    }

                    // Archive
                    Text { text: "Archive Selected"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutArchive
                        onSequenceCaptured: (seq) => AppController.setShortcut("archive", seq)
                    }

                    // Delete
                    Text { text: "Delete Selected"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutDelete
                        onSequenceCaptured: (seq) => AppController.setShortcut("delete", seq)
                    }

                    // Refresh
                    Text { text: "Refresh Library"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutRefresh
                        onSequenceCaptured: (seq) => AppController.setShortcut("refresh", seq)
                    }

                    // Expand All
                    Text { text: "Expand All Categories"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutExpandAll
                        onSequenceCaptured: (seq) => AppController.setShortcut("expand_all", seq)
                    }

                    // Collapse All
                    Text { text: "Collapse All Categories"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutCollapseAll
                        onSequenceCaptured: (seq) => AppController.setShortcut("collapse_all", seq)
                    }

                    // Top of List
                    Text { text: "Scroll to Top"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutTopOfList
                        onSequenceCaptured: (seq) => AppController.setShortcut("top_of_list", seq)
                    }

                    // Clear Selection
                    Text { text: "Clear Selection"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutClearSelection
                        onSequenceCaptured: (seq) => AppController.setShortcut("clear_selection", seq)
                    }

                    // Theme Toggle
                    Text { text: "Toggle Theme"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutThemeToggle
                        onSequenceCaptured: (seq) => AppController.setShortcut("theme_toggle", seq)
                    }

                    // Navigation
                    Text { text: "Quick Copy View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutQuickCopyView
                        onSequenceCaptured: (seq) => AppController.setShortcut("quick_copy_view", seq)
                    }

                    Text { text: "Library View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutLibraryView
                        onSequenceCaptured: (seq) => AppController.setShortcut("library_view", seq)
                    }

                    Text { text: "Updates View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutUpdatesView
                        onSequenceCaptured: (seq) => AppController.setShortcut("updates_view", seq)
                    }

                    Text { text: "Settings View"; font.family: Theme.fontFamily; color: Theme.label }
                    KeySequenceCapture {
                        sequence: AppController.shortcutSettingsView
                        onSequenceCaptured: (seq) => AppController.setShortcut("settings_view", seq)
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
                    onClicked: (mouse) => AppController.resetShortcuts()
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
