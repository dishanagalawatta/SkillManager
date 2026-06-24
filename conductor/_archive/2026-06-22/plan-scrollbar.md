# Scroll Bar Fix Implementation Plan

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Make scrollbars visible across the application, adhering to the dark theme styling.

## Scope

- **In:** Creating `AppScrollBar.qml`, modifying `SmoothListView.qml` and `SmoothScrollView.qml`, cleaning up redundant `ScrollBar.vertical` overrides in other UI views.
- **Out:** Changing the core scroll/wheel logic inside the views.

## Action Items

1. **Create `AppScrollBar.qml`**
   - Create `src/skill_manager/SkillManagerComponents/AppScrollBar.qml`.
   - Implement a custom `contentItem` and `background` utilizing `Theme.secondaryLabel`.
   - Add opacity animations for `active`, `hovered`, and `pressed` states.

2. **Update Core Scroll Components**
   - In `SmoothListView.qml`, add `ScrollBar.vertical: AppScrollBar {}`.
   - In `SmoothScrollView.qml`, add `ScrollBar.vertical: AppScrollBar {}`.

3. **Cleanup Redundant Declarations**
   - Remove explicit `ScrollBar.vertical` definitions from the following files, as they will inherit it from the `Smooth*` components:
     - `SkillInspector.qml`
     - `GlassDropdown.qml`
     - `GlassCollectionDropdown.qml`
     - `PackageEditDialog.qml`
     - `LibraryView.qml`
     - `QuickCopyView.qml`
   - *Note*: Ensure any specific policies like `ScrollBar.AlwaysOn` or `ScrollBar.AsNeeded` in these files are kept if they differ from the default `AsNeeded`.

## Verification

- Run `python run_tests.py` to confirm 0 failures and lint clean.
- Visually verify scrollbars appear when scrolling or hovering inside Library, Quick Copy, and Inspector views.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
