# Screenshot Capture & Snap-Flow Validation Report

> **Scope**: MCP `sm_screenshot` empty-capture defect, the internal capture
> fix, and the internal-tool verification harnesses for the snap flow.
> **Date**: 2026-08-01 · **Environment**: GNOME Wayland, single 1920×1080.

---

## 1. Diagnosis

### Symptom
`sm_screenshot` (MCP bridge) returned an empty/blank PNG while the live GUI
window was visible. Portal-based system screenshots also failed under the
Wayland portal (denied, wrong region in multiscreen/headless environments).

### Root Causes
1. **`CommandChannel._normalize_capture_image`** produced invalid/empty
   images — the internal capture path used by the bridge.
2. **`ScreenshotController.takeScreenshot`** captured the wrong region in
   multiscreen setups.
3. **Portal path (`utils/portal_capture.py`)** is unreliable on Wayland:
   app-id resolution fails without the desktop-file env trick, and portal
   screenshots grab the wrong region in headless/multiscreen environments.
4. **System-level screenshot verification** (portal subprocess) steals
   focus/raises windows on the user's live desktop — the exact UX failure
   reported ("i clickd something and losed the focus to app").

## 2. Implementation

| File | Change |
|------|--------|
| `src/skill_manager/controllers/command_channel.py` | Fixed `_normalize_capture_image()` (line 23) — internal window-only capture |
| `src/skill_manager/controllers/screenshot_controller.py` | Fixed `takeScreenshot()` capture region (line 295); notification signals `notifyCapturePending`/`notifyCaptureActivation` |
| `src/skill_manager/mcp/bridge/_capture.py` | Uses the fixed internal capture path |
| `src/skill_manager/utils/notifications.py` | D-Bus capture-pending notification (enabled only outside pytest/offscreen) |
| `src/skill_manager/utils/portal_capture.py` | Portal path retained for read-only fallback only |

**Design constraint honored**: verification must NEVER touch the desktop —
no portal subprocess, no window raise, no input injection, no real desktop
notification. All verification now renders via `QQuickWindow::grabWindow()`
+ `_normalize_capture_image()` (the exact code the fixed `sm_screenshot`
uses), which works even while the window is minimized/unmapped.

## 3. Testing

### 3.1 Automated (pytest)
- `tests/test_mcp_screenshot.py` — MCP capture contract
- `tests/test_screenshot_feature.py` — screenshot controller logic
- `tests/test_notifications.py` — notification enablement guard
- `tests/ui/test_ui_auto_minimize_snap.py` — snap-flow unit contract

Result: **62 passed**; `ruff check` + `ruff format` clean on `src tests`.

### 3.2 Live-app verification — internal tool only
`scripts/verify_auto_minimize_snap.py` — **PASS 15/15** (4 consecutive runs):

- Experiment A (minimize state machine): hiding flag set on
  `minimizeWindowInstantly()`, cleared on restore; opacity untouched (no
  opacity hack); internal renders valid **while minimized** and after restore.
- Experiment B (real Snap-button click): `minimizeRequested` emitted,
  `pendingScreenshot` set, `showOverlay` emitted, activation gate engaged
  (overlay deferred until app active — the designed behavior on Wayland),
  overlay renders via internal capture (dimming layer + selection border
  visible), overlay cursor = Cross (2), capture-pending notification
  **recorded, never sent to desktop**, state cleared after cancel.
- QML errors: **none**.

`scripts/diagnose_overlay_minimized.py` — **PASS 6/6** (converted from
portal captures to the internal tool):

- Case A (visible): gate engaged → in-process activation → overlay renders +
  Cross cursor.
- Case B (minimized): gate engaged, overlay **stays deferred** while
  minimized (notification recorded) — the designed behavior for the reported
  scenario; Cross cursor property intact in both cases.

### 3.3 Visual evidence (mandatory rule #6)
Captures in `/tmp/opencode/evidence/` (42 files) + `data/mcp/captures/`
(cleaned after each run). `look_at` confirmed:

- `internal_A_while_minimized.png` — full UI renders correctly while
  minimized (no clipping).
- `internal_B_overlay.png` / `screen_A_t250_overlay_visible.png` /
  `screen_B_t250_overlay_visible.png` — full-screen dimming layer + cyan
  selection border visible in both cases.

Note: the crosshair cursor itself is compositor-drawn and never appears in
a scene-graph render; the Qt-side `cursorShape == 2` (Cross) property is the
correct verification.

## 4. Validation Findings

1. **Capture fix proven end-to-end**: fresh `sm_screenshot` returns a valid
   835×700 RGBA image (evidence `16fca99c…png`).
2. **Wayland activation gate is the correct behavior**: when the app is not
   truly active, `showOverlay()` is deferred until activation (the
   notification is the user-facing trigger). The harness asserts the gate as
   expected behavior rather than forcing the overlay.
3. **Harness crash workarounds** (documented in scripts):
   - `restoreWindowState()` + `showOverlay()` races two `requestActivate`
     calls on Wayland → Qt segfault.
   - Re-showing a closed child `QQuickWindow` (overlay) segfaults Qt —
     overlay rendering is proven once (Case A / verify Exp B).
4. **No source behavior change** in the snap feature (`Main.qml`,
   `ScreenshotOverlay.qml` untouched by verification work).

## 5. Artifacts

| Artifact | Location |
|----------|----------|
| Verify harness | `scripts/verify_auto_minimize_snap.py` |
| Diagnose harness | `scripts/diagnose_overlay_minimized.py` |
| Evidence (backed up) | `/tmp/opencode/evidence/` |
| Run logs | `/tmp/opencode/verify_stab{1,2}.log`, `/tmp/opencode/diagnose_stab{1,2}.log` |
| Live-capture proof | `/tmp/opencode/sm5_mcp.png` (835×700 RGBA) |
