import QtQuick
import QtQuick.Layouts

// Bottom-right transient notification for skill package auto-update events.
//
// Two shapes, both driven from Python (UpdateController signals):
//   - updates available (Auto Update off): message + Update action button.
//   - background auto-update finished: informational message, no action.
//
// Shown/hidden imperatively via show()/hide(); auto-dismisses after 10s.
// Follows the statusToast pattern in Main.qml (Theme tokens only).
Rectangle {
    id: root
    objectName: "updateToast"

    property string toastTitle: ""
    property string toastMessage: ""
    property bool showAction: false
    // "packages" = skill-package updates (opens Updates and installs them),
    // "release"  = app release (opens the GitHub releases page).
    property string actionMode: "packages"

    function show(title, message, action, mode) {
        root.toastTitle = title
        root.toastMessage = message
        root.showAction = action
        root.actionMode = mode === undefined ? "packages" : mode
        root.visible = true
        hideTimer.restart()
    }

    function hide() {
        hideTimer.stop()
        root.visible = false
    }

    visible: false
    width: Math.min(window.width - 32, 360)
    height: toastLayout.implicitHeight + 24
    radius: Theme.radiusCard
    color: Theme.alpha(Theme.glassPill, 0.97)
    border.color: Theme.glassBorder
    border.width: 1
    z: 110

    ColumnLayout {
        id: toastLayout
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 12
        anchors.bottomMargin: 12
        spacing: 8

        Text {
            objectName: "updateToastTitle"
            text: root.toastTitle
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            font.weight: Font.Bold
            color: Theme.label
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Text {
            objectName: "updateToastMessage"
            text: root.toastMessage
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            color: Theme.secondaryLabel
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        RowLayout {
            spacing: 8

            Item {
                Layout.fillWidth: true
            }

            ActionButton {
                objectName: "updateToastDismissBtn"
                labelText: "Dismiss"
                role: "secondary"
                buttonHeight: 28
                tooltipText: "Dismiss this notification"
                onClicked: (mouse) => root.hide()
            }

            ActionButton {
                objectName: "updateToastActionBtn"
                visible: root.showAction
                labelText: root.actionMode === "release" ? "View Release" : "Update"
                role: "primary"
                buttonHeight: 28
                tooltipText: root.actionMode === "release"
                             ? "Open the SkillManager release page"
                             : "Open Updates and install all package updates"
                onClicked: (mouse) => {
                    root.hide()
                    if (root.actionMode === "release") {
                        AppController.app_update_controller.openReleasesPage()
                    } else {
                        window.navigateTo("Updates")
                        AppController.update_controller.updateAllOutdated()
                    }
                }
            }
        }
    }

    Timer {
        id: hideTimer
        interval: 10000
        onTriggered: root.hide()
    }
}
