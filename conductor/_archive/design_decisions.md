# Decision Log: Modern Context Menu

> Historical debug record — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Investigation

The application currently lacks a context menu for right-clicking skill items. The goal is to implement a modern, sleek, and compact context menu that aligns with the existing "Glass" aesthetic.

## Hypothesis

- Use the standard QML `Menu` and heavily style it via properties and delegates.
- Implement an "Ultra-Glass" aesthetic with heavy background blur using `FrostOverlay.qml`, transparent background colors, and subtle `Theme.glassBorder`.
- Menu items will be compact but legible: 14px text size, ~32px row height.
- Full control over menu behavior and appearance via settings: `showMenuIcons`, `compactMenu`.

## Resolution

1. **Approach: Styled `QtQuick.Controls.Menu`** — Chosen for built-in accessibility, standard behaviors (nested sub-menus), and focus management.
2. **Visual Style: "Ultra-Glass"** — Heavy background blur, transparent backgrounds, subtle borders.
3. **Layout: "Standard Compact"** — 14px text, ~32px rows (adjustable via settings).
4. **Settings Integration** — `showMenuIcons` and `compactMenu` persisted via `config_controller.py` and configurable in `SettingsView.qml`.

**Assumptions:**
- `FrostOverlay` component can be nested within a `Popup` or `Menu` background without significant visual artifacting.
- Menu actions will map to existing functions in `AppController`.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
