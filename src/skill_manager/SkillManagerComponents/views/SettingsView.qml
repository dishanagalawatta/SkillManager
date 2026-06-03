import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import App 1.0
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

        GlassPill {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: Theme.radiusPill

            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 4

                TabButton {
                    id: generalTab
                    text: "General"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    checked: tabBar.currentIndex === 0
                    onClicked: tabBar.currentIndex = 0
                    
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
                        radius: Theme.radiusPill - 4
                    }
                }
                TabButton {
                    id: shortcutsTab
                    text: "Shortcuts"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    checked: tabBar.currentIndex === 1
                    onClicked: tabBar.currentIndex = 1
                    
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
                        radius: Theme.radiusPill - 4
                    }
                }
            }
        }

        // Hidden TabBar to drive the StackLayout
        TabBar {
            id: tabBar
            visible: false
            height: 0
            TabButton { text: "General" }
            TabButton { text: "Shortcuts" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // Settings Content
            SmoothScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth

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

                            RowLayout {
                                Text {
                                    text: "Dark Mode"
                                    font.family: Theme.fontFamily
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                GlassSwitch {
                                    checked: AppController.ui_controller ? AppController.ui_controller.darkMode : false
                                    onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.darkMode = checked
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
                                    checked: AppController.ui_controller ? AppController.ui_controller.reducedMotion : false
                                    onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.setReducedMotion(checked)
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
                                    checked: AppController.ui_controller ? AppController.ui_controller.compactListRows : false
                                    onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.setCompactListRows(checked)
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            RowLayout {
                                spacing: 12
                                ColumnLayout {
                                    spacing: 2
                                    Layout.fillWidth: true
                                    Text {
                                        text: "Scroll Speed"
                                        font.family: Theme.fontFamily
                                        color: Theme.label
                                    }
                                    Text {
                                        text: "Multiplier: " + (AppController.config_controller ? AppController.config_controller.scrollSpeedMultiplier.toFixed(1) : "1.0") + "x"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        color: Theme.secondaryLabel
                                    }
                                }
                                Slider {
                                    Layout.preferredWidth: 150
                                    from: 0.5
                                    to: 5.0
                                    stepSize: 0.1
                                    value: AppController.config_controller ? AppController.config_controller.scrollSpeedMultiplier : 1.0
                                    onMoved: if (AppController.config_controller) AppController.config_controller.scrollSpeedMultiplier = value
                                }
                            }
                        }
                    }

                    // Application Updates Section
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
                                text: "Application Updates"
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
                                    text: "Auto Check for Updates"
                                    font.family: Theme.fontFamily
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                GlassSwitch {
                                    checked: AppController.config_controller ? AppController.config_controller.autoCheckUpdates : true
                                    onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoCheckUpdates = checked
                                }
                            }

                            RowLayout {
                                Text {
                                    text: "Auto Download Updates"
                                    font.family: Theme.fontFamily
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                GlassSwitch {
                                    checked: AppController.config_controller ? AppController.config_controller.autoDownloadUpdates : false
                                    onCheckedChanged: if (AppController.config_controller) AppController.config_controller.autoDownloadUpdates = checked
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.separator
                            }

                            Text {
                                text: "Skill Packages"
                                font.family: Theme.fontFamily
                                font.pixelSize: 14
                                font.weight: Font.Bold
                                color: Theme.label
                            }

                            RowLayout {
                                Text {
                                    text: "Skill Package Auto Updates"
                                    font.family: Theme.fontFamily
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                GlassSwitch {
                                    checked: AppController.config_controller ? AppController.config_controller.skillPackageAutoUpdate : true
                                    onCheckedChanged: if (AppController.config_controller) AppController.config_controller.skillPackageAutoUpdate = checked
                                }
                            }

                            RowLayout {
                                Text {
                                    text: "Auto Update Mode"
                                    font.family: Theme.fontFamily
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                GlassDropdown {
                                    model: ["prompt", "silent"]
                                    currentIndex: AppController.config_controller ? model.indexOf(AppController.config_controller.skillPackageAutoUpdateMode) : 0
                                    onActivated: {
                                        if (AppController.config_controller) AppController.config_controller.skillPackageAutoUpdateMode = model[index]
                                    }
                                    Layout.preferredWidth: 100
                                }
                            }

                            RowLayout {
                                spacing: 12
                                ColumnLayout {
                                    spacing: 2
                                    Layout.fillWidth: true
                                    Text {
                                        text: "Check Interval"
                                        font.family: Theme.fontFamily
                                        color: Theme.label
                                    }
                                    Text {
                                        text: "Every " + (AppController.config_controller ? AppController.config_controller.updateCheckIntervalHours : 24) + " hours"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        color: Theme.secondaryLabel
                                    }
                                }
                                Slider {
                                    Layout.preferredWidth: 150
                                    from: 1
                                    to: 168
                                    stepSize: 1
                                    value: AppController.config_controller ? AppController.config_controller.updateCheckIntervalHours : 24
                                    onMoved: if (AppController.config_controller) AppController.config_controller.updateCheckIntervalHours = value
                                }
                            }
                        }
                    }

                    // Context Menu Section
                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: contextMenuLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: contextMenuLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "Context Menu"
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
                                    text: "Show Icons"
                                    font.family: Theme.fontFamily
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                GlassSwitch {
                                    checked: AppController.config_controller ? AppController.config_controller.showMenuIcons : true
                                    onCheckedChanged: if (AppController.config_controller) AppController.config_controller.showMenuIcons = checked
                                }
                            }

                            RowLayout {
                                Text {
                                    text: "Compact Menu"
                                    font.family: Theme.fontFamily
                                    color: Theme.label
                                    Layout.fillWidth: true
                                }
                                GlassSwitch {
                                    checked: AppController.config_controller ? AppController.config_controller.compactMenu : false
                                    onCheckedChanged: if (AppController.config_controller) AppController.config_controller.compactMenu = checked
                                }
                            }
                        }
                    }

                    // Daily Speed Section
                    GlassPill {
                        Layout.fillWidth: true
                        Layout.preferredHeight: dailySpeedLayout.implicitHeight + 32
                        radius: Theme.radiusCard

                        ColumnLayout {
                            id: dailySpeedLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

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
                                    currentIndex: AppController.ui_controller ? Math.max(0, model.indexOf(AppController.ui_controller.startupView)) : 0
                                    onActivated: (index) => { if (AppController.ui_controller) AppController.ui_controller.setStartupView(model[index]) }
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
                                    model: AppController.clientFormats ? AppController.clientFormats : []
                                    currentIndex: AppController.ui_controller ? Math.max(0, model.indexOf(AppController.clientFormat)) : 0
                                    onActivated: (index) => { if (AppController.ui_controller) AppController.ui_controller.setClientFormat(model[index]) }
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
                                    currentIndex: AppController.ui_controller && AppController.ui_controller.defaultProjectFilter === "all" ? 1 : 0
                                    onActivated: (index) => { if (AppController.ui_controller) AppController.ui_controller.setDefaultProjectFilter(index === 1 ? "all" : "last") }
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
                                    checked: AppController.ui_controller ? AppController.ui_controller.rememberFilters : true
                                    onCheckedChanged: if (AppController.ui_controller) AppController.ui_controller.setRememberFilters(checked)
                                }
                            }

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
            }
            
            ShortcutsSettings {}
        }
    }
}
