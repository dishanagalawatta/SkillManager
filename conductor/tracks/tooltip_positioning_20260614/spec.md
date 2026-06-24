# Tooltip Positioning Fix

## Description
The user reported that the image and text tooltips for skills, commands, and screenshots are appearing in a fixed, default position rather than near the mouse cursor.

## Architecture Constraints
- The `ToolTip` component in QML has a default position that is not relative to the mouse when triggered via properties like `visible: mouseArea.containsMouse`.
- To attach it to the mouse cursor, we need to bind the `x` and `y` properties of the `ToolTip` to the mouse coordinates within the `MouseArea` or use a `HoverHandler`. 
- Since we already use `MouseArea` (`id: mouseArea`), we can track `mouseX` and `mouseY` to position the tooltips relative to the mouse.

## Requirements
- The screenshot and text tooltips must appear near the mouse cursor.
- The position must dynamically update or be set when the tooltip appears.
- Ensure the tooltip stays within screen bounds if possible (though QML ToolTip often handles screen bounds internally if positioned relative to the parent).