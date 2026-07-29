import QtQuick
import Qt5Compat.GraphicalEffects
import "."

Item {
    id: root

    property Item sourceItem: null
    property color primaryColor: Theme.darkMode ? "#F3F4F6" : "#000000"
    property color secondaryColor: Theme.darkMode ? Qt.rgba(1, 1, 1, 0.35) : "#E2E8F0"

    anchors.fill: sourceItem
    visible: sourceItem !== null

    // Layer 1: Secondary Accent Layer (WHITE / Light in Light Mode)
    ColorOverlay {
        id: bgOverlay
        anchors.fill: parent
        source: root.sourceItem
        color: root.secondaryColor
        visible: root.sourceItem !== null
    }

    // Layer 2: Primary Stroke Layer (BLACK stroke in Light Mode)
    ShaderEffect {
        id: strokeOverlay
        anchors.fill: parent
        visible: root.sourceItem !== null
        property variant source: root.sourceItem
        property color glyphColor: root.primaryColor

        fragmentShader: "
            varying highp vec2 qt_TexCoord0;
            uniform lowp float qt_Opacity;
            uniform sampler2D source;
            uniform lowp vec4 glyphColor;

            void main() {
                lowp vec4 tex = texture2D(source, qt_TexCoord0);
                lowp float strokeAlpha = smoothstep(0.65, 0.95, tex.a);
                gl_FragColor = glyphColor * strokeAlpha * qt_Opacity;
            }
        "
    }
}
