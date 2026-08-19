import QtQuick
import QtQuick.Controls
import App 1.0

ScrollView {
    id: root

    ScrollBar.vertical: AppScrollBar {
        interactive: true
    }

    WheelHandler {
        target: root.contentItem
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: (event) => {
            let config = AppController.config_controller
            let multiplier = (config && typeof config.scrollSpeedMultiplier !== "undefined") ? config.scrollSpeedMultiplier : 1.0

            if (Math.abs(multiplier - 1.0) < 0.01 || !root.contentItem) {
                event.accepted = false
                return
            }

            event.accepted = true

            let flick = root.contentItem
            if (event.pixelDelta.y !== 0) {
                let scrollAmount = event.pixelDelta.y * multiplier
                flick.contentY = Math.max(flick.originY,
                                          Math.min(flick.contentY - scrollAmount,
                                                   flick.originY + Math.max(0, flick.contentHeight - flick.height)))
                return
            }

            let scrollAmount = event.angleDelta.y * (multiplier * 0.5)
            flick.contentY = Math.max(flick.originY,
                                      Math.min(flick.contentY - scrollAmount,
                                               flick.originY + Math.max(0, flick.contentHeight - flick.height)))
        }
    }
}
