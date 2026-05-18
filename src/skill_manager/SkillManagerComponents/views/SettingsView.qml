import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0
import ".."

Item {
    id: sv_root

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

        // Settings Content
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: 25

                // Appearance Section
                ColumnLayout {
                    spacing: 12
                    Layout.fillWidth: true

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

                    RowLayout {
                        Text {
                            text: "Dark Mode"
                            font.family: Theme.fontFamily
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                        GlassSwitch {
                            checked: AppController.darkMode
                            onCheckedChanged: AppController.darkMode = checked
                        }
                    }

                    RowLayout {
                        Text {
                            text: "Reduced Motion"
                            font.family: Theme.fontFamily
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                        GlassSwitch {
                            checked: AppController.reducedMotion
                            onCheckedChanged: AppController.setReducedMotion(checked)
                        }
                    }

                    RowLayout {
                        Text {
                            text: "Compact List Rows"
                            font.family: Theme.fontFamily
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                        GlassSwitch {
                            checked: AppController.compactListRows
                            onCheckedChanged: AppController.setCompactListRows(checked)
                        }
                    }
                }

                ColumnLayout {
                    spacing: 12
                    Layout.fillWidth: true

                    Text {
                        text: "Daily Speed"
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

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Startup View"
                            font.family: Theme.fontFamily
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                        GlassDropdown {
                            Layout.preferredWidth: 170
                            model: ["Library", "QuickCopy", "Updates", "Settings"]
                            currentIndex: Math.max(0, model.indexOf(AppController.startupView))
                            onActivated: (index) => AppController.setStartupView(model[index])
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Default Client"
                            font.family: Theme.fontFamily
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                        GlassDropdown {
                            Layout.preferredWidth: 170
                            model: AppController.clientFormats
                            currentIndex: Math.max(0, model.indexOf(AppController.clientFormat))
                            onActivated: (index) => AppController.setClientFormat(model[index])
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Project Filter"
                            font.family: Theme.fontFamily
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                        GlassDropdown {
                            Layout.preferredWidth: 170
                            model: ["Last Project", "All Projects"]
                            currentIndex: AppController.defaultProjectFilter === "all" ? 1 : 0
                            onActivated: (index) => AppController.setDefaultProjectFilter(index === 1 ? "all" : "last")
                        }
                    }

                    RowLayout {
                        Text {
                            text: "Remember Filters"
                            font.family: Theme.fontFamily
                            color: Theme.label
                            Layout.fillWidth: true
                        }
                        GlassSwitch {
                            checked: AppController.rememberFilters
                            onCheckedChanged: AppController.setRememberFilters(checked)
                        }
                    }

                    ActionButton {
                        Layout.preferredHeight: 36
                        text: "Reset UI State"
                        onClicked: (mouse) => AppController.resetUiState()
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
}
