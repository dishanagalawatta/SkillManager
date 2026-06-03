import QtQuick
import QtQuick.Controls

ListView {
    id: root

    WheelHandler {
        target: root
        onWheel: (event) => {
            // If multiplier is 1.0, we let the default behavior handle it.
            // If it's different, we add/subtract the difference.
            // Note: We don't 'accept' the event so the default scroll still happens,
            // we just supplement it.
            let multiplier = appController.config_mgr.scrollSpeedMultiplier
            if (multiplier !== 1.0) {
                // angleDelta.y is typically 120.
                // We want to add (multiplier - 1) * 120 pixels of extra scroll.
                // However, standard scroll is not exactly 120 pixels.
                // It varies by platform. 
                // A better way is to accept the event and handle it entirely if we want precise control.
                
                // For now, let's try the additive approach with a scaling factor.
                let extra = event.angleDelta.y * (multiplier - 1.0) * 0.5 
                root.contentY = Math.max(root.originY, 
                                         Math.min(root.contentY - extra, 
                                                  root.originY + root.contentHeight - root.height))
            }
        }
    }
}
