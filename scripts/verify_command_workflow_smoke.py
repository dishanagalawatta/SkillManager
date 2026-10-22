# ruff: noqa: E402, ARG001
"""
Offscreen smoke check for the unified command workflow.

Replaces the old "command-edit project selector resync" check. The
create/edit dialog no longer has a project selector — the Library owns
the canonical command file and deployment goes through the Library's copy
flow — so the stale-checkbox regression the old check guarded can no
longer happen. The check now asserts the contract that replaced it:

  1. The command dialog exposes no project selector.
  2. Editing a command rewrites the canonical file IN PLACE and does not
     fan out a copy into another project.
  3. The copy flow DETECTS a command that already exists in the target
     project instead of overwriting it silently.

Drives the REAL app (real AppController + real Main.qml, same process) —
no inline QML, no temp .qml files, no pytest. Property assertions only;
visual layout is out of scope for this check.

Usage: uv run python scripts/verify_command_workflow_smoke.py
Exit code 0 = all assertions held, 1 = regression detected.
"""

import os
import sys
import threading
import time
from pathlib import Path

START_TIME = time.monotonic()
FAILURES: list[str] = []


def _watchdog_fire():
    print(f"WATCHDOG: {time.monotonic() - START_TIME:.1f}s elapsed — forcing exit")
    os._exit(1)


# threading.Timer (not signal.alarm) so the watchdog also works on Windows CI.
_WATCHDOG = threading.Timer(120.0, _watchdog_fire)
_WATCHDOG.daemon = True
_WATCHDOG.start()


def qml_to_py(value):
    # QML var properties surface as QJSValue; toVariant() converts JS
    # arrays/objects to Python lists/dicts.
    if value is not None and hasattr(value, "toVariant"):
        try:
            return value.toVariant()
        except Exception:
            return value
    return value


