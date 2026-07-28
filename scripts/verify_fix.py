"""
Helper: inject a skill with LONG description, select it, screenshot.
Run via: .venv/bin/python scripts/verify_fix.py
"""

import json
import os
import signal
import sys
import time
import uuid
from pathlib import Path

# ── Timeout watchdog ───────────────────────────────────────────────
START_TIME = time.monotonic()


def watchdog_timeout(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog_timeout)
signal.alarm(50)

# ── Seed library (keep real skills, add our test skill) ────────────
os.makedirs("/tmp/test-pkg-skill", exist_ok=True)
with open("/tmp/test-pkg-skill/skill.md", "w") as f:
    f.write("# Test Skill\n\nContent.\n")

LONG_DESC = (
    "Senior System Architect responsible for designing "
    "large-scale distributed systems, microservices architectures, "
    "event-driven patterns, and cloud-native solutions. "
    * 30  # ~1800 chars, many lines when wrapped
)

# Inject into existing index if present, otherwise create
index_path = Path("data/skill_library_index.json")
if index_path.exists():
    with open(index_path) as f:
        lib_data = json.load(f)
else:
    lib_data = {"skills": [], "projects": [], "categories": [], "project_labels": [], "status": ""}

# Add/update our test skill with a long description
lib_data["skills"].append(
    {
        "name": "ZZ_Test_Long_Description",
        "description": LONG_DESC,
        "local_path": "/tmp/test-pkg-skill/skill.md",
        "category": "architecture",
        "author": "team",
        "version": "1.0.0",
        "tags": ["test"],
        "source_id": "test",
        "is_command": False,
        "is_package": True,
        "commands": [],
        "body_content": "# Test Skill\n\nLong body content for testing.\n",
        "raw_content": "",
        "project_label": "Test",
        "date": "2026-01-15",
        "source": "built-in",
        "risk": "Low",
        "client": "Antigravity",
    }
)
with open(index_path, "w") as f:
    json.dump(lib_data, f)

print("[+0.0s] Library seeded with test skill")

# ── Boostrap REAL app ──────────────────────────────────────────────
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

if not engine.rootObjects():
    print("FATAL: No QML root objects!")
    sys.exit(1)


# ── Schedule actions ───────────────────────────────────────────────
def step1_wait():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(12000, step2_inject_and_select)


def step2_inject_and_select():
    lm = controller.libraryModel
    rc = lm.rowCount()
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model: {rc} skills")

    # Inject our test skill
    lm.isPackageOnly = False
    test_skill = {
        "name": "ZZ_Test_Long_Description",
        "description": LONG_DESC,
        "local_path": "/tmp/test-pkg-skill/skill.md",
        "category": "architecture",
        "author": "team",
        "version": "1.0.0",
        "tags": ["test"],
        "source_id": "test",
        "is_command": False,
        "is_package": True,
        "commands": [],
        "body_content": "# Test\n\nBody\n",
        "raw_content": "",
        "project_label": "Test",
        "date": "2026-01-15",
        "source": "built-in",
        "risk": "Low",
        "client": "Antigravity",
    }
    lm.setSkills([test_skill] + [])  # replace model
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model after inject: {lm.rowCount()} skills")

    # Select it
    controller.ui_controller.selectSkill(0)
    sel = controller.selectedSkill
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {sel.name if sel else 'NONE'}")

    QTimer.singleShot(3000, step3_capture)


def step3_capture():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Capturing screenshot...")

    # Try IPC capture first
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

    if shot_path:
        print(f"[+{time.monotonic() - START_TIME:.1f}s] IPC capture: {shot_path}")
    else:
        # Fallback: direct grab
        if window:
            out = captures_dir / f"{cmd_id}.png"
            img = window.grabWindow()
            img.save(str(out))
            shot_path = str(out)
            print(f"[+{time.monotonic() - START_TIME:.1f}s] Direct capture: {out}")

    print(f"\nRESULT: screenshot={shot_path}")
    print(
        f"RESULT: selected={controller.selectedSkill.name if controller.selectedSkill else 'NONE'}"
    )
    if controller.selectedSkill:
        desc = controller.selectedSkill.description or ""
        print(f"RESULT: desc_length={len(desc)}")

    signal.alarm(0)
    QTimer.singleShot(0, app.quit)


QTimer.singleShot(100, step1_wait)
print("[+0.0s] Starting event loop...")
sys.stdout.flush()
ret = app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Done, exit code={ret}")
