# ruff: noqa: E402, ARG001
"""Real-app interaction profiler for the "feel snappy" pass (2026-10-28).

Boots the REAL ``AppController`` + ``Main.qml`` on the real display, then times
what the user actually waits for: how long the window keeps rendering after an
action, and the worst frame in that burst (a long frame is the visible hitch).

For every action it reports:

* ``settle``  — ms from the action until the render burst goes quiet, i.e. how
  long the UI was still visibly reacting.
* ``max``     — the longest single frame in that burst (jank; 16.7 ms = 60 Hz).
* ``frames``  — frames rendered in the burst.

Run: uv run python scripts/profile_ui_perf.py [--skills 120]
"""

import json
import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

CAPTURES_DIR = Path("data/mcp/captures")
START_TIME = time.monotonic()

SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-perf-ui-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_MCP_NO_IPC"] = "1"

SKILLS_PER_PROJECT = 120
for arg in sys.argv[1:]:
    if arg.startswith("--skills="):
        SKILLS_PER_PROJECT = int(arg.split("=")[-1])
if "--skills" in sys.argv:
    SKILLS_PER_PROJECT = int(sys.argv[sys.argv.index("--skills") + 1])


def watchdog(signum, frame):
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s — forcing exit", flush=True)
    os._exit(1)


signal.signal(signal.SIGALRM, watchdog)
signal.alarm(240)

import sentry_sdk

import skill_manager

sentry_sdk.init(dsn="", default_integrations=False)

from PySide6.QtCore import QObject, QTimer
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
controller.ui_controller.darkMode = True

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
if window is None:
    print("FATAL: no QML root object", flush=True)
    sys.exit(1)
window.show()
window.raise_()

RESULTS: list[dict] = []
BURST: list[float] = []
ACTION_START = 0.0
CURRENT: dict = {}


def _now() -> float:
    return time.perf_counter()


def _on_frame():
    BURST.append(_now())


window.frameSwapped.connect(_on_frame)


def _log(step, message):
    print(f"[+{time.monotonic() - START_TIME:.1f}s] {step}: {message}", flush=True)


def _make_world(projects: int, skills: int) -> list[Path]:
    import random

    random.seed(7)
    roots = []
    categories = ["Engineering", "Design", "Marketing", "Ops", "Security"]
    for index in range(projects):
        root = SCRATCH / f"project{index}"
        skills_dir = root / ".agents" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        for number in range(skills):
            category = categories[number % len(categories)]
            folder = skills_dir / f"skill-{number:03d}"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "SKILL.md").write_text(
                "---\n"
                f"name: Skill {number:03d}\n"
                f"description: {category} workflow {number} for project {index}.\n"
                "allowed-tools: Read, Write, Edit\n"
                f"collections: [{category.lower()}]\n"
                "---\n\n"
                f"# Skill {number:03d}\n\n" + ("Body line for the agent.\n" * 30),
                encoding="utf-8",
            )
        (root / ".agents" / "commands").mkdir(parents=True, exist_ok=True)
        for number in range(6):
            (root / ".agents" / "commands" / f"cmd-{number}.md").write_text(
                f"---\nname: Command {number}\ndescription: Do the thing.\n---\n\nRun it.\n",
                encoding="utf-8",
            )
        roots.append(root)
    return roots


def _record():
    settle_ms = ((BURST[-1] - ACTION_START) * 1000) if BURST else 0.0
    gaps = [(BURST[i] - BURST[i - 1]) * 1000 for i in range(1, len(BURST))]
    CURRENT.update(
        settle=round(settle_ms, 1),
        max=round(max(gaps), 1) if gaps else 0.0,
        frames=len(BURST),
    )
    RESULTS.append(dict(CURRENT))
    _log("MEASURE", f"{CURRENT.get('action')}: {CURRENT}")
    settle_timer.stop()
    QTimer.singleShot(120, _run_next)


