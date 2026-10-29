import QtQuick
import QtQuick.Layouts
import App 1.0

// Application-level update surface, shared by Settings and the Updates hub.
//
// Everything is bound to AppUpdateController so both hosts stay truthful:
// checks, download progress, checksum/install failures and the platform
// install kind each have exactly one source of truth.
GlassPill {
    id: root
    objectName: "appUpdateCard"

    // Compact drops the explanatory captions; used in the Updates hub banner.
    property bool compact: false

    readonly property var controller: AppController.app_update_controller
    readonly property bool updateAvailable: controller.updateAvailable
    readonly property bool downloading: controller.isDownloading
    readonly property bool installing: controller.installInProgress
    readonly property bool checking: controller.isCheckingForUpdates
    readonly property bool supported: controller.selfUpdateSupported
    readonly property string installError: controller.installError

    function progressLabel() {
        if (root.installing) return "Installing…"
        if (root.downloading) {
            return "Downloading…"
        }
        if (root.updateAvailable) {
            return root.supported ? "Download & Install" : "Update Available"
        }
        return root.checking ? "Checking…" : "Check for Updates"
    }

    Layout.fillWidth: true
    Layout.preferredHeight: cardLayout.implicitHeight + (root.compact ? 20 : 28)
    radius: Theme.radiusCard

    ColumnLayout {
        id: cardLayout
        anchors.fill: parent
        anchors.margins: root.compact ? 10 : 14
        spacing: root.compact ? 6 : 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ColumnLayout {
                spacing: 1
                Text {
                    text: "SkillManager Application"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeBody
                    font.weight: Font.DemiBold
                    color: Theme.label
                }
                Text {
                    objectName: "appUpdateVersionText"
                    text: root.updateAvailable
                        ? "Version v" + root.controller.currentVersion + "  →  v"
                            + root.controller.latestVersion
                        : "Version v" + root.controller.currentVersion
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.sizeCaption
                    color: root.updateAvailable ? Theme.accent : Theme.secondaryLabel
                }
            }

            Item { Layout.fillWidth: true }

            ActionButton {
                objectName: "appUpdateReleaseBtn"
                labelText: "View Release"
                role: "secondary"
                buttonHeight: 28
                tooltipText: "Open the SkillManager release page in your browser"
                onClicked: (mouse) => root.controller.openReleasesPage()
            }

            ActionButton {
                objectName: "appUpdateCancelBtn"
                visible: root.downloading
                labelText: "Cancel"
                role: "secondary"
                buttonHeight: 28
                tooltipText: "Cancel the update download"
                onClicked: (mouse) => root.controller.cancelUpdateDownload()
            }

            ActionButton {
                objectName: "appUpdateInstallBtn"
                // A source checkout has no artifact to install into; keep the
                // primary action out of the UI and let the reason line explain.
                visible: root.updateAvailable && (root.supported || root.downloading || root.installing)
                enabled: root.supported && !root.downloading && !root.installing
                labelText: root.progressLabel()
                role: "primary"
                buttonHeight: 28
                tooltipText: root.supported
                    ? "Download, verify and install SkillManager v" + root.controller.latestVersion
                    : root.controller.selfUpdateReason
                onClicked: (mouse) => root.controller.downloadAndInstallUpdate()
            }

            ActionButton {
                objectName: "appUpdateCheckBtn"
                visible: !root.updateAvailable
                enabled: !root.checking
                labelText: root.progressLabel()
                role: "secondary"
                buttonHeight: 28
                tooltipText: "Check GitHub Releases for a newer SkillManager version"
                onClicked: (mouse) => root.controller.checkForUpdates(true)
            }
        }

        // Determinate progress when the server sends a content length; the
        // indeterminate track is the honest fallback for chunked responses.
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            visible: root.downloading

            Rectangle {
                Layout.fillWidth: true
                height: 5
                radius: 2.5
                color: Theme.alpha(Theme.accent, 0.16)

                Rectangle {
                    height: parent.height
                    radius: parent.radius
                    color: Theme.accent
                    width: root.controller.downloadTotalBytes > 0
                        ? Math.max(4, parent.width * root.controller.downloadProgress / 100)
                        : parent.width * 0.18
                    Behavior on width { NumberAnimation { duration: 160 } }
                }
            }

            Text {
                objectName: "appUpdateProgressText"
                text: root.controller.downloadTotalBytes > 0
                    ? root.controller.downloadProgress + "%  ·  "
                        + (root.controller.downloadedBytes / 1048576).toFixed(0) + " / "
                        + (root.controller.downloadTotalBytes / 1048576).toFixed(0) + " MB"
                    : (root.controller.downloadedBytes / 1048576).toFixed(0) + " MB"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.sizeCaption
                color: Theme.secondaryLabel
            }
        }

        Text {
            objectName: "appUpdateErrorText"
            Layout.fillWidth: true
            visible: root.installError !== ""
            text: root.installError
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            color: Theme.warning
            wrapMode: Text.WordWrap
        }

        Text {
            Layout.fillWidth: true
            visible: root.updateAvailable && !root.supported
            text: root.controller.selfUpdateReason
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            color: Theme.secondaryLabel
            wrapMode: Text.WordWrap
        }

        Text {
            Layout.fillWidth: true
            visible: !root.compact && root.supported && root.updateAvailable
            text: "The download is verified against the release SHA-256 checksum before "
                + "the " + root.controller.installKindLabel + " is installed. "
                + "SkillManager restarts automatically."
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            color: Theme.secondaryLabel
            wrapMode: Text.WordWrap
        }
    }
}
