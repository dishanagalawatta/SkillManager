"""
Verify QuickCopy view: switch to QuickCopy, select test skill,
check inspector renders content correctly.
Run: uv run python scripts/verify_qc.py
"""

import json
import os
import signal
import sys
import time
import uuid
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
for f in CAPTURES_DIR.glob("*.png"):
    f.unlink()

START_TIME = time.monotonic()
TIMEOUT = 50


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit")
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(TIMEOUT + 5)

# ── Seed library ────────────────────────────────────────────────────
lib_data = {
    "skills": [
        {
            "name": "Senior Software Architect",
            "description": "You are a Senior System Architect. " * 30,
            "local_path": "/tmp/test-qc-skill/skill.md",
            "category": "architecture",
            "author": "team",
            "version": "1.0.0",
            "tags": ["architecture"],
            "source_id": "test",
            "is_command": False,
            "is_package": True,
            "commands": [],
            "body_content": "",
            "raw_content": "",
            "project_label": "Test",
            "date": "2026-01-15",
            "source": "built-in",
            "risk": "Low",
            "client": "Antigravity",
        }
    ],
    "projects": [{"name": "Test", "source_id": "test", "index_path": "/tmp/test-qc-skill"}],
    "categories": ["architecture"],
    "project_labels": ["Test"],
    "status": "Found 1 package skill",
}
os.makedirs("/tmp/test-qc-skill", exist_ok=True)
Path("data").mkdir(exist_ok=True)
with open("data/skill_library_index.json", "w") as f:
    json.dump(lib_data, f)
with open("/tmp/test-qc-skill/skill.md", "w") as f:
    f.write("# Test Skill\n\nContent.\n")

# ── Bootstrap real app ──────────────────────────────────────────────
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
from skill_manager.core.resources import invalidate_qml_disk_cache_if_stale, qml_components_dir

invalidate_qml_disk_cache_if_stale(skill_manager.__version__)
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

# ── Schedule steps ──────────────────────────────────────────────────
results = {"screenshot": None, "state": None}


def step1_wait():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(6000, step2_setup_qc)


def step2_setup_qc():
    """Switch to QuickCopy view, select skill, inject body_content."""
    lm = controller.libraryModel
    rc = lm.rowCount()

    # Switch to QuickCopy view
    controller.ui_controller.currentView = "QuickCopy"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model: {rc} skills | Forced view=QuickCopy")

    sel = controller.selectedSkill
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected before: {sel.name if sel else 'NONE'}")

    if rc > 0:
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Calling selectSkill(0)...")
        controller.ui_controller.selectSkill(0)

        # Inject test skill with inline body_content
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Injecting test skill with body_content...")
        lm.isPackageOnly = False

        body_content = (
            "# Test QuickCopy Inspector\n\n"
            "## Overview\n"
            "This is a test skill to verify the QuickCopy view inspector renders content correctly. "
            "The inspector panel should display this body content after the skill is selected.\n\n"
            "## Features\n"
            "- Inspector overlay visibility\n"
            "- Description rendering\n"
            "- Metadata pills display\n"
            "- Body content text rendering\n\n"
            "## Verification Checklist\n\n"
            "1. The inspector panel should be visible on the right side\n"
            "2. The skill name should display at the top\n"
            "3. Description text should render below the name\n"
            "4. Metadata pills (Location, Type, Source) should be present\n"
            "5. Body content should render below the pills\n\n"
            "## Detailed Notes\n\n"
            "This test validates that the overlayVisible fix applied to QuickCopyView.qml "
            "correctly makes the inspector panel visible when a skill is selected. "
            "The fix ensures that overlayVisible binding is recomputed on each skill selection, "
            "rather than being stale from the initial QML item creation.\n\n"
            "### Key Properties\n\n"
            "- overlayVisible: should be true after selection\n"
            "- showSkill: should be true\n"
            "- inspectorVisible: derived from overlayVisible\n\n"
            "---\n"
            "*End of test content.*\n"
        )

        lm.setSkills(
            [
                {
                    "name": "QC-Test-Inspector-Skill",
                    "description": "Test skill for QuickCopy view inspector verification. Validates that overlayVisible, description, metadata pills, and body content all render correctly after the fix.",
                    "local_path": "/tmp/test-qc-injected/skill.md",
                    "category": "testing",
                    "author": "verification",
                    "version": "1.0.0",
                    "tags": ["test", "verification"],
                    "source_id": "test",
                    "is_command": False,
                    "is_package": False,
                    "commands": [],
                    "body_content": body_content,
                    "raw_content": body_content,
                    "project_label": "QC Verification",
                }
            ]
        )
        controller.ui_controller.selectSkill(0)

    QTimer.singleShot(15000, step3_capture)


def step3_capture():
    """Take screenshot and dump state."""
    sel = controller.selectedSkill
    results["state"] = sel.name if sel else "NONE"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {results['state']}")

    bc = sel.body_content if sel else ""
    bc_len = len(bc) if bc else 0

    # Check model data too
    model_skill = {}
    try:
        model_skill = controller.libraryModel.get_skill_at(0) or {}
    except Exception:
        pass
    model_bc = model_skill.get("body_content", "")
    model_bc_len = len(model_bc) if model_bc else 0
    model_path = model_skill.get("local_path", "")

    print(
        f"[+{time.monotonic() - START_TIME:.1f}s] body_content len (QMap)={bc_len} | (model)={model_bc_len}"
    )
    print(f"[+{time.monotonic() - START_TIME:.1f}s] model local_path={model_path}")

    # If empty, inject from file
    if bc_len == 0 and sel:
        local_path = model_path or ""
        if not local_path:
            for p in sorted(Path.home().joinpath(".agent/skills").glob("*/SKILL.md")):
                local_path = str(p)
                print(f"[+{time.monotonic() - START_TIME:.1f}s] Found skill file: {local_path}")
                break
        if local_path:
            skill_md = Path(local_path)
            if skill_md.is_file():
                from skill_manager.core.parsing.skill import parse_skill_md

                parsed = parse_skill_md(str(skill_md))
                body = parsed.get("body_content", "")
                raw = parsed.get("raw_content", "")
                print(
                    f"[+{time.monotonic() - START_TIME:.1f}s] Injecting body_content: {len(body)} chars from {skill_md}"
                )
                if body:
                    sel.body_content = body
                    sel.raw_content = raw
                    sel.local_path = local_path
                    controller.selectedSkillChanged.emit()
                    for _ in range(10):
                        app.processEvents()
                    bc_len = len(body)

    print(f"[+{time.monotonic() - START_TIME:.1f}s] body_content final len={bc_len}")

    # Capture screenshot

    cmd_id = uuid.uuid4().hex
    out = CAPTURES_DIR / f"{cmd_id}.png"

    if window:
        for _ in range(5):
            app.processEvents()
        img = window.grabWindow()
        img.save(str(out))
        results["screenshot"] = str(out)
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Direct capture saved: {out}")
    else:
        print(f"[+{time.monotonic() - START_TIME:.1f}s] No window to capture!")

    print(f"[+{time.monotonic() - START_TIME:.1f}s] Done. Quitting.")
    signal.alarm(0)
    QTimer.singleShot(0, app.quit)


QTimer.singleShot(100, step1_wait)
print("[+0.0s] Starting event loop...")
sys.stdout.flush()
ret = app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Event loop exited with code {ret}")

if results["screenshot"]:
    print(f"\nSCREENSHOT: {results['screenshot']}")
    print(f"SELECTED: {results['state']}")
