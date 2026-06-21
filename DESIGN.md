# SkillManager — Design System

> "Solid Matte & Liquid Glass" — frozen design contract for the
> PySide6/QML shell. The full historical rationale lives in
> [`ADR_INDEX.md`](ADR_INDEX.md).

## 1. Scope

- Applies to the QML shell under `src/skill_manager/SkillManagerComponents/`.
- Does not govern the Python core under `src/skill_manager/core/`.
- Style is the only `DESIGN.md` in this repository.

## 2. Layers

| Layer | Purpose | Visual Treatment |
|-------|---------|------------------|
| L0 Window | Foundation | Solid Matte `#121214` (dark) / `#F5F7F9` (light). |
| L1 Functional | Navigation | High-opacity frosted glass. 12 px radius. |
| L2 Segmented | Content panels | Floating frosted glass pills. |
| L3 Floating | Popovers, toasts | High-translucency, high-elevation. |

## 3. Tokens

See [`src/skill_manager/SkillManagerComponents/Theme.qml`](src/skill_manager/SkillManagerComponents/Theme.qml) for the authoritative QML token map. The table below is the *contract*; the QML file is the *implementation*.

| Token | Dark | Light | Use |
|-------|------|-------|-----|
| `--app-bg` | `#121214` | `#F5F7F9` | Window background. |
| `--glass-pill` | `#1E1E22` | `#FFFFFF` | L2 panels. |
| `--glass-border` | `#2A2A30` | `#DDE5E1` | 1 px reflection border. |
| `--accent` | `#3B82F6` | `#059669` | Primary action. |
| `--danger` | `#EF4444` | `#DC2626` | Destructive action. |
| `--label` | `#F3F4F6` | `#111827` | Primary text. |

## 4. Geometry

- Window, L1, L2 containers: **12 px** radius (synchronised with Windows 11 `DWMWCP_ROUND`).
- Buttons: 8 px (compact) or 20 px (pill).
- Borders: 1 px solid hairline; no gradients on chrome.

## 5. Motion

- 150 ms hover/focus transitions.
- No height animations on bulk list operations.
- Honour reduced-motion by removing movement.

## 6. Accessibility

- WCAG AA contrast minimums.
- Focus visible on every interactive element.
- Reduced-transparency mode maps glass to opaque semantic surfaces.
- Increased-contrast mode strengthens borders and selection outlines.

## 7. Non-Goals

- No branding-dominant UI.
- No decorative animations that slow workflows.
- No clear (non-blurred) glass behind text-heavy controls.
- No macOS / Linux support (see ADR-0008).

## 8. Cross-references

- API: [`docs/API.md`](docs/API.md)
- ADRs: [`ADR_INDEX.md`](ADR_INDEX.md)
- Agent instructions: [`AGENTS.md`](AGENTS.md)
