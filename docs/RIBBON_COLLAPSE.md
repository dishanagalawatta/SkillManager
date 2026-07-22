# Ribbon Collapse System

> **Scope**: `QuickCopyView.qml` and `TopBar.qml` — responsive ribbons that adapt to window width.

---

## 1. Collapse Phases (dynamic, NOT threshold-based)

The ribbon uses a **needs-based phase system** — items collapse only when there's physically not enough room. Phases are computed by comparing `_calcWidth(phase)` to `headerControls.width`.

| Phase | Action | Width Saved |
|-------|--------|-------------|
| **0** | All expanded | — |
| **1** | Delete + Add → overflow (`⋮` button appears where Delete was) | ~56px (delete+add) |
| **2** | Category dropdown (160px) → 36px icon | ~124px |
| **3** | Collection dropdown (160px) → 36px icon | ~124px |
| **4** | Project dropdown (160px) → 36px icon | ~124px |
| **5** | Client format logos → single dropdown button | ~4×32 - 32 = 96px (varies) |
| **6** | ToggleAll → overflow | ~24px |
| **7** | Category icon → overflow | ~36px |
| **8** | Project icon → overflow | ~36px |

### Always visible (never collapse)
- Copy button
- Cycle project switch
- Select checkbox
- Selected count badge + label
- Collection dropdown (icon-only from phase 3, never hidden)

### Overflow menu items (visible per phase)
- Delete Selected (`_collapsePhase >= 1`)
- Add Selected / Create New (`_collapsePhase >= 1`)
- Expand/Collapse All (`_collapsePhase >= 6`)
- Category cycle (`_collapsePhase >= 7`)
- Project cycle (`_collapsePhase >= 8`)

---

## 2. Width Calculation (`_calcWidth`, lines 56–106)

The function computes total width for a given phase by summing:

```
ToggleAll (24)  ... phase < 6
SelectCheck (24)  ... always
InfoGroup (dynamic)  ... when selection active
Delete (28)  ... phase < 1
Add (28)  ... phase < 1
Overflow (32)  ... phase >= 1
Collection (160/36)  ... always, icon phase >= 3
Category (160/36/0) ... phase < 7, icon phase >= 2
Project (160/36/0) ... phase < 8, icon phase >= 4
CycleProject (32)  ... always
ClientLogos (CF×32 + (CF-1)×8) ... phase < 5
ClientDropdown (32) ... phase >= 5
CopyBtn (32)  ... always
+ RowLayout spacing: (visibleCount - 1) × 8
```

### Phase selection

```qml
property int _collapsePhase: {
    var avail = headerControls.width
    // Start at 0 (most expanded) and stop at the first phase that fits
    for (var p = 0; p <= 8; p++) {
        if (_calcWidth(p) <= avail) return p
    }
    return 8  // safety fallback
}
```

Iterates from 0→8 (most→least expanded), returning the first phase that fits. Always uses exact fit — no hysteresis.

---

## 3. Ribbon Layout (left→right)

