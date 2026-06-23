import QtQuick
import Qt5Compat.GraphicalEffects

// Re-export Qt5Compat.GraphicalEffects.ColorOverlay under the same API
// (anchors.fill + source + color) that the rest of the UI uses.
//
// Qt5Compat.GraphicalEffects.ColorOverlay replaces the source's pixel colour
// with `color` while preserving the source's alpha channel — i.e. it
// recolours an SVG icon (whose strokes are `currentColor`) to any target
// colour without modifying the source, without re-rendering the icon at a
// different resolution, and without depending on the source's intrinsic
// luminance. This is the exact behaviour the UI relied on before the
// Qt5Compat imports were removed from the call sites.
ColorOverlay {
    id: root

    property alias source: root.source
    property alias color: root.color
}
