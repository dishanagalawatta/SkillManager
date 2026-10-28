# ADR-0047: Common Side-Panel Shell

> Status: **Accepted**
> Date: 2026-10-28
> Owner: @DIKKA

## Context

The app grew two unrelated right-hand panel designs.

The inspector panels (`SkillInspectorOverlay.qml`) float over the content,
anchor to the right edge below the ribbon, expose a left-edge drag grip, clamp
their width, remember the user's width in `UIStateRecord.inspectorWidth`, and
carry a close button. The Quick Copy task list (`views/ProjectTasksPanel.qml`)
was instead an inline `RowLayout` child of `QuickCopyView.qml` with a fixed
340 px width: no grip, no persistence, no close affordance, and different
insets. Two panels occupying the same screen edge felt like two applications.

The duplication was structural, not cosmetic: the resize gesture, the width
clamp, the debounced persistence timer and the header layout each existed in
exactly one of the two panels, so any new panel would either copy one of them
or invent a third behaviour.

## Decision

Introduce **`SidePanel.qml`** as the single shell for every right-anchored
panel, and let hosts supply only the body.

- The shell owns the matte surface (`Theme.glassPill` + `glassBorder`,
  16 px insets, `Theme.radiusCard`), the header (title, optional counter
  `badgeText` pill, close button), the open/close fade (suppressed under
  `reducedMotion`), width clamping (85 % of the host, `minimumPanelWidth`
  floor) and persistence.
- The body is the **default property**, wired as
  `default property alias content: body.data`. Consumers declare children and
  they land inside the body `ColumnLayout`; the shell's own declarations stay
  root children, so the alias does not capture the surface.
- Width persistence is generic: `SidePanel.widthKey` (for example
  `"quickcopy.tasks"`) plus `UIController.getPanelWidth(key)` /
  `setPanelWidth(key, width)`, stored in the new
  `UIStateRecord.panel_widths` map. `inspectorWidth` remains for the
  inspector's existing key so no user setting is lost.
- The drag gesture is extracted into **`PanelResizeHandle.qml`**
  (`widthEdited` / `widthCommitted`), now shared by `SidePanel` and
  `SkillInspectorOverlay`. The shell never mutates persisted state directly;
  the host or shell persists after a debounce.
- The shell reports `closeRequested` and never writes the open state itself —
  the owner stays the single source of truth. `Esc` remains owned by
  `Main.qml`.
- Reusable body parts are extracted rather than inlined: `SegmentedFilter.qml`
  for pill tab strips and `TaskItem.qml` for the task row.

## Consequences

### Positive

- One place to change panel chrome: a new panel is a `SidePanel` plus content,
  and automatically inherits resize, clamp, persistence, reduced-motion and
  accessibility behaviour.
- The task panel reaches parity with the inspectors (overlay placement, grip,
  remembered width, close button) without duplicating ~120 lines of gesture
  and persistence code.
- `ProjectTasksPanel.qml` dropped from 521 to ~250 lines and now composes
  instead of owning layout math.
- Contract tests (`tests/qml/test_qml_side_panel_contract.py`) pin the shell's
  invariants, so a future panel cannot fork them silently.

### Negative

- One more indirection for anyone reading a panel: the chrome lives in
  `SidePanel.qml`, not in the panel file.
- `SidePanel` assumes an overlay host that fills the viewport; placing it
  inline requires the host to provide that geometry.
- The default-property alias is subtle — adding a non-body declaration to the
  root of a `SidePanel` consumer would be captured as content if written after
  the body.

### Neutral

- Inspector width keeps its existing key/record; only new panels use
  `panel_widths`.
- The shell does not implement keyboard focus trapping or a shortcut; those
  stay with `Main.qml` and `QuickCopyView.qml` respectively.

## Alternatives Considered

### Keep the panels separate and copy the inspector behaviour into the task panel

Fastest to write, and rejected: it duplicates the gesture, clamp and debounce
logic in a second file, which is exactly the drift this ADR removes. A third
panel would make it worse.

### Put the shell in Python (a `QQuickWidget`/registered `QObject` wrapper)

Rejected: the shared parts are pure QML layout and gestures. A Python
wrapper would move declarative layout into imperative code and break the
existing QML contract tests, which read the `.qml` sources directly.

### Make `SkillInspectorOverlay` the base class and specialise it

Rejected: the inspector is a domain component (skill / command / image
variants, preview loading, star action). Inheriting from it would drag
inspector-specific state into the task list and couple unrelated features.

## References

- `src/skill_manager/SkillManagerComponents/SidePanel.qml`
- `src/skill_manager/SkillManagerComponents/PanelResizeHandle.qml`
- `docs/ARCHITECTURE.md` — Per-Project Task List
- `DESIGN.md` — Side Panels
- [ADR-0031](ADR-0031-qml-accessibility-role-matrix.md) — accessibility role matrix
