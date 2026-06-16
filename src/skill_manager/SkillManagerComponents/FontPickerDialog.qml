import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Popup {
    id: fontPickerDialog

    // --- Public API ---
    property string selectedFamily: "Segoe UI"
    property string selectedStyle: "Regular"
    property int selectedSize: 14
    property string previewText: "The quick brown fox jumps over the lazy dog"
    property color previewColor: Theme.label

    signal fontSelected(string family, string style, int size)

    // --- Dialog Properties ---
    modal: true
    width: 680
    height: 520
    parent: Overlay.overlay
    anchors.centerIn: parent
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    // --- Background ---
    background: Rectangle {
        radius: Theme.radiusCard
        color: Theme.glassPill
        border.color: Theme.glassBorder
        border.width: 1
    }

    // --- Enter/Exit Animations ---
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 200; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.95; to: 1.0; duration: 200; easing.type: Easing.OutCubic }
        }
    }

    exit: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 150; easing.type: Easing.InCubic }
            NumberAnimation { property: "scale"; from: 1.0; to: 0.95; duration: 150; easing.type: Easing.InCubic }
        }
    }

    onOpened: {
        fontDB.setSelectedFamily(selectedFamily)
        fontDB.setSelectedStyle(selectedStyle)
        familyColumn.refresh()
        styleColumn.refresh()
        sizeColumn.refresh()
    }

    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // --- Header with Title and Close Button ---
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "Select Font"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeSectionTitle
                font.weight: Font.Bold
                color: Theme.label
                Layout.fillWidth: true
            }

            IconButton {
                iconSource: AppController.ui_controller.getAssetUri("ui/tool-x.svg")
                tooltipText: "Close"
                role: "ghost"
                buttonSize: 28
                iconSize: 14
                onClicked: fontPickerDialog.close()
            }
        }

        // --- Search Field ---
        GlassSearchInput {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search fonts..."
            onTextChanged: familyColumn.searchFilter = text
        }

        // --- Three-Column Selector ---
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            FontFamilyColumn {
                id: familyColumn
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentFamily: fontPickerDialog.selectedFamily
                searchFilter: searchField.text
                onFamilySelected: (family) => {
                    fontPickerDialog.selectedFamily = family
                    fontDB.setSelectedFamily(family)
                    styleColumn.refresh()
                    sizeColumn.refresh()
                }
            }

            FontStyleColumn {
                id: styleColumn
                Layout.fillWidth: true
                Layout.fillHeight: true
                family: fontPickerDialog.selectedFamily
                currentStyle: fontPickerDialog.selectedStyle
                onStyleSelected: (style) => {
                    fontPickerDialog.selectedStyle = style
                    fontDB.setSelectedStyle(style)
                    sizeColumn.refresh()
                }
            }

            FontSizeColumn {
                id: sizeColumn
                Layout.fillWidth: true
                Layout.fillHeight: true
                family: fontPickerDialog.selectedFamily
                style: fontPickerDialog.selectedStyle
                currentSize: fontPickerDialog.selectedSize
                onSizeSelected: (size) => {
                    fontPickerDialog.selectedSize = size
                }
            }
        }

        // --- Preview Pane ---
        FontPreviewPane {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            family: fontPickerDialog.selectedFamily
            style: fontPickerDialog.selectedStyle
            size: fontPickerDialog.selectedSize
            previewText: fontPickerDialog.previewText
            previewColor: fontPickerDialog.previewColor
        }

        // --- Footer Buttons ---
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight
            spacing: 8

            ActionButton {
                text: "Cancel"
                role: "secondary"
                onClicked: fontPickerDialog.close()
            }
            ActionButton {
                text: "Select"
                role: "primary"
                onClicked: {
                    fontPickerDialog.fontSelected(
                        fontPickerDialog.selectedFamily,
                        fontPickerDialog.selectedStyle,
                        fontPickerDialog.selectedSize
                    )
                    fontPickerDialog.close()
                }
            }
        }
    }
}
