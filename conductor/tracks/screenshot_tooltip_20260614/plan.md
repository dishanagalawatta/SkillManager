# Implementation Plan

## Objective
Implement a tooltip image preview for screenshot items in the main list.

## Key Files & Context
- `src/skill_manager/SkillManagerComponents/SkillItem.qml`: Displays individual skill items including screenshots in the main list.

## Implementation Steps
- [x] **Task 1.1: Add ToolTip to SkillItem for Screenshots**
  - Locate the `mouseArea` within `SkillItem.qml`.
  - Add a custom `ToolTip` component.
  - Set its `visible` property to `containsMouse && model && model.isScreenshot && model.path`.
  - Set a `delay` of `400` milliseconds.
  - Define `contentItem` as an `Item` wrapping an `Image`.
  - Configure the `Image` source to `model.path ? "file:///" + model.path : ""` (or handle path formatting correctly, ensuring it is a valid QUrl, usually `file:///` prefix helps or `model.path` may already work in QML if it's absolute, but in QML standard strings are fine or might need `AppController.ui_controller.getAssetUri` if not absolute. Wait, `ImageInspector.qml` uses `let p = root.skill.local_path.replace(/\\/g, "/");` and `model: root.skill.local_path ? ["file:///" + p] : []`. So we will construct it similar to that if necessary).
  - Constrain the image size (e.g., max width/height ~300).

## Verification & Testing
- [x] Run the application.
- [x] Select the 'Screenshots' category or find a screenshot item.
- [x] Hover over the screenshot item.
- [x] Verify that a preview image tooltip appears after a short delay.
- [x] Verify that the tooltip disappears when moving the mouse away.
- [x] Verify that non-screenshot items do not show this tooltip (they might have their own tooltips, ensure no interference).