def _settle_tick():
    """Record the burst once the window has been quiet for a moment."""
    if not BURST:
        # Some actions render nothing (no visual change): don't wait forever.
        if _now() - ACTION_START > 0.4:
            _record()
        return
    if _now() - BURST[-1] < 0.12:
        return
    _record()


settle_timer = QTimer()
settle_timer.setInterval(40)
settle_timer.timeout.connect(_settle_tick)

STEPS: list[tuple[str, object]] = []


def _measure(action):
    def _begin():
        CURRENT.clear()
        CURRENT["action"] = action[0]
        BURST.clear()
        global ACTION_START
        ACTION_START = _now()
        action[1]()
        settle_timer.start()

    return _begin


def _run_next():
    if not STEPS:
        _finish()
        return
    _measure(STEPS.pop(0))()


def _find(name):
    return window.findChild(QObject, name)


def _set_page(index):
    pages = _find("uv_pages")
    if pages is not None:
        pages.setProperty("currentIndex", index)


def _open_project_dropdown_and_pick(index):
    """Pick a project the way the UI does: through the config controller."""
    labels = controller.config_controller.projectLabels
    if 0 <= index < len(labels):
        controller.setCurrentProject(labels[index])


def _finish():
    print("\n=== INTERACTION TIMINGS ===")
    header = f"{'action':38s} {'settle ms':>10s} {'max frame':>10s} {'frames':>7s}"
    print(header)
    for row in RESULTS:
        print(
            f"{row.get('action', '?'):38s} {row.get('settle', 0):10.1f} "
            f"{row.get('max', 0):10.1f} {row.get('frames', 0):7d}"
        )
    Path("data/mcp/perf_interactions.json").parent.mkdir(parents=True, exist_ok=True)
    Path("data/mcp/perf_interactions.json").write_text(json.dumps(RESULTS, indent=2))
    print("\nwrote data/mcp/perf_interactions.json")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0)


def step_boot():
    roots = _make_world(3, SKILLS_PER_PROJECT)
    paths = [str(root) for root in roots]
    controller._config.set("sources", paths)
    controller._config.set("projects", paths)
    controller._sources = paths
    controller._projects = paths
    controller.config_controller._invalidate_project_cache()
    active = paths[0]
    for number in range(12):
        controller.addProjectTask(active, f"Existing task {number}", "medium", "notes")
    _log("SETUP", f"3 projects x {SKILLS_PER_PROJECT} skills")
    controller.refreshSkills("perf", True)
    QTimer.singleShot(6000, _start_measuring)


def _start_measuring():
    labels = controller.config_controller.projectLabels
    STEPS.extend(
        [
            ("navigate Workbench (cold)", lambda: window.navigateTo("QuickCopy")),
            ("navigate Library", lambda: window.navigateTo("Library")),
            ("navigate Hub", lambda: window.navigateTo("Updates")),
            ("navigate Settings", lambda: window.navigateTo("Settings")),
            ("navigate Workbench (warm)", lambda: window.navigateTo("QuickCopy")),
            ("switch project #2", lambda: _open_project_dropdown_and_pick(1)),
            ("switch project #3", lambda: _open_project_dropdown_and_pick(2)),
            ("switch project #1", lambda: _open_project_dropdown_and_pick(0)),
            (
                "open tasks panel",
                lambda: controller.ui_controller.setTasksPanelOpen(True),
            ),
            ("close tasks panel", lambda: controller.ui_controller.setTasksPanelOpen(False)),
            ("select first skill", lambda: controller.selectSkill(0)),
            ("select 40th skill", lambda: controller.selectSkill(40)),
            ("navigate Library (warm)", lambda: window.navigateTo("Library")),
            ("navigate Workbench (again)", lambda: window.navigateTo("QuickCopy")),
        ]
    )
    if not labels:
        _log("SETUP", "no project labels resolved — project switches will no-op")
    _log("START", f"labels={labels}")
    _run_next()


QTimer.singleShot(2500, step_boot)
app.exec()