def check(name, actual, expected):
    actual, expected = list(qml_to_py(actual) or []), list(expected or [])
    if sorted(actual) == sorted(expected):
        print(f"  PASS: {name} = {actual}")
    else:
        msg = f"{name}: expected {expected}, got {actual}"
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def check_true(name, condition, detail=""):
    if condition:
        print(f"  PASS: {name}")
    else:
        msg = f"{name} {detail}".strip()
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"
os.environ["SKILL_MANAGER_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["XDG_DATA_HOME"] = str(Path("data/test_xdg_data").resolve())
os.environ["XDG_CONFIG_HOME"] = str(Path("data/test_xdg_config").resolve())
# ConfigManager in test mode refuses the production data dir (XDG vars do
# not redirect it on Windows) — point it at an isolated path instead,
# same as tests/conftest.py.
os.environ["SKILL_MANAGER_DATA_DIR"] = str(Path("data/test_xdg_data/smoke_datadir").resolve())

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
app.setApplicationVersion(skill_manager.__version__)

from skill_manager.app import AppController
from skill_manager.controllers.font_database_bridge import FontDatabaseBridge
from skill_manager.core.commands import find_command_holder_projects
from skill_manager.core.resources import qml_components_dir

controller = AppController()
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
font_bridge = FontDatabaseBridge()
qmlRegisterSingletonInstance(FontDatabaseBridge, "App", 1, 0, "FontDB", font_bridge)

engine = QQmlApplicationEngine()
controller._qml_engine = engine
qml_dir = qml_components_dir(package_file="src/skill_manager/app.py")
engine.addImportPath(str(qml_dir.parent))
engine.load(str(qml_dir / "Main.qml"))

if not engine.rootObjects():
    print("FATAL: No QML root objects!")
    sys.exit(1)
window = engine.rootObjects()[0]

# Deterministic fixture: one command held by both test projects.
proj_a = Path("data/test_xdg_data/smoke_projA").resolve()
proj_b = Path("data/test_xdg_data/smoke_projB").resolve()
for proj in (proj_a, proj_b):
    (proj / ".agents" / "commands").mkdir(parents=True, exist_ok=True)
    (proj / ".agents" / "commands" / "SmokeCmd.md").write_text(
        "---\nname: SmokeCmd\ncategory: Custom Commands\ntype: command\n---\nBody",
        encoding="utf-8",
    )
controller._projects = [str(proj_a), str(proj_b)]
EXPECTED_HOLDERS = find_command_holder_projects("SmokeCmd", [str(proj_a), str(proj_b)])
assert len(EXPECTED_HOLDERS) == 2, f"fixture broken: {EXPECTED_HOLDERS}"

SKILL = {
    "name": "SmokeCmd",
    "local_path": str(proj_a / ".agents" / "commands" / "SmokeCmd.md"),
    "category": "Custom Commands",
    "is_command": True,
    "body_content": "Body",
    "project_label": EXPECTED_HOLDERS[0],
}


def find_dialog(obj):
    if obj is not None and "CommandCreateDialog" in str(obj.metaObject().className()):
        return obj
    for child in obj.children():
        res = find_dialog(child)
        if res is not None:
            return res
    return None


def find_multiselect(dialog):
    for child in dialog.findChildren(object):
        try:
            if (
                child.property("allLabel") == "All Projects"
                and child.property("selectedValues") is not None
            ):
                return child
        except Exception:
            continue
    return None


CTX: dict = {}


def step_open_first():
    print(f"[+{time.monotonic() - START_TIME:.1f}s] open the command dialog")
    dlg = find_dialog(window)
    if dlg is None:
        print("FATAL: CommandCreateDialog not found in QML tree!")
        os._exit(1)
    CTX["dlg"] = dlg
    dlg.openForEdit(SKILL)
    QTimer.singleShot(800, step_assert_dialog)


def step_assert_dialog():
    """The dialog must not offer a project selector any more."""
    dlg = CTX["dlg"]
    print("assert the dialog has no project selector:")
    check_true(
        "no editProjectLabels property",
        dlg.property("editProjectLabels") is None,
        f"(got {dlg.property('editProjectLabels')!r})",
    )
    check_true(
        "no GlassMultiSelect under the dialog",
        find_multiselect(dlg) is None,
        "(a project selector is still present)",
    )
    check_true(
        "the edited command path is known",
        bool(dlg.property("editLocalPath")),
        f"(got {dlg.property('editLocalPath')!r})",
    )
    dlg.close()
    QTimer.singleShot(600, step_update_in_place)


def step_update_in_place():
    """Editing a command rewrites the canonical file, in place only."""
    print(f"[+{time.monotonic() - START_TIME:.1f}s] update the canonical command")
    controller.ops.updateCustomCommandFull(
        str(proj_a / ".agents" / "commands" / "SmokeCmd.md"),
        "SmokeCmd",
        "Updated body",
        "Custom Commands",
        "",
    )
    QTimer.singleShot(1200, step_assert_in_place)


def step_assert_in_place():
    canonical = proj_a / ".agents" / "commands" / "SmokeCmd.md"
    other = proj_b / ".agents" / "commands" / "SmokeCmd.md"
    print("assert the update stayed in place:")
    check_true(
        "the canonical file carries the new body",
        "Updated body" in canonical.read_text(encoding="utf-8"),
        f"(got {canonical.read_text(encoding='utf-8')!r})",
    )
    check_true(
        "the other project was NOT modified",
        "Updated body" not in other.read_text(encoding="utf-8"),
        "(the edit fanned out into another project)",
    )
    QTimer.singleShot(300, step_conflict_detection)


def step_conflict_detection():
    """The copy flow must detect the command that already exists."""
    print(f"[+{time.monotonic() - START_TIME:.1f}s] detect the copy conflict")
    from skill_manager.core.copier import find_existing_commands_in_projects

    existing = find_existing_commands_in_projects(
        [{"local_path": str(proj_a / ".agents" / "commands" / "SmokeCmd.md"), "name": "SmokeCmd"}],
        [str(proj_b)],
    )
    check("the conflicting command is reported", [e["name"] for e in existing], ["SmokeCmd"])
    check_true(
        "the conflict points at the target project",
        bool(existing) and existing[0]["project"] == str(proj_b),
        f"(got {existing[0]['project'] if existing else None!r})",
    )
    QTimer.singleShot(300, finish)


def finish():
    _WATCHDOG.cancel()
    if FAILURES:
        print(f"SMOKE RESULT: {len(FAILURES)} FAILURE(S)")
        for f in FAILURES:
            print(f"  - {f}")
        os._exit(1)
    print(f"[+{time.monotonic() - START_TIME:.1f}s] SMOKE RESULT: all workflow assertions held")
    QTimer.singleShot(100, app.quit)


QTimer.singleShot(2500, step_open_first)
app.exec()
print(f"[+{time.monotonic() - START_TIME:.1f}s] Script complete.")
