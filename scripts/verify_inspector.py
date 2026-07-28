"""
Helper script: starts the REAL SkillManager app, ensures Library view,
selects a skill, takes a screenshot, and exits.
Must be run from the project root via: uv run python scripts/verify_inspector.py

NOTE: old screenshots in data/mcp/captures/ are cleaned at each run.
If you add a new step, insert it BEFORE step3_take_shot.
"""

import json
import os
import sys
import time
from pathlib import Path

# ── Clean old captures so we never reference stale screenshots ─────
CAPTURES_DIR = Path("data/mcp/captures")
COMMANDS_DIR = Path("data/mcp/commands")
ACKS_DIR = Path("data/mcp/acks")
for d in [CAPTURES_DIR, COMMANDS_DIR, ACKS_DIR]:
    if d.exists():
        for f in d.iterdir():
            f.unlink()
    d.mkdir(parents=True, exist_ok=True)

# ── Step 1: Seed library with a package skill ──────────────────────
lib_data = {
    "skills": [
        {
            "name": "Senior Software Architect",
            "description": (
                "You are a Senior System Architect responsible for designing "
                "large-scale distributed systems, microservices architectures, "
                "event-driven patterns, and cloud-native solutions. " * 30
            ),
            "local_path": "/tmp/test-pkg-skill/skill.md",
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
    "projects": [{"name": "Test", "source_id": "test", "index_path": "/tmp/test-pkg-skill"}],
    "categories": ["architecture"],
    "project_labels": ["Test"],
    "status": "Found 1 package skill",
}
os.makedirs("/tmp/test-pkg-skill", exist_ok=True)
Path("data").mkdir(exist_ok=True)
with open("data/skill_library_index.json", "w") as f:
    json.dump(lib_data, f)
with open("/tmp/test-pkg-skill/skill.md", "w") as f:
    f.write("# Test Skill\n\nPackage skill content.\n")

# ── Step 2: Set up Ctrl+C / timeout watchdog to prevent hung app ───
import signal

START_TIME = time.monotonic()
TIMEOUT = 45  # seconds


def watchdog_timeout(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s elapsed — forcing exit")
    # Forceful termination
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog_timeout)
signal.alarm(TIMEOUT + 5)

# ── Step 3: Bootstrap the REAL app (same as app_main()) ────────────
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"

import sentry_sdk  # noqa: E402

import skill_manager  # noqa: E402

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN", ""),
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment="development",
    release=f"skill-manager@{skill_manager.__version__}",
    default_integrations=False,
)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication, QSurfaceFormat  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

QQuickStyle.setStyle("Basic")
fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)

app = QGuiApplication(sys.argv)
app.setApplicationName("SkillManager")
app.setApplicationVersion(skill_manager.__version__)

# ── Step 4: Create AppController ───────────────────────────────────
from skill_manager.app import AppController  # noqa: E402

controller = AppController()
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)

from skill_manager.controllers.font_database_bridge import FontDatabaseBridge  # noqa: E402

font_bridge = FontDatabaseBridge()
qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)

# ── Step 5: Create engine & load real Main.qml ─────────────────────
engine = QQmlApplicationEngine()
controller._qml_engine = engine

from skill_manager.core.resources import (  # noqa: E402
    invalidate_qml_disk_cache_if_stale,
    qml_components_dir,
)

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

# ── Step 6: Schedule actions after app starts ────────────────────┐
results = {"screenshot": None, "state": None}


def step1_wait_for_load():
    """Wait 15 seconds for discovery, model population, and incubation."""
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Waiting for app to settle...")
    QTimer.singleShot(6000, step2_check_state)


