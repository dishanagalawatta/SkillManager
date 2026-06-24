# Implementation Plan

## Objective
Fix the positioning of the screenshot and text tooltips in `SkillItem.qml` so they appear near the mouse cursor.

## Key Files & Context
- `src/skill_manager/SkillManagerComponents/SkillItem.qml`: Contains the `ToolTip` instances for screenshots and text previews.

## Implementation Steps
- [x] **Task 1.1: Track Mouse Position**
  - Ensure `hoverEnabled: true` is on the `mouseArea` (it already is).
- [x] **Task 1.2: Bind ToolTip Position**
  - Add `x: mouseArea.mouseX + 15` and `y: mouseArea.mouseY + 15` to both `screenshotTooltip` and `textPreviewTooltip` to position them near the cursor with a slight offset.
  - Alternatively, if QML requires global positioning, we might need to map to global coordinates. However, `ToolTip` is usually positioned relative to its parent item. Setting `x` and `y` relative to `mouseArea`'s coordinates should work.
  - Wait, QML `ToolTip` properties `x` and `y` are relative to the parent item of the ToolTip. Since `ToolTip` is a child of `MouseArea`, `mouseX` and `mouseY` are relative to the `MouseArea`. So setting `x: mouseX + 15` and `y: mouseY + 15` should position it relative to the mouse.

## Verification & Testing
- [x] Run the application.
- [x] Hover over a skill item and verify the tooltip appears near the mouse cursor.
- [x] Hover over a screenshot item and verify the tooltip appears near the mouse cursor.
- [x] Move the mouse around within the item and verify the tooltip follows the mouse or appears where the mouse initially hovered (if position binding updates continuously, it will follow. If we only want it near where it triggered, continuous binding is fine).