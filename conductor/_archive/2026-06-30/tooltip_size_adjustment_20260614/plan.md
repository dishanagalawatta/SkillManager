# Implementation Plan

## Objective
Limit the amount of text shown in the skill and command tooltips to prevent them from taking up the entire window.

## Key Files & Context
- `src/skill_manager/SkillManagerComponents/SkillItem.qml`

## Implementation Steps
- [x] **Task 1.1: Truncate Tooltip Text**
  - Update the `previewText` property logic in `textPreviewTooltip`.
  - For commands: Split by `\n`, slice to max 5 lines. Join, then slice the total length to a max of 250 characters. Append `...` if truncated.
  - For skills: Slice `model.description` to a max of 250 characters. Append `...` if truncated.
  - Ensure the `Text` component has `maximumLineCount: 5` and `elide: Text.ElideRight` for extra safety.

## Verification & Testing
- [x] Hover over a skill with a very long description and ensure it is truncated gracefully and the tooltip remains small.
- [x] Hover over a command with many lines or very long lines and ensure it is truncated gracefully.