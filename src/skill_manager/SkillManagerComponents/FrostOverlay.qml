import QtQuick

Item {
    id: root
    anchors.fill: parent

    property real radius: 0
    
    // Layer 1: The Tint
    Rectangle {
        id: bgRect
        anchors.fill: parent
        color: Theme.appBackground
        radius: root.radius
        clip: true
        layer.enabled: root.radius > 0
    }

    // Layer 2: The Crystal Texture (Diamond Dust)
    Canvas {
        id: noiseCanvas
        anchors.fill: bgRect
        opacity: Theme.glassNoiseOpacity
        
        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            
            // Draw 5,000 fine points for a smooth matte finish
            ctx.fillStyle = Theme.darkMode ? "#FFFFFF" : "#000000";
            for (var i = 0; i < 5000; i++) {
                var x = Math.random() * width;
                var y = Math.random() * height;
                ctx.fillRect(x, y, 1, 1);
            }
        }
    }
}