def step2_check_state():
    """Ensure Library view, check model state, and select a skill."""
    lm = controller.libraryModel
    rc = lm.rowCount()
    sel = controller.selectedSkill

    # Force Library view — the config may have been corrupted by prior runs
    controller.ui_controller.currentView = "Library"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Model: {rc} skills | Forced view=Library")
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected before: {sel.name if sel else 'NONE'}")

    if rc > 0:
        # Inject body_content into the selected skill from the actual file
        # since the discovery cache strips body_content
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Calling selectSkill(0)...")
        controller.ui_controller.selectSkill(0)
        # Also force-inject our test skill with body_content to verify QML rendering
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Injecting test skill with body_content...")
        lm.isPackageOnly = False
        with open(
            "/home/dikka/.agent/skills/agentic-awesome-skills-86c7698d/ask-questions-if-underspecified/SKILL.md",
            encoding="utf-8",
        ) as f:
            raw = f.read()
        from skill_manager.core.parsing.skill import split_frontmatter

        _, body = split_frontmatter(raw)
        lm.setSkills(
            [
                {
                    "name": "ask-questions-if-underspecified",
                    "description": "Clarify requirements before implementing. Use when serious doubts arise.",
                    "local_path": "/tmp/test-injected/skill.md",
                    "category": "architecture",
                    "author": "team",
                    "version": "1.0.0",
                    "tags": ["architecture"],
                    "source_id": "test",
                    "is_command": False,
                    "is_package": False,
                    "commands": [],
                    "body_content": body,
                    "raw_content": raw,
                    "project_label": "Test Injection",
                }
            ]
        )
        controller.ui_controller.selectSkill(0)

    # Wait for QML to process AND for full discovery to populate body_content
    QTimer.singleShot(15000, step3_take_shot)


def step3_take_shot():
    """Take screenshot and dump state."""
    sel = controller.selectedSkill
    results["state"] = sel.name if sel else "NONE"
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Selected: {results['state']}")

    # Debug: check body_content in the selected skill and model
    bc = sel.body_content if sel else ""
    bc_len = len(bc) if bc else 0

    # Also check the raw model data
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

    # If body_content is empty, inject it from the actual skill file
    if bc_len == 0 and sel:
        # Get path from model or fallback to known paths
        local_path = model_path or ""
        if not local_path:
            # Try the most common skill directory
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
                    # Force re-emit so QML bindings re-evaluate
                    controller.selectedSkillChanged.emit()
                    # Let QML settle
                    for _ in range(10):
                        app.processEvents()
                    bc_len = len(body)
            else:
                print(f"[+{time.monotonic() - START_TIME:.1f}s] File not found: {skill_md}")
        else:
            print(
                f"[+{time.monotonic() - START_TIME:.1f}s] No local_path available from model or filesystem"
            )

    print(f"[+{time.monotonic() - START_TIME:.1f}s] body_content final len={bc_len}")

    import uuid

    cmd_id = uuid.uuid4().hex
    out = CAPTURES_DIR / f"{cmd_id}.png"

    # Use direct window grab — IPC capture in headless mode grabs wrong region
    if window:
        # Force multiple event loops so QML paints the inspector frame
        for _ in range(5):
            app.processEvents()
        img = window.grabWindow()
        img.save(str(out))
        results["screenshot"] = str(out)
        print(f"[+{time.monotonic() - START_TIME:.1f}s] Direct capture saved: {out}")
    else:
        print(f"[+{time.monotonic() - START_TIME:.1f}s] No window to capture!")

    # Quit
    print(f"[+{time.monotonic() - START_TIME:.1f}s] Done. Quitting.")
    signal.alarm(0)  # disarm watchdog
    QTimer.singleShot(0, app.quit)


# Schedule step 1 after a brief delay to let constructor settle
QTimer.singleShot(100, step1_wait_for_load)

# ── Step 7: Enter event loop ───────────────────────────────────────
print("[+0.0s] Starting event loop...")
sys.stdout.flush()
ret = app.exec()

print(f"[+{time.monotonic() - START_TIME:.1f}s] Event loop exited with code {ret}")

if results["screenshot"]:
    print(f"\nSCREENSHOT: {results['screenshot']}")
    print(f"SELECTED: {results['state']}")
