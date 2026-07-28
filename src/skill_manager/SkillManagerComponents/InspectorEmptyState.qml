import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

/*!
    \qmltype InspectorEmptyState
    \inqmlmodule SkillManagerComponents
    \brief Reusable placeholder component for empty inspector panel states.

    Renders centered placeholder icon, title, and guidance text using design system
    tokens from Theme.qml when no skill or command is selected.

    \property string titleText
        The header text (defaults to "No Selection").
    \property string guidanceText
        The descriptive body text for guidance.
*/
ColumnLayout {
    id: root

    property string titleText: "No Selection"
    property string guidanceText: "Select an item from the list to view details."

    Layout.fillWidth: true
    Layout.fillHeight: true
    alignment: Qt.AlignCenter
    spacing: 12

    Image {
        id: placeholderIcon
        source: AppController.ui_controller.getAssetUri("ui/info-icon.svg")
        sourceSize.width: 48
        sourceSize.height: 48
        Layout.alignment: Qt.AlignHCenter
        opacity: 0.4
    }

    Text {
        text: root.titleText
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeSectionTitle
        font.weight: Font.Bold
        color: Theme.secondaryLabel
        Layout.alignment: Qt.AlignHCenter
        horizontalAlignment: Text.AlignHCenter
    }

    Text {
        text: root.guidanceText
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeSubtext
        color: Theme.tertiaryLabel
        Layout.alignment: Qt.AlignHCenter
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        Layout.maximumWidth: 260
    }
}
