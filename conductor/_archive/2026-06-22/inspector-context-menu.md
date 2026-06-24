# Skill Inspector Context Menu Modernization

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Replace the native, unstyled Qt context menus in `SkillInspector.qml` with the application's modernized, SVG-based `GlassMenu`.

## Scope

- **In:** `src/skill_manager/SkillManagerComponents/SkillInspector.qml` (Name, Metadata, Description, Raw Content, and Quick Copy Argument text fields).
- **Out:** Other components already modernized.

## Action Items

- [ ] Add a `GlassMenu` named `inspectorContextMenu` at the root of `SkillInspector.qml` to serve as a shared context menu.
- [ ] Configure `inspectorContextMenu` with "Copy" and "Select All" actions using `copy-icon.svg`.
- [ ] Attach `TapHandler` to `rawContentArea` (Implementation Details) to trigger `inspectorContextMenu` on right-click.
- [ ] Attach `TapHandler` to the skill name `TextEdit` to trigger the menu.
- [ ] Attach `TapHandler` to the description `TextEdit` to trigger the menu.
- [ ] Attach `TapHandler` to the Quick Copy `argField` to trigger the menu.
- [ ] Attach `TapHandler` to the metadata `Repeater` `TextEdit`s to trigger the menu.

## Verification

- Right-clicking on the raw skill content displays the themed `GlassMenu`.
- "Copy" and "Select All" function correctly on the selected text.
- The native Qt menu no longer appears in the Inspector.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
