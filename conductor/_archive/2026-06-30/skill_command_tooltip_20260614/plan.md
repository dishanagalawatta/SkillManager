# Implementation Plan

## Objective
Implement a tooltip text preview for skill and command items in the main list.

## Key Files & Context
- `src/skill_manager/SkillManagerComponents/SkillItem.qml`: Displays individual skill items including screenshots, commands, and skills in the main list.

## Implementation Steps
- [x] **Task 1.1: Add Text ToolTip to SkillItem**
  - Add a custom `ToolTip` component named `textPreviewTooltip` to the `mouseArea` in `SkillItem.qml`.
  - Add logic to determine `previewText`:
    - For commands (`model.isCommand`), extract up to 10 lines of `model.bodyContent`.
    - For standard skills, return `model.description`.
  - Set `visible: mouseArea.containsMouse && previewText.length > 0`.
  - Set a `delay` of `450` milliseconds.
  - Set `contentWidth: Math.min(textItem.implicitWidth, 400)` to constrain the width.
  - Use a `Text` element for `contentItem` with `wrapMode: Text.Wrap` and font family logic to switch to monospace for commands.

## Verification & Testing
- [x] Run the application.
- [x] Hover over a skill item and verify the description appears in a tooltip.
- [x] Hover over a command item and verify the script code appears in a tooltip with a monospace font.
- [x] Verify text wrapping behaves correctly and doesn't exceed reasonable width.
- [x] Check that screenshot items still show the image tooltip correctly and no overlapping tooltips occur.