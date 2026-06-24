import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root

    property string family: ""
    property string currentStyle: ""
    signal styleSelected(string style)

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Label {
            text: "Style"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeMetadata
            font.weight: Font.Bold
            color: Theme.secondaryLabel
        }

        SmoothListView {
            id: styleList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            model: {
                if (!root.family) return []
                return fontDB.getStyles(root.family)
            }

            currentIndex: {
                var mdl = styleList.model
                if (!mdl) return 0
                for (var i = 0; i < mdl.length; i++) {
                    if (mdl[i] === root.currentStyle) return i
                }
                return 0
            }

            onCurrentIndexChanged: {
                if (currentIndex >= 0 && model && model.length > currentIndex) {
                    root.styleSelected(model[currentIndex])
                }
            }

            delegate: ItemDelegate {
                width: styleList.width
                height: 32
                highlighted: styleList.currentIndex === index

                contentItem: Text {
                    text: modelData
                    font.family: root.family
                    font.pixelSize: 13
                    font.bold: fontDB.isBold(root.family, modelData)
                    font.italic: fontDB.isItalic(root.family, modelData)
                    color: highlighted ? Theme.accent : Theme.label
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                }

                background: Rectangle {
                    color: highlighted ? Theme.selectedRow :
                           hovered ? Theme.glassHover : "transparent"
                    radius: Theme.radiusSmall
                }

                onClicked: root.styleSelected(modelData)
            }

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        }
    }

    function refresh() {
        styleList.model = Qt.binding(() => {
            if (!root.family) return []
            return fontDB.getStyles(root.family)
        })
    }
}
