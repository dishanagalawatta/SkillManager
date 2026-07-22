# Ribbon Collapse System

> **Scope**: `QuickCopyView.qml` — the responsive ribbon that adapts to window width.

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
│  │  [▢] Collection      ← always, icon phase 3+                  │  │
│  │  [▢] Category        ← phase <7, icon phase 2+                │  │
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
