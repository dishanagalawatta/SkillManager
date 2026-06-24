# Systematic Debugging: Scroll Lag and Visibility (Update)

> Historical debug record — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Investigation

- **Scroll Bar Visibility:** Auto-hide works when `opacity` falls back to `0.0`. But maybe it is too eager to hide? Or maybe it's not visible enough when it does appear? The user says "Scroll bar not visible as previous". The original `AppScrollBar` had `implicitWidth: 6` but we set `background: Item { implicitWidth: 6 }` and removed it from `contentItem`. Let's ensure the `contentItem` still has `implicitWidth` and `radius`.
- **Scrolling Lag:** The `NumberAnimation` approach inside the `WheelHandler` is causing lag. Why?
    - `contentY` bindings and layout updates in `ListView` can be heavy. Animating them directly via `NumberAnimation` on every wheel event might be causing the QML engine to thrash.
    - Also, `Math.max(root.originY, ...)` logic limits `contentY`.
    - If the user scrolls fast, we rapidly `stop()` and `start()` the animation, which feels like stuttering or lag.
    - Native `Flickable` handles scrolling efficiently. By using `event.accepted = true`, we completely bypass the native physics engine.

## Hypothesis

1.  **Visibility Hypothesis**: The scrollbar is not visible because `0.0` makes it completely invisible when not actively scrolling. Users often prefer a *slight* visual indicator of the scrollbar track even when inactive, or at least it should be highly visible when they start scrolling. My previous fix changed `0.3` to `0.0`. Let's change it to something very subtle like `0.1` so it's not completely invisible but doesn't dominate, or ensure the active state triggers correctly.
2.  **Lag Hypothesis**: The `NumberAnimation` restarting on every wheel tick causes stuttering. Instead of a manual animation, we can leverage the built-in `Flickable` methods. To adjust scroll speed *without* breaking native smoothing, we can intercept the wheel event, let it remain *unaccepted* so the native handler catches it, but we *modify* the event data? No, we can't modify the event in QML.
    - **Better Alternative Approach**: Use Qt's built in `flick()` method to impart velocity instead of directly setting `contentY`.
      `root.flick(0, event.angleDelta.y * multiplier * some_factor)`
      This relies entirely on the native C++ physics engine for smoothing and bounds checking!

Let's test the `flick()` hypothesis.

## Resolution

_(No resolution block in original — investigation only.)_

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
