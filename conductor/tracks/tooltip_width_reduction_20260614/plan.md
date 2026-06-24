# Implementation Plan

## Objective
Reduce the maximum horizontal length of tooltips in `SkillItem.qml`.

## Implementation Steps
- [x] **Task 1.1: Reduce Screenshot Tooltip Width**
  - Change `implicitWidth: Math.min(400, previewImg.implicitWidth)` to `implicitWidth: Math.min(300, previewImg.implicitWidth)` in `screenshotTooltip`.
- [x] **Task 1.2: Reduce Text Tooltip Width and Truncation**
  - Update `previewText` truncation character limit from 250 to 180 for both skills and commands.
  - Change `width: Math.min(implicitWidth, 400)` to `width: Math.min(implicitWidth, 280)` in `textPreviewTooltip`.

## Verification & Testing
- [x] Verify tooltips are horizontally narrower.
- [x] Verify text still wraps correctly and is readable.