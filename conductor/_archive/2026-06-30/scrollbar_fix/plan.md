# Plan - Standardize Scroll Bar Behavior Across Application

Update scroll bar behavior to show only while scrolling or interacted with, ensuring consistency across all main views.

## Approach

- Modify `src/skill_manager/SkillManagerComponents/SkillInspector.qml`, `src/skill_manager/SkillManagerComponents/views/LibraryView.qml`, and `src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml`.
- Remove `active: true` from `ScrollBar` instances.
- Ensure `policy` is set to `ScrollBar.AsNeeded` (or use default).
- For `SkillInspector.qml`, add a fade effect to the `contentItem` based on the `active` state for a smoother transition.

## Scope

- In: 
    - `src/skill_manager/SkillManagerComponents/SkillInspector.qml`
    - `src/skill_manager/SkillManagerComponents/views/LibraryView.qml`
    - `src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml`
- Out: Other components that already use default scroll behavior.

## Action Items

[ ] Update `src/skill_manager/SkillManagerComponents/SkillInspector.qml`:
    - In `rawContentScroll`, remove `active: true` from `ScrollBar.vertical`.
    - Update `contentItem` of `vScroll` to use `opacity: vScroll.active ? (vScroll.hovered ? 0.8 : 0.4) : 0`.
    - Add `Behavior on opacity { NumberAnimation { duration: 200 } }`.
[ ] Update `src/skill_manager/SkillManagerComponents/views/LibraryView.qml`:
    - In `lv_listView`, remove `active: true` from `ScrollBar.vertical`.
[ ] Update `src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml`:
    - In `qcv_skillList`, remove `active: true` from `ScrollBar.vertical`.
[ ] Verify the change by checking the QML code and ensuring it follows the requirements.

## Verification

- Static analysis of the QML files to ensure `active: true` is removed.
- Manual verification of fading/hiding behavior in the application.

## Open Questions

- Is 200ms a good duration for the fade effect? (Defaulting to this).
