import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App 1.0

/*!
    \qmltype InspectorActionBar
    \inqmlmodule SkillManagerComponents
    \brief Reusable action ribbon component for inspector panels.

    Renders action buttons (Copy Path, Open Folder, Star, Delete) using design system
    tokens from Theme.qml.

    \property var selectedSkill
        The skill dictionary or live-bound selection object.
    \property bool showStarButton
        Whether to display the star toggle button.
    \property bool showDeleteButton
        Whether to display the delete action button.

    \signal starClicked()
        Emitted when the star button is clicked.
    \signal copyPathClicked()
        Emitted when the copy path button is clicked.
    \signal openFolderClicked()
        Emitted when the open folder button is clicked.
    \signal deleteClicked()
        Emitted when the delete button is clicked.
    \signal editClicked()
        Emitted when the edit button is clicked.
*/
RowLayout {
    id: root

    property var selectedSkill: null
    property bool showStarButton: true
    property bool showDeleteButton: false

    signal starClicked()
    signal copyPathClicked()
    signal openFolderClicked()
    signal deleteClicked()
    signal editClicked()

    Layout.fillWidth: true
    spacing: 8
    visible: root.selectedSkill && root.selectedSkill.local_path !== undefined

    // Star Button
    IconButton {
        id: starBtn
        iconSource: (root.selectedSkill && root.selectedSkill.is_starred)
            ? AppController.ui_controller.getAssetUri("ui/star-filled.svg")
            : AppController.ui_controller.getAssetUri("ui/star-outline.svg")
        customIconColor: (root.selectedSkill && root.selectedSkill.is_starred) ? "#FFD700" : Theme.secondaryLabel
        iconSize: 20
        flat: true
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        visible: root.showStarButton
        onClicked: (mouse) => root.starClicked()
        tooltipText: (root.selectedSkill && root.selectedSkill.is_starred) ? "Unstar Skill" : "Star Skill"

        background: Rectangle {
            color: starBtn.hovered ? Theme.glassHover : "transparent"
            radius: Theme.radiusPill
        }
    }

    // Open Folder / Path Button
    IconButton {
        id: openFolderBtn
        iconSource: AppController.ui_controller.getAssetUri("ui/folder-open.svg")
        flat: true
        iconSize: 20
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        visible: root.selectedSkill && root.selectedSkill.local_path !== undefined
        onClicked: (mouse) => {
            if (root.selectedSkill && root.selectedSkill.local_path) {
                AppController.ui_controller.openPath(root.selectedSkill.local_path)
            }
            root.openFolderClicked()
        }
        tooltipText: "Open file location"

        background: Rectangle {
            color: openFolderBtn.hovered ? Theme.glassHover : "transparent"
            radius: Theme.radiusPill
        }
    }

    // Copy Path Button
    IconButton {
        id: copyPathBtn
        iconSource: AppController.ui_controller.getAssetUri("ui/copy-icon.svg")
        flat: true
        iconSize: 20
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        visible: root.selectedSkill && root.selectedSkill.local_path !== undefined
        onClicked: (mouse) => {
            if (root.selectedSkill && root.selectedSkill.local_path) {
                AppController.ui_controller.copyToClipboard(root.selectedSkill.local_path)
            }
            root.copyPathClicked()
        }
        tooltipText: "Copy file path"

        background: Rectangle {
            color: copyPathBtn.hovered ? Theme.glassHover : "transparent"
            radius: Theme.radiusPill
        }
    }

    // Optional Delete Button
    IconButton {
        id: deleteBtn
        iconSource: AppController.ui_controller.getAssetUri("ui/delete-icon.svg")
        role: "destructive"
        flat: true
        iconSize: 20
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        visible: root.showDeleteButton && root.selectedSkill && root.selectedSkill.local_path !== undefined
        onClicked: (mouse) => root.deleteClicked()
        tooltipText: "Delete item"

        background: Rectangle {
            color: deleteBtn.hovered ? Theme.glassHover : "transparent"
            radius: Theme.radiusPill
        }
    }
}
