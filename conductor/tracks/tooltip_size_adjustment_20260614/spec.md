# Tooltip Size Adjustment

## Description
The user reported that the tooltip can take up the entire window size if the text is very long. We need to limit the amount of text shown in both the command and skill description tooltips so that the popup window remains reasonably small.

## Architecture Constraints
- Edit `SkillItem.qml` where the tooltips are defined.
- Truncate both `model.description` and `model.bodyContent` to a reasonable character limit (e.g., 200-300 characters) and a reasonable line limit (e.g., 5 lines) before passing it to the `Text` component.
- The `Text` component can also use `maximumLineCount` and `elide: Text.ElideRight` for safety, though manual string truncation with `...` often feels better for preview text since QML's `elide` on multi-line wrapped text can sometimes be tricky depending on the version. Combining both is safest.

## Requirements
- Command previews should show max 5 lines, or a maximum of 250 characters, whichever comes first.
- Skill descriptions should be truncated to a max of 250 characters.
- The tooltip width should remain constrained (e.g., max 400).
- The `maximumLineCount` should be set on the `Text` item as a failsafe.