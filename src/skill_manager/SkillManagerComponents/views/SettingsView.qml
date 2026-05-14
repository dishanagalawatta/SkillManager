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


                }
            }
        }
    }
}
