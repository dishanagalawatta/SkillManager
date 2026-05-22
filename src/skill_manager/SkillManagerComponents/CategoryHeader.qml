import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0
import SkillManagerComponents 1.0

Item {
    id: root
    width: parent.width

    property string mainCatName: "" // Passed from ListView section
    property bool isMainCollapsed: AppController.skillModel.collapsedCategories.includes(mainCatName)

    height: 44 // Fixed height for main header
    visible: mainCatName !== ""

    Rectangle {
        anchors.fill: parent
        color: mouseAreaMain.containsMouse ? Theme.glassHover : "transparent"
        radius: Theme.radiusSmall
        anchors.margins: 2
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 8

        Image {
            source: root.isMainCollapsed ?
                    AppController.getAssetUri(Theme.darkMode ? "ui/expand-arrow-icon-dark.svg" : "ui/expand-arrow-icon-light.svg") :
                    AppController.getAssetUri(Theme.darkMode ? "ui/collapse-arrow-icon-dark.svg" : "ui/collapse-arrow-icon-light.svg")
            width: 14
            height: 14
            Layout.preferredWidth: 14
            Layout.preferredHeight: 14
            Layout.alignment: Qt.AlignVCenter
            sourceSize.width: 56
            sourceSize.height: 56
            fillMode: Image.PreserveAspectFit
            opacity: 0.7
            horizontalAlignment: Image.AlignHCenter
            verticalAlignment: Image.AlignVCenter
        }

        Text {
            text: {
                if (!root.mainCatName) return "";
                if (root.mainCatName === "Special") return "⭐";
                let parts = root.mainCatName.split(" ");
                return parts.length > 0 ? parts[0] : "";
            }
            font.pixelSize: 20
            opacity: root.isMainCollapsed ? 0.7 : 1.0
            Layout.alignment: Qt.AlignVCenter
            Behavior on opacity { NumberAnimation { duration: 200 } }
        }

        Text {
            Layout.fillWidth: true
            text: {
                if (!root.mainCatName) return "";
                if (root.mainCatName === "Special") return "Special";
                let spaceIdx = root.mainCatName.indexOf(" ");
                return spaceIdx !== -1 ? root.mainCatName.substring(spaceIdx + 1) : root.mainCatName;
            }
            font.family: Theme.fontFamily
            font.pixelSize: 14
            font.weight: Font.Bold
            color: root.mainCatName === "Special" ? "#FFD700" : Theme.label
            opacity: 0.9
        }
    }

    MouseArea {
        id: mouseAreaMain
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: (mouse) => Qt.callLater(AppController.skillModel.toggleCategory, root.mainCatName)

        ToolTip.text: root.isMainCollapsed ? "Expand " + root.mainCatName : "Collapse " + root.mainCatName
        ToolTip.visible: containsMouse
        ToolTip.delay: 400

        Accessible.role: Accessible.Button
        Accessible.name: root.mainCatName
        Accessible.description: ToolTip.text
    }
}
