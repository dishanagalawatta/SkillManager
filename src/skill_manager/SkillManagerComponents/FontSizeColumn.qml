import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root

    property string family: ""
    property string style: ""
    property int currentSize: 14
    signal sizeSelected(int size)

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Label {
            text: "Size"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeMetadata
            font.weight: Font.Bold
            color: Theme.secondaryLabel
        }

        // Direct size input
        SpinBox {
            id: sizeInput
            Layout.fillWidth: true
            from: 6
            to: 120
            value: root.currentSize
            editable: true
            onValueModified: root.sizeSelected(value)

            contentItem: TextInput {
                text: sizeInput.textFromValue(sizeInput.value, sizeInput.locale)
                font.family: Theme.fontFamily
                font.pixelSize: 12
                color: Theme.label
                horizontalAlignment: Qt.AlignHCenter
                verticalAlignment: Qt.AlignVCenter
                readOnly: !sizeInput.editable
                validator: sizeInput.validator
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }

            background: Rectangle {
                radius: Theme.radiusSmall
                color: Theme.glassPill
                border.color: sizeInput.activeFocus ? Theme.accent : Theme.glassBorder
                border.width: sizeInput.activeFocus ? 2 : 1
            }
        }

        SmoothListView {
            id: sizeList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            model: {
                if (!root.family || !root.style) return fontDB.standardSizes
                return fontDB.getSizes(root.family, root.style)
            }

            currentIndex: {
                var mdl = sizeList.model
                if (!mdl) return -1
                for (var i = 0; i < mdl.length; i++) {
                    if (mdl[i] === root.currentSize) return i
                }
                return -1
            }

            onCurrentIndexChanged: {
                if (currentIndex >= 0 && model && model.length > currentIndex) {
                    root.sizeSelected(model[currentIndex])
                }
            }

            delegate: ItemDelegate {
                width: sizeList.width
                height: 28
                highlighted: sizeList.currentIndex === index

                contentItem: Text {
                    text: modelData
                    font.family: Theme.fontFamily
                    font.pixelSize: 12
                    color: highlighted ? Theme.accent : Theme.label
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    color: highlighted ? Theme.selectedRow :
                           hovered ? Theme.glassHover : "transparent"
                    radius: Theme.radiusSmall
                }

                onClicked: root.sizeSelected(modelData)
            }

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        }
    }

    function refresh() {
        sizeList.model = Qt.binding(() => {
            if (!root.family || !root.style) return fontDB.standardSizes
            return fontDB.getSizes(root.family, root.style)
        })
    }
}
