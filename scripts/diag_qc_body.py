"""
Diagnose blank body_content in QuickCopy inspector.
Traces: model body_content → selectedSkill QMap → QML rendering.
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


def log(msg):
    print(f"[+{time.monotonic() - T0:.1f}s] {msg}", flush=True)


def qmap_state(label):
    sel = controller.selectedSkill
    if sel and sel.local_path:
        bc = sel.body_content or ""
        desc = sel.description or ""
        name = sel.name or "?"
        lp = sel.local_path or ""
        print(
            f"  QMAP ['{label}']: name='{name}' body={len(bc)}ch desc={len(desc)}ch path={lp}",
            flush=True,
        )
        return name, bc, desc, lp
    print(f"  QMAP ['{label}']: None", flush=True)
    return None, "", "", ""


def model_first(model_ref, label):
    """Get first skill from model, log body_content state."""
    m = model_ref
    if m and m.rowCount() > 0:
        sd = m.get_skill_at(0)
        if sd:
            bc = sd.get("body_content", "") or ""
            desc = sd.get("description", "") or ""
            name = sd.get("name", "?")
            lp = sd.get("local_path", "")
            print(
                f"  MODEL[{label}][0]: name='{name}' body={len(bc)}ch desc={len(desc)}ch path={lp}",
                flush=True,
            )
            return name, bc, desc, lp
    return None, "", "", ""


def model_list(model_ref, label):
    """List ALL skills showing body_content length."""
    m = model_ref
    if m and m.rowCount() > 0:
        bodies = []
        for i in range(min(m.rowCount(), 5)):
            sd = m.get_skill_at(i)
            if sd:
                bc_len = len(sd.get("body_content", "") or "")
                bodies.append(f"  [{i}] '{sd.get('name', '?')}' body={bc_len}ch")
        print(f"  MODEL[{label}]: first 5 bodies:", flush=True)
        for b in bodies:
            print(b, flush=True)
        # Check how many skills have empty body
        empty = sum(
            1
            for i in range(min(m.rowCount(), 50))
            if not (m.get_skill_at(i).get("body_content") or "")
        )
        total_checked = min(m.rowCount(), 50)
        print(
            f"  MODEL[{label}]: {empty}/{total_checked} skills with empty body (first 50)",
            flush=True,
        )


def run():
    log("=== STEP 1: Let models populate (4s) ===")
    QTimer.singleShot(4000, step2)


def step2():
    log("=== STEP 2: Check LIBRARY model state ===")
    lm = controller.libraryModel
    qcm = controller.quickCopyModel
    log(f"LibraryModel: {lm.rowCount()} skills")
    log(f"QuickCopyModel: {qcm.rowCount()} skills")

    model_first(lm, "LIB")
    model_first(qcm, "QC")
    model_list(lm, "LIB-list")
    model_list(qcm, "QC-list")

    log("=== Switching to QuickCopy view ===")
    controller.ui_controller.currentView = "QuickCopy"
    QTimer.singleShot(500, step3)


def step3():
    log("=== STEP 3: In QuickCopy view, select first 3 skills ===")
    qcm = controller.quickCopyModel
    qmap_state("QC-PRE-SELECT")

    if qcm.rowCount() > 0:
        # Select and check each of first 3 skills
        for idx in range(min(3, qcm.rowCount())):
            sd = qcm.get_skill_at(idx)
            bc = sd.get("body_content", "") or ""
            name = sd.get("name", "?")
            print(f"  QC MODEL[{idx}]: name='{name}' body={len(bc)}ch", flush=True)

        controller.ui_controller.selectSkill(0)
        QTimer.singleShot(500, step4)
    else:
        log("No skills in QuickCopy model!")
        app.quit()


def step4():
    log("=== STEP 4: Post selection ===")
    qmap_state("QC-POST-SELECT")
    model_first(controller.quickCopyModel, "QC-VERIFY")

    # Check the view's selected inspector

    qcv = _find_qml_obj("QuickCopyView")
    if qcv:
        sv = qcv.property("showSkillInspector")
        si = qcv.property("showCommandInspector")
        svi = qcv.property("selectedSkillValid")
        print(
            f"  QuickCopyView: showSkillInspector={sv} showCommandInspector={si} selectedSkillValid={svi}",
            flush=True,
        )

    # Now switch back to Library and test
    log("=== Switching to Library view ===")
    controller.ui_controller.currentView = "Library"
    QTimer.singleShot(1000, step5)


def step5():
    log("=== STEP 5: In Library view, select skill 0 ===")
    lm = controller.libraryModel
    if lm.rowCount() > 0:
        controller.ui_controller.selectSkill(0)
        QTimer.singleShot(500, step6)
    else:
        log("No skills in Library model!")
        app.quit()


def step6():
    log("=== STEP 6: Library post selection ===")
    qmap_state("LIB-POST-SELECT")

    # VERDICT
    sel = controller.selectedSkill
    if sel and sel.local_path:
        bc_qc = sel.body_content or ""
        print(f"\n{'=' * 60}", flush=True)
        if bc_qc:
            print(f"✅ PASS: selectedSkill has body_content ({len(bc_qc)} chars)", flush=True)
        else:
            print("❌ FAIL: selectedSkill body_content is EMPTY", flush=True)
        print(f"{'=' * 60}\n", flush=True)

    app.quit()


def _find_qml_obj(name):
    for o in engine.rootObjects():
        r = _find_recursive(o, name)
        if r:
            return r
    return None


def _find_recursive(obj, name):
    if hasattr(obj, "objectName") and obj.objectName() == name:
        return obj
    if hasattr(obj, "children"):
        for c in obj.children():
            r = _find_recursive(c, name)
            if r:
                return r
    return None


QTimer.singleShot(500, run)
log("Starting...")
app.exec()
log("Done.")
os._exit(0)
