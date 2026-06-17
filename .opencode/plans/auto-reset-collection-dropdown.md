# Plan: Auto-Reset Collection Dropdown on Manual Selection Change

## Problem
When user applies a collection (e.g., "TestFixing") and then manually toggles items, the dropdown still shows "TestFixing" — misleading because the selection no longer matches.

## Solution
Add a `Connections` block in `QuickCopyView.qml` that listens to `quickCopyModel.selectionStateChanged`. When fired:
1. If `_isInternalSelectionChange` is true → ignore (programmatic change)
2. If `qcv_collectionDrop.currentIndex === 0` → ignore (already at "All Collections")
3. Otherwise → set `qcv_collectionDrop.currentIndex = 0` and reset view_filter

## File Change

**File**: `src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml`

**Location**: After `Component.onCompleted` block (after line 31)

**Add**:
```qml
Connections {
    target: AppController.quickCopyModel
    function onSelectionStateChanged() {
        if (qcv_root._isInternalSelectionChange) return
        if (qcv_collectionDrop.currentIndex === 0) return
        qcv_collectionDrop.currentIndex = 0
        AppController.ui_controller.setViewFilterForView("QuickCopy", "collection", "")
    }
}
```

## How It Works

| Scenario | `_isInternalSelectionChange` | `currentIndex` | Result |
|---|---|---|---|
| User clicks item (`toggleSelection`) | false | != 0 | **Reset** ✓ |
| User clicks checkbox (`setSelected`) | false | != 0 | **Reset** ✓ |
| User clicks "select all" (`selectAll`) | false | != 0 | **Reset** ✓ |
| User clicks "clear all" checkbox | false | != 0 | **Reset** ✓ |
| Collection applied (`applyCollectionSelection`) | true | any | **Ignored** ✓ |
| "All Collections" selected (`clearSelection`) | true | any | **Ignored** ✓ |
| Project switch | N/A | N/A | **Ignored** ✓ (fires `selectionDataChanged`, not `selectionStateChanged`) |

## Edge Cases

- **Toggle same item twice**: First click removes → diverges → reset. Second click re-adds → already at "All Collections". Selection returns to collection state but dropdown shows "All Collections" — acceptable, user explicitly interacted.
- **Project switch after collection apply**: `selectionDataChanged` fires (not `selectionStateChanged`) → dropdown stays. Correct — project switch doesn't invalidate the collection.
- **Delete skills after collection apply**: `selectionStateChanged` fires → reset. Correct — deletion is a divergence.

## No Python Changes Needed

The fix is purely QML-side. No changes to the model, controller, or tests.

## Validation (manual)
1. Apply collection → dropdown shows collection name ✓
2. Click an item → dropdown resets to "All Collections" ✓
3. Apply collection → click "select all" → dropdown resets ✓
4. Apply collection → switch project → dropdown stays ✓
