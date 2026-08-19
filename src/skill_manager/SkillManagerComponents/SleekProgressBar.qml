import QtQuick
import QtQuick.Effects

Item {
    id: root
    property bool running: false
    property color color: Theme.accent
    property real barHeight: 3
    
    // Internal animation progress
    property real animationProgress: 0
    
    height: barHeight
    clip: true
    visible: running

    NumberAnimation on animationProgress {
        from: 0
        to: 1
        duration: 1500
        loops: Animation.Infinite
        running: root.running
    }

    Rectangle {
        id: track
        anchors.fill: parent
        color: Theme.alpha(root.color, 0.15)
        radius: height / 2
    }
    
    Rectangle {
        id: indicator
        height: parent.height
        radius: height / 2
        color: root.color
        
        // Dynamically compute width and x based on animationProgress
        // width pulses between 10% and 50% of parent width
        width: Math.max(root.width * 0.1, root.width * (0.1 + 0.4 * Math.sin(root.animationProgress * Math.PI)))
        
        // x sweeps from just off-screen left to just off-screen right
        x: -width + (root.width + width) * root.animationProgress
    }
    
    MultiEffect {
        source: indicator
        anchors.fill: indicator
        shadowEnabled: true
        shadowColor: root.color
        shadowBlur: 0.8
        shadowOpacity: 0.6
        shadowHorizontalOffset: 0
        shadowVerticalOffset: 0
    }
}
