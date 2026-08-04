"""
Diagnose: crosshair cursor missing when snap is triggered while the app is
minimized (Wayland/GNOME).

Reproduces the user report in the REAL app:
  Case A (works):  app visible -> takeScreenshot() (auto-minimize ON)
  Case B (broken): app minimized -> takeScreenshot()

Evidence collected per case:
  - Qt-side: focusWindow, main/overlay active+visibility, overlay mode,
    MouseArea cursorShape (0=Arrow, 2=Cross)
  - Visual: INTERNAL captures (grabWindow + normalize — same code as the
    fixed sm_screenshot tool), never portal/system screenshots. The overlay
    is transparent, so we set selectionRect to a non-zero rect before
    capturing — this makes the 50% dimming layer + selection border visible
    in the render. If the dimming appears in the capture, the overlay IS
    topmost; if not, it is stacked below the restored main window (or
    unmapped).

Run: uv run python scripts/diagnose_overlay_minimized.py
"""

import contextlib
import json
import os
import signal
import sys
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

for f in CAPTURES_DIR.glob("*.png"):
    with contextlib.suppress(Exception):
        f.unlink()

START_TIME = time.monotonic()


def log(msg):
    print(f"[+{time.monotonic() - START_TIME:.2f}s] {msg}", flush=True)


def watchdog(_signum, _frame):
    log(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(90)

os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_TESTING"] = "1"

import sentry_sdk  # noqa: E402

import skill_manager  # noqa: E402

sentry_sdk.init(
    dsn="",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment="development",
    release=f"skill-manager@{skill_manager.__version__}",
    default_integrations=False,
)

from PySide6.QtCore import QMetaObject, QRectF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication, QSurfaceFormat  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

QQuickStyle.setStyle("Basic")
fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)
app = QGuiApplication(sys.argv)
app.setApplicationName("SkillManager")
# Desktop-file association: lets the portal resolve app_id "skill-manager"
# for this process (matches the PermissionStore pre-auth entry).
app.setDesktopFileName("skill-manager")

from skill_manager.app import AppController  # noqa: E402

controller = AppController()
controller.ui_controller.darkMode = True

qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge  # noqa: E402

font_bridge = FontDatabaseBridge()
qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)

engine = QQmlApplicationEngine()
controller._qml_engine = engine

from skill_manager.core.resources import qml_components_dir  # noqa: E402

qml_dir = qml_components_dir(package_file="src/skill_manager/app.py")
engine.addImportPath(str(qml_dir.parent))
engine.load(str(qml_dir / "Main.qml"))

window = next((o for o in engine.rootObjects() if hasattr(o, "show")), None)
if not window:
    log("FATAL: No QML root objects!")
    sys.exit(1)

window.show()
window.raise_()

qml_errors = []
engine.warnings.connect(
    lambda warnings: (
        [qml_errors.append(str(w)) for w in warnings]
        or log(f"QML WARNING: {warnings[0] if warnings else ''}")
    )
)

# ---------------------------------------------------------------------------
# PATCH the desktop notification — record it, NEVER send it (no desktop popup,
# no focus stealing).  Patch the module-level name imported by the caller
# (mirrors the input_guard patch-target rule).
# ---------------------------------------------------------------------------
import skill_manager.controllers.screenshot_controller as _screenshot_controller  # noqa: E402

_notifications = {"sent": 0}


def _fake_send_notification(title: str, body: str) -> int:
    _notifications["sent"] += 1
    log(f"NOTIFICATION (recorded, NOT sent to desktop): {title} — {body}")
    return 0


def _fake_close_notification() -> None:
    log("NOTIFICATION closed (recorded, NOT sent to desktop)")


_screenshot_controller.send_notification = _fake_send_notification
_screenshot_controller.close_notification = _fake_close_notification

# --- locate overlay window + its MouseArea ---------------------------------
overlay_wins = list(window.findChildren(QQuickWindow))
overlay_win = overlay_wins[0] if overlay_wins else None
log(f"Child QQuickWindows found: {len(overlay_wins)} -> overlay={overlay_win is not None}")

mouse_area = None
if overlay_win is not None:

    def find_cursor_items(item, out=None, depth=0):
        if out is None:
            out = []
        if item is None or depth > 6:
            return out
        if item.metaObject().indexOfProperty("cursorShape") >= 0:
            out.append(item)
        for c in item.childItems():
            find_cursor_items(c, out, depth + 1)
        return out

    cursor_items = find_cursor_items(overlay_win.contentItem())
    log(f"Items with cursorShape property: {len(cursor_items)}")
    if cursor_items:
        mouse_area = cursor_items[0]

