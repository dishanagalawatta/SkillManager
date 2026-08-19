# Plan - Fix UI Lag and Scrollbar Visibility

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

The recent changes to scrolling mechanics (additive WheelHandler) and scrollbar styling (0.0 inactive opacity) have caused UI jitter, lag, and poor visibility. This plan restores performance by correctly intercepting wheel events when a multiplier is present and restores visibility by increasing the minimum scrollbar opacity.

## Scope

- **In:** `AppScrollBar.qml`, `SmoothListView.qml`, `SmoothScrollView.qml`.
- **Out:** Core logic or view models.

## Action Items

- [ ] 1. Update `AppScrollBar.qml`: Increase inactive opacity from `0.0` to `0.3` to ensure it's "visible as previous" but still distinct from the active state. Remove redundant `import "."`.
- [ ] 2. Update `SmoothListView.qml`: Modify `WheelHandler` to `event.accepted = true` when `multiplier !== 1.0`. This prevents fighting with the native scroll engine, eliminating lag.
- [ ] 3. Update `SmoothListView.qml`: Add a `SmoothedAnimation` on `contentY` to maintain a fluid feel even when manually scrolling with the multiplier.
- [ ] 4. Update `SmoothScrollView.qml`: Apply identical `WheelHandler` and `SmoothedAnimation` logic to `contentItem.contentY`.
- [ ] 5. Run QML quality tests to ensure the UI contract is still met.
- [ ] 6. (Optional) Run UI E2E tests if available to verify navigation.

## Verification

- Run `python run_tests.py` to confirm 0 failures and lint clean.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
