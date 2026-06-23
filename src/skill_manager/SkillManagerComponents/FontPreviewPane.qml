import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root

    property string family: ""
    property string style: ""
    property int size: 14
    property string previewText: "The quick brown fox jumps over the lazy dog"
    property color previewColor: Theme.label

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 4

        Label {
            text: "Preview"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeMetadata
            font.weight: Font.Bold
            color: Theme.secondaryLabel
        }

        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: root.previewText
            font.family: root.family
            font.pixelSize: root.size
            font.bold: fontDB.isBold(root.family, root.style)
            font.italic: fontDB.isItalic(root.family, root.style)
            color: root.previewColor
            wrapMode: Text.WordWrap
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            maximumLineCount: 2
        }
    }
}