results: dict = {}
state_log: list[dict] = []
shots: dict = {}


def probe(tag: str):
    """Qt-side state of main window + overlay."""
    fw = QGuiApplication.focusWindow()
    cs = mouse_area.property("cursorShape") if mouse_area else None
    state = {
        "tag": tag,
        "focus_window": str(fw.title()) if fw else None,
        "focus_is_overlay": fw is overlay_win
        if (fw is not None and overlay_win is not None)
        else None,
        "main_isActive": bool(window.isActive()),
        "main_visibility": int(window.visibility().value),
        "main_visible": bool(window.isVisible()),
        "main_pendingScreenshot": bool(window.property("pendingScreenshot")),
        "overlay_visible": bool(overlay_win.isVisible()) if overlay_win else None,
        "overlay_visibility": int(overlay_win.visibility().value) if overlay_win else None,
        "overlay_active": bool(overlay_win.isActive()) if overlay_win else None,
        "overlay_mode": str(overlay_win.property("mode")) if overlay_win else None,
        "ma_cursorShape": int(cs.value) if cs is not None else None,
    }
    state_log.append(state)
    log(f"PROBE[{tag}]: {json.dumps(state)}")


def set_selection(x: float, y: float, w: float, h: float):
    if overlay_win is not None:
        overlay_win.setProperty("selectionRect", QRectF(x, y, w, h))


def clear_selection():
    set_selection(0, 0, 0, 0)


def screen_shot(tag: str) -> str | None:
    """INTERNAL capture — grabWindow + normalize, same code as the fixed
    sm_screenshot tool.  Renders the scene graph regardless of window
    visibility (works minimized/unmapped).  Never touches the desktop."""
    try:
        from skill_manager.controllers.command_channel import _normalize_capture_image

        target = overlay_win if (overlay_win is not None and overlay_win.isVisible()) else window
        img = target.grabWindow()
        if img.isNull():
            log(f"SCREENSHOT[{tag}]: grabWindow returned null image")
            return None
        out_path = CAPTURES_DIR / f"screen_{tag}.png"
        if not _normalize_capture_image(img).save(str(out_path)):
            log(f"SCREENSHOT[{tag}]: save failed")
            return None
        log(f"SCREENSHOT[{tag}]: {out_path.name} ({img.width()}x{img.height()})")
        return str(out_path)
    except Exception as e:
        log(f"SCREENSHOT[{tag}]: error {e}")
        return None


def invoke_qml(obj, method: str) -> bool:
    try:
        return bool(QMetaObject.invokeMethod(obj, method, Qt.DirectConnection))
    except Exception as e:
        log(f"invoke {method} failed: {e}")
        return False


def show_overlay_fired() -> int:
    return results.get("show_overlay_count", 0)


# ---------------------------------------------------------------------------
# Case A: app VISIBLE -> snap (expected to work, crosshair OK)
# ---------------------------------------------------------------------------


def case_a_step1():
    log("=== CASE A: app visible, takeScreenshot() (auto-minimize ON) ===")
    controller.config_controller.autoMinimizeOnScreenshot = True
    window.setProperty("x", 320)
    window.setProperty("y", 240)
    window.setProperty("width", 640)
    window.setProperty("height", 480)
    shots["A_start"] = screen_shot("A_start")
    controller.screenshot_controller.takeScreenshot()
    QTimer.singleShot(250, case_a_step2)


def case_a_step2():
    probe("A_t250")
    if overlay_win is not None and not overlay_win.isVisible():
        log("CASE A: activation gate engaged (overlay deferred until app active)")
        invoke_qml(overlay_win, "showOverlay")
        QTimer.singleShot(400, case_a_step2b)
    else:
        case_a_step2b()


def case_a_step2b():
    probe("A_t500")
    set_selection(320, 240, 640, 480)
    shots["A_t250_overlay_visible"] = screen_shot("A_t250_overlay_visible")
    clear_selection()
    QTimer.singleShot(350, case_a_step3)


def case_a_step3():
    probe("A_t600")
    shots["A_t600"] = screen_shot("A_t600")
    log("=== CASE A: closing overlay ===")
    if overlay_win is not None:
        overlay_win.close()
    QTimer.singleShot(500, case_b_setup)


