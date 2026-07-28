"""
Final verification: test body_content in BOTH Library and QuickCopy views.
"""

import os
import sys
import time

os.environ["QML_DISABLE_DISK_CACHE"] = "1"
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["INSPECTOR_DEBUG"] = "1"

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle

QQuickStyle.setStyle("Basic")
fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)
app = QGuiApplication(sys.argv)
app.setApplicationName("SkillManager")

from skill_manager.app import AppController

controller = AppController()
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge

font_bridge = FontDatabaseBridge()
qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)

engine = QQmlApplicationEngine()
controller._qml_engine = engine
from skill_manager.core.resources import qml_components_dir

qml_dir = qml_components_dir(package_file="src/skill_manager/app.py")
engine.addImportPath(str(qml_dir.parent))
engine.load(str(qml_dir / "Main.qml"))

window = next((o for o in engine.rootObjects() if hasattr(o, "show")), None)
if window:
    window.show()
    window.raise_()
    window.requestActivate()

T0 = time.monotonic()
passed, failed = 0, 0


def log(msg):
    print(f"[+{time.monotonic() - T0:.1f}s] {msg}", flush=True)


def check_qmap(label):
    sel = controller.selectedSkill
    if sel and sel.local_path:
        bc = sel.body_content or ""
        name = sel.name or "?"
        print(f"  [{label}] name='{name}' body={len(bc)}ch", flush=True)
        return len(bc) > 0
    print(f"  [{label}] selectedSkill is None", flush=True)
    return False


def model_first(model_ref, label):
    m = model_ref
    if m and m.rowCount() > 0:
        sd = m.get_skill_at(0)
        if sd:
            bc = sd.get("body_content", "") or ""
            name = sd.get("name", "?")
            print(f"  [{label}] name='{name}' body={len(bc)}ch", flush=True)
            return len(bc) > 0
    print(f"  [{label}] no skills", flush=True)
    return False


VERDICT = {"passed": 0, "failed": 0}


def assert_body(label, condition):
    if condition:
        print(f"  ✅ {label}: PASS", flush=True)
        VERDICT["passed"] += 1
    else:
        print(f"  ❌ {label}: FAIL", flush=True)
        VERDICT["failed"] += 1


def run():
    log("=== STEP 1: Wait for initial data (8s) ===")
    QTimer.singleShot(8000, step2)


def step2():
    log("=== STEP 2: Check models after init ===")
    lm = controller.libraryModel
    qcm = controller.quickCopyModel
    log(f"Library: {lm.rowCount()} skills, QuickCopy: {qcm.rowCount()} skills")

    # Switch to QuickCopy, select first skill
    log("=== STEP 3: QuickCopy view ===")
    controller.ui_controller.currentView = "QuickCopy"

    def select_qc():
        if qcm.rowCount() > 0:
            sd = qcm.get_skill_at(0)
            bc = sd.get("body_content", "") or ""
            log(f"QC MODEL[0] body before select: {len(bc)}ch")
            controller.ui_controller.selectSkill(0)
            QTimer.singleShot(500, check_qc_after)
        else:
            log("QC model empty!")
            app.quit()

    def check_qc_after():
        has = check_qmap("QC-POST-SELECT")
        assert_body("QC: body_content present after selectSkill", has)
        # Now Library view
        log("=== STEP 4: Library view ===")
        controller.ui_controller.currentView = "Library"
        QTimer.singleShot(1000, select_lib)

    def select_lib():
        if lm.rowCount() > 0:
            controller.ui_controller.selectSkill(0)
            QTimer.singleShot(500, check_lib_after)
        else:
            log("Library model empty!")
            app.quit()

    def check_lib_after():
        has = check_qmap("LIB-POST-SELECT")
        assert_body("LIB: body_content present after selectSkill", has)

        # Final verdict
        print(f"\n{'=' * 60}", flush=True)
        if VERDICT["failed"] == 0:
            print(f"✅ ALL {VERDICT['passed']}/{VERDICT['passed']} TESTS PASSED", flush=True)
        else:
            print(
                f"❌ {VERDICT['failed']} FAILURES out of {VERDICT['passed'] + VERDICT['failed']} TESTS",
                flush=True,
            )
        print(f"{'=' * 60}\n", flush=True)
        app.quit()

    QTimer.singleShot(500, select_qc)


QTimer.singleShot(500, run)
log("Starting...")
app.exec()
log("Done.")
os._exit(0)
