import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

Item {
    id: root
    width: parent.width
    height: 38
    
    property string sectionName: ""
    property bool isCollapsed: AppController.skillModel.isCategoryCollapsed(sectionName)

    Rectangle {
        anchors.fill: parent
        color: mouseAreaSection.containsMouse ? Theme.glassHover : "transparent"
        radius: Theme.radiusSmall
        anchors.margins: 3
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 8

        Image {
            source: root.isCollapsed ? AppController.getAssetUri("ui/expand.svg") : AppController.getAssetUri("ui/collapse.svg")
            sourceSize.width: 12
            sourceSize.height: 12
            fillMode: Image.PreserveAspectFit
            opacity: 0.6
            horizontalAlignment: Image.AlignHCenter
            verticalAlignment: Image.AlignVCenter
        }

        Text {
            id: categoryEmoji
            text: root.sectionName === "Essentials" ? "⭐" : AppController.getCategoryEmoji(root.sectionName)
            font.pixelSize: 18
            opacity: root.isCollapsed ? 0.6 : 1.0
            Layout.alignment: Qt.AlignVCenter
            
            Behavior on opacity { NumberAnimation { duration: 200 } }
        }


        Text {
            Layout.fillWidth: true
            text: root.sectionName
            font.family: Theme.fontFamily
            font.pixelSize: 12
            font.weight: Font.Bold
            color: root.sectionName === "Essentials" ? "#FFD700" : Theme.secondaryLabel
            opacity: 0.8
        }
    }

    Accessible.role: Accessible.Button
    Accessible.name: (root.isCollapsed ? "Expand" : "Collapse") + " category " + root.sectionName

    MouseArea {
        id: mouseAreaSection
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: (mouse) => Qt.callLater(AppController.skillModel.toggleCategory, root.sectionName)

        ToolTip.text: root.isCollapsed ? "Expand " + root.sectionName : "Collapse " + root.sectionName
        ToolTip.visible: containsMouse
        ToolTip.delay: 400
    }
}
