import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App 1.0

Rectangle {
    id: root

    property string currentFamily: ""
    property string searchFilter: ""
    signal familySelected(string family)

    radius: Theme.radiusCard
    color: Theme.glassPill
    border.color: Theme.glassBorder
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Label {
            text: "Family"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeMetadata
            font.weight: Font.Bold
            color: Theme.secondaryLabel
        }

        SmoothListView {
            id: familyList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            model: {
                var allFamilies = fontDB.families
                if (root.searchFilter === "") return allFamilies
                var query = root.searchFilter.toLowerCase()
                return allFamilies.filter(f => f.toLowerCase().includes(query))
            }

            currentIndex: {
                var mdl = familyList.model
                for (var i = 0; i < mdl.length; i++) {
                    if (mdl[i] === root.currentFamily) return i
                }
                return -1
            }

            onCurrentIndexChanged: {
                if (currentIndex >= 0 && model && model.length > currentIndex) {
                    root.familySelected(model[currentIndex])
                }
            }

            delegate: ItemDelegate {
                width: familyList.width
                height: 32
                highlighted: familyList.currentIndex === index

                contentItem: Text {
                    text: modelData
                    font.family: modelData
                    font.pixelSize: 13
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

                onClicked: root.familySelected(modelData)
            }

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        }
    }

    function refresh() {
        familyList.model = Qt.binding(() => {
            var allFamilies = fontDB.families
            if (root.searchFilter === "") return allFamilies
            var query = root.searchFilter.toLowerCase()
            return allFamilies.filter(f => f.toLowerCase().includes(query))
        })
    }
}
