# Plan - Fix Scroll Animations

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

The E2E UI tests are failing because `SmoothScrollView` uses `Behavior on contentItem.contentY`. In QML, `ScrollView.contentItem` is statically typed as an `Item`, which does not have a `contentY` property, causing a binding error that breaks the whole component and cascading into other views failing to load.

## Scope

- **In:** `SmoothScrollView.qml`, `SmoothListView.qml`.
- **Out:** Other UI views.

## Action Items

- [ ] Update `SmoothScrollView.qml`: Remove `Behavior on contentItem.contentY`. Replace with a standalone `NumberAnimation` targeting `root.contentItem` and `property: "contentY"`. Trigger this manually in `onWheel`.
- [ ] Update `SmoothListView.qml`: Do the same for consistency. Remove `Behavior on contentY`, use a standalone `NumberAnimation` targeting `root` and `property: "contentY"`. Trigger manually in `onWheel`.
- [ ] Run tests to verify the QML errors are gone and E2E flows pass.

## Verification

- Run `python run_tests.py` to confirm 0 failures and lint clean.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