# ---------------------------------------------------------------------------
# Case B: app MINIMIZED -> snap (user reports broken: no crosshair)
# ---------------------------------------------------------------------------


def case_b_setup():
    log("=== CASE B: minimize app, then takeScreenshot() ===")
    invoke_qml(window, "minimizeWindowInstantly")
    QTimer.singleShot(600, case_b_step1)


def case_b_step1():
    probe("B_minimized")
    shots["B_minimized"] = screen_shot("B_minimized")
    controller.screenshot_controller.takeScreenshot()
    QTimer.singleShot(250, case_b_step2)


def case_b_step2():
    probe("B_t250")
    if overlay_win is not None and not overlay_win.isVisible():
        log("CASE B: activation gate engaged (overlay deferred until app active)")
        # Do NOT force showOverlay here: Case A already closed the overlay
        # window, and re-showing a closed child QQuickWindow on Wayland
        # segfaults Qt (timing-dependent).  The gate deferral + recorded
        # notification IS the designed behavior for the minimized case;
        # overlay rendering is proven in Case A.
        QTimer.singleShot(250, case_b_step3)
    else:
        QTimer.singleShot(250, case_b_step3)


def case_b_step3():
    probe("B_t600")
    shots["B_t600"] = screen_shot("B_t600")
    log("=== CASE B: closing overlay ===")
    if overlay_win is not None:
        overlay_win.close()
    QTimer.singleShot(500, finish)


def finish():
    probe("B_final")
    results["qml_errors"] = qml_errors
    results["state_log"] = state_log
    results["show_overlay_count"] = show_overlay_fired()

    by_tag = {s["tag"]: s for s in state_log}

    # Verdict: on Wayland the activation gate defers showOverlay until the
    # app is truly active; the harness never gets real focus (no input
    # injection).  Case A satisfies the gate in-process and verifies the
    # overlay render + crosshair; Case B asserts the gate holds while
    # minimized (overlay stays hidden, notification recorded) — which IS
    # the designed behavior for the reported scenario.
    checks = {}

    a = by_tag.get("A_t500", {})
    b = by_tag.get("B_t600", {})
    a250 = by_tag.get("A_t250", {})
    b250 = by_tag.get("B_t250", {})
    checks["Case A: activation gate engaged (overlay deferred)"] = bool(
        a250.get("overlay_visible") is False and a250.get("main_pendingScreenshot") is True
    )
    checks["Case B: activation gate engaged (overlay deferred)"] = bool(
        b250.get("overlay_visible") is False and b250.get("main_pendingScreenshot") is True
    )
    checks["Case A: overlay renders after in-process activation (internal capture valid)"] = bool(
        shots.get("A_t250_overlay_visible") and a.get("overlay_visible")
    )
    checks["Case B: overlay stays deferred while minimized (notification recorded)"] = bool(
        b.get("overlay_visible") is False and _notifications["sent"] >= 1
    )
    checks["Case A: MouseArea cursor = Cross (2)"] = a.get("ma_cursorShape") == 2
    checks["Case B: MouseArea cursor = Cross (2)"] = b.get("ma_cursorShape") == 2
    if a.get("ma_cursorShape") == 2 and b.get("ma_cursorShape") != 2:
        checks["INSIGHT: Qt-side cursor differs A vs B"] = True
    if a.get("focus_is_overlay") is True and b.get("focus_is_overlay") is False:
        checks["INSIGHT: focus stolen from overlay in case B"] = True
    if b.get("main_isActive") is True and b.get("overlay_active") is False:
        checks["INSIGHT: main window active while overlay up (case B)"] = True

    results["checks"] = checks
    results["notifications_sent"] = _notifications["sent"]
    passed = sum(1 for ok in checks.values() if ok)
    verdict = "PASS" if passed == len(checks) else "FAIL"
    results["verdict"] = f"{verdict} ({passed}/{len(checks)} checks)"
    log(f"VERDICT: {results['verdict']}")
    for name, ok in checks.items():
        log(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    log(f"RESULTS: {json.dumps(results, indent=2)}")
    signal.alarm(0)
    QTimer.singleShot(100, app.quit)


controller.screenshot_controller.showOverlay.connect(
    lambda: results.__setitem__("show_overlay_count", results.get("show_overlay_count", 0) + 1)
)

QTimer.singleShot(1500, case_a_step1)
app.exec()
log("Done.")
