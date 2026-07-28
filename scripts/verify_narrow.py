"""
Resize window to minimum width, select skill with very long description,
screenshot, verify no clipping in descriptionEdit.
"""

import json
import os
import signal
import sys
import time
import uuid
from pathlib import Path

START_TIME = time.monotonic()


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(55)

# ── Inject test skill into cached index ────────────────────────────
cache_path = Path.home() / ".local/share/SkillManager/skill_library_index.json"
if cache_path.exists():
    with open(cache_path) as f:
        lib_data = json.load(f)
else:
    lib_data = {"skills": [], "projects": [], "categories": [], "project_labels": [], "status": ""}

LONG_DESC = "Senior System Architect. " * 200  # ~5600 chars, many wrapped lines
test_skill = {
    "name": "ZZ_Test_Long_Desc",
    "description": LONG_DESC,
    "local_path": "/tmp/test-long-desc/skill.md",
    "category": "test",
    "author": "test",
    "version": "1.0.0",
    "tags": ["test"],
    "source_id": "test_local",
    "is_command": False,
    "is_package": True,
    "commands": [],
    "body_content": "# Test\n\nContent.\n",
    "raw_content": "",
    "project_label": "Test",
    "date": "2026-01-15",
    "source": "built-in",
    "risk": "Low",
    "client": "Antigravity",
}
lib_data["skills"].append(test_skill)
with open(cache_path, "w") as f:
    json.dump(lib_data, f)
Path("/tmp/test-long-desc").mkdir(parents=True, exist_ok=True)
Path("/tmp/test-long-desc/skill.md").write_text("# Test\n\nContent.\n")
print(f"[+0.0s] Injected test skill (desc={len(LONG_DESC)} chars)")

# ── Bootstrap ──────────────────────────────────────────────────────
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
import sentry_sdk

import skill_manager

sentry_sdk.init(
    dsn="",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment="development",
    release=f"skill-manager@{skill_manager.__version__}",
    default_integrations=False,
)
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

# ── Resize window early by setting env for the QML Window ──────────
# We'll resize programmatically after loading

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
    # Resize to narrow width (600px) to test constraint behavior
    window.resize(600, 700)
    print("[+0.1s] Window resized to 600x700")
else:
    print("FATAL: No window!")
    sys.exit(1)


# ── Schedule ──────────────────────────────────────────────────────
def step1_wait():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(14000, step2_select_long_desc)


def step2_select_long_desc():
    lm = controller.libraryModel
    rc = lm.rowCount()
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model: {rc} skills")

    # Find test skill in filtered model
    idx = -1
    for i in range(rc):
        s = lm.get_skill_at(i)
        if s.get("name") == "ZZ_Test_Long_Desc":
            idx = i
            break

    if idx >= 0:
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Found test skill at index {idx}")
        controller.ui_controller.selectSkill(idx)
    else:
        # Fallback: inject directly into model
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Test skill not found, injecting...")
        lm.isPackageOnly = False
        lm.setSkills([test_skill])
        if lm.rowCount() > 0:
            controller.ui_controller.selectSkill(0)

    sel = controller.selectedSkill
    name = sel.name if sel else "NONE"
    desc = sel.description if sel else ""
    if desc is None:
        desc = ""
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {name}, desc_len={len(desc)}")
    QTimer.singleShot(3000, step3_capture)


def step3_capture():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing screenshot...")
    commands_dir = Path("data/mcp/commands")
    acks_dir = Path("data/mcp/acks")
    captures_dir = Path("data/mcp/captures")
    for d in [commands_dir, acks_dir, captures_dir]:
        d.mkdir(parents=True, exist_ok=True)

    cmd_id = uuid.uuid4().hex
    (commands_dir / f"{cmd_id}.json").write_text(
        json.dumps({"action": "capture_screenshot", "id": cmd_id}), encoding="utf-8"
    )

    ack_path = acks_dir / f"{cmd_id}.json"
    deadline = time.monotonic() + 5.0
    shot_path = None
    while time.monotonic() < deadline:
        if ack_path.exists():
            ack = json.loads(ack_path.read_text(encoding="utf-8"))
            cp = ack.get("capture_path")
            if cp and Path(cp).exists():
                shot_path = cp
            break
        app.processEvents()
        time.sleep(0.05)

    if not shot_path and window:
        shot_path = str(captures_dir / f"{cmd_id}.png")
        img = window.grabWindow()
        img.save(shot_path)

    print(f"\nRESULT: screenshot={shot_path}")
    print(
        f"RESULT: selected={controller.selectedSkill.name if controller.selectedSkill else 'NONE'}"
    )
    print("RESULT: window_size=600x700")
    signal.alarm(0)
    QTimer.singleShot(0, app.quit)


QTimer.singleShot(100, step1_wait)
print("[+0.0s] Starting event loop...")
sys.stdout.flush()
ret = app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Done, exit={ret}")