```
┌─────────────────────────────────────────────────────────────────────┐
│  headerControls  (GlassPill, radius:24, height:48)                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  qcv_headerLayout  (RowLayout, spacing:8)                     │  │
│  │                                                               │  │
│  │  [⟱] ToggleAll       ← always, hidden phase 6+                │  │
│  │  [✓] SelectCheck     ← always                                 │  │
│  │  [12 selected]       ← always when selection active           │  │
│  │  [⋮] OverflowBtn     ← phase 1+, takes Delete's slot          │  │
│  │  [🗑] Delete          ← phase 0 only                           │  │
│  │  [+⋁] Add            ← phase 0 only                           │  │
│  │  [▢] Category        ← phase <7, icon phase 2+                │  │
│  │  [▢] Collection      ← always, icon phase 3+                  │  │
│  │  [▢] Project         ← phase <8, icon phase 4+                │  │
│  │  [↺] Cycle Project   ← always                                 │  │
│  │  [spacer]                                                      │  │
│  │  [edit controls]     ← only during collection edit            │  │
│  │  [spacer]                                                      │  │
│  │  [logo1][logo2]…     ← phase <5                               │  │
│  │  [⏷ format]          ← phase 5+                               │  │
│  │  [📋 Copy]           ← always                                 │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  anchors.margins: 4, leftMargin: 16, rightMargin: 16               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Debug Overlay

`--debug-overlay` CLI flag or `sm_toggle_debug_overlay` MCP tool enables a green overlay showing live phase.

### Fields

| Code | Meaning |
|------|---------|
| `CP` | Current collapse phase (0–8) |
| `HW` | `headerControls.width` (available content width) |
| `IGW` | Info group width (badge + "selected" label) |
| `CF` | Client format count |

### Activation

```bash
uv run python -m skill_manager.__main__ --debug-overlay
```

Or via MCP:
```
sm_toggle_debug_overlay({ "enabled": true })
```

---

## 5. Key Constraints

- **No hardcoded pixel thresholds** — every collapse decision is based on `_calcWidth(avail)`.
- **Items never "jump" when there's space** — the system is purely needs-based.
- **Collection is always visible** — it collapses to icon-only but never goes to overflow.
- **Overflow `⋮` is where Delete was** — between InfoGroup and (Delete/Add), so it naturally takes Delete's slot.

---

## 6. TopBar Collapse

**Scope**: `TopBar.qml` — the top navigation bar.

Phases are independent from QuickCopyView — TopBar has its own `_topPhase` (0–3) and `_topCalcWidth()`.

| Phase | Action | Width Saved |
|-------|--------|-------------|
| **0** | All expanded (nav labels, search bar, refresh) | — |
| **1** | Search bar (300px) → search icon (28px) | ~172px |
| **2** | Nav buttons collapse to icon-only (5× icons) | ~266px (label text) |
| **3** | Refresh + Settings → overflow `⋮` (where Refresh was) | ~72px |

### Other nav buttons (Snap, QuickCopy, Library, Updates)

Always visible on nav bar — never go to overflow. At phase 2+ they become icon-only.

### Overflow menu items (phase 3 only)

- **Refresh** — `AppController.refreshSkills()`
- **Settings** — navigates to Settings view (hidden when `currentView === "Settings"`)

### Width Calculation (`_topCalcWidth`)

```
Fixed widths:
  Snap / QuickCopy / Library / Updates / Settings labels: 76 / 96 / 80 / 84 / 90
  Nav button icon-only: 40 each
  Refresh: 32
  Search icon: 28
  Overflow btn: 36
  Search input: Math.min(200, root.width * 0.3)  [phase 0 only]
  + 40 margins, 24 outer spacing, 4 nav spacing, 8 action spacing

Phase 0: nav_labels(426) + margins(40) + spacing(28) + refresh(32) + search(dynamic) + action_spacing(8)
Phase 1: nav_labels(426) + margins(40) + spacing(28) + refresh(32) + search_icon(28) + action_spacing(8)
Phase 2: nav_icons×5(200) + margins(40) + spacing(28) + refresh(32) + search_icon(28) + action_spacing(8)
Phase 3: nav_icons×4(160) + margins(40) + spacing(24) + overflow(36) + search_icon(28) + action_spacing(8)
```

### Phase selection (most expanded first)

```qml
property int _topPhase: {
    if (_topCalcWidth(0) <= root.width) return 0
    if (_topCalcWidth(1) <= root.width) return 1
    if (_topCalcWidth(2) <= root.width) return 2
    return 3
}
```

### Layout (left → right)

```
┌─────────────────────────────────────────────────────────────┐
│  RowLayout (anchors.leftMargin:20, rightMargin:20, spacing:24)  │
│                                                             │
│  Nav RowLayout (fillWidth)                                  │
│  [📷 Snap] [⚡ Quick Copy] [📚 Library] [🔄 Updates] [⚙️ Settings]  │
│  ── all visible, showLabel = phase<2                       │
│  ── Settings hidden at phase 3+                             │
│  [spacer]                                                   │
│                                                             │
│  Actions RowLayout (spacing:8)                              │
│  [🔄 Refresh]  (visible phase<3)                            │
│  [⋮ Overflow]  (visible phase>=3, where Refresh was)        │
│  [🔍 SearchInput] (visible phase<1, fillWidth, max 200px)   │
│  [🔍 SearchIcon] (visible phase>=1, 28px)                   │
└─────────────────────────────────────────────────────────────┘
```

### Key differences from QuickCopyView collapse

| Aspect | QuickCopyView | TopBar |
|--------|---------------|--------|
| Overflow position | Between InfoGroup and Delete | Replaces Refresh in actions section |
| Nav items to overflow | Multiple per phase | Only Settings at phase 3 |
| Hidden items | Yes, hidden per phase | Nav always visible (except Settings at phase 3) |
| Search | N/A | Collapses bar→icon at phase 1 |
