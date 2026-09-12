# ADR-0034: Keyboard-Operable List Reorder in ProjectReorderDialog

> Status: **Accepted**
> Date: 2026-09-12
> Owner: @DIKKA

## Context

`ProjectReorderDialog` offered drag-and-drop as the only reorder path:
a `MouseArea` drag handle with no `activeFocusOnTab`, no `Keys` handling,
and no `Accessible` metadata. Keyboard and screen-reader users could not
change project order at all. The codebase-wide a11y consolidation (PRs
#278/#280, ADR-0031) explicitly deferred this surface pending a dedicated
design, since reorder is neither a toggle (CheckBox) nor a momentary
button — it is a positional operation on list items.

## Decision

1. **One focus stop per row**: the delegate root `Item` gets
   `activeFocusOnTab: true`, replacing mouse-only interaction.
2. **Move gestures**: `Alt+Up` / `Alt+Down` (with `Ctrl` accepted as an
   alias) move the focused row one position; plain arrows keep native
   `ListView` navigation (`event.accepted = false` otherwise). Boundary
   moves are no-ops, never wraps.
3. **Reuse the drag slot**: keyboard moves call the same
   `AppController.reorderProjects(from, to)` via `Qt.callLater` (deferred
   because the call rebuilds delegates mid-script, same hazard the drag
   path documents).
4. **Focus retention**: `pendingFocusIndex` records the destination;
   the rebuilt delegate with the matching index reclaims focus in
   `Component.onCompleted`, so AT users hear the new position.
5. **AT naming**: `Accessible.ListItem` with
   `"<label>, <i> of <n>. Press Alt Up or Alt Down to move."`
   `Accessible.onIncreaseAction`/`onDecreaseAction` were rejected: Qt
   scopes them to value widgets (sliders, spin boxes, dials), and using
   them on a list item would advertise unverified semantics.
6. **Focus visibility**: the row border binds to
   `delegateWrapper.activeFocus` (accent, width 2), sharing the existing
   drag-highlight channel; mouse press also moves focus to the row.
7. **Programmatic hook**: `focusRow(idx)` helper on the dialog root for
   services/tests that cannot inject key events.
8. **Observability**: `reorderProjects` logs moves at info and ignored
   no-ops at debug under `[PROJECTS]`.

## Consequences

### Positive

- Full keyboard parity with drag reorder; screen readers announce
  position and the exact move gesture per row.
- Zero layout change: no new buttons, no delegate resize; verified via
  real-app screenshots (focused + post-move states, no clipping).
- Contract tests pin the bindings so a drag-only regression fails fast.

### Negative

- One extra Tab stop per project row (consistent with other dialogs'
  per-row controls).
- `focusRow(idx)` is a small test/service seam on production QML.

### Neutral

- No model, persistence, or API changes: same slot, same bounds checks.
- `GlassMultiSelect` row-background clicks remain mouse-only by design
  (inner checkbox is the single keyboard stop); same pattern applies.

## Alternatives Considered

### Visible move up/down buttons per row

Rejected: adds layout churn and per-row chrome for an infrequent action;
keyboard + AT coverage achieves parity without visual cost.

### `Accessible.onIncreaseAction`/`onDecreaseAction` for moves

Rejected: Qt documents these for value-type roles; advertising them on
`ListItem` risks incorrect AT behavior. Revisit if Qt clarifies support.

## References

- ADR-0031 (role matrix and keyboard contract)
- Qt 6 `qml-qtquick-accessible`, `accessible-qtquick` docs
- `tests/qml/test_qml_reorder_keyboard_contract.py`
- `scripts/verify_reorder_keyboard_dialog.py` (+ captures)
