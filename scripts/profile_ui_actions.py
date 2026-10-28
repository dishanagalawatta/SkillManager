"""Profiling harness for the "make the UI feel snappy" pass (2026-10-28).

Drives the REAL ``AppController`` (no QML engine needed) through the work a
session actually does — discovery, project switches, selecting skills, task
counts, adding tasks — and prints a per-action table plus a cProfile dump of
the whole run.

Run: uv run python scripts/profile_ui_actions.py [--skills 120]
"""

from __future__ import annotations

import cProfile
import io
import os
import pstats
import shutil
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SKILL_MANAGER_SKIP_INITIAL_LOAD", "1")
os.environ["SKILL_MANAGER_DEV_MODE"] = "1"

SCRATCH = Path(tempfile.mkdtemp(prefix="skillmanager-perf-"))
os.environ["SKILL_MANAGER_DATA_DIR"] = str(SCRATCH / "data")


def _noop(*_args, **_kwargs):
    return None


import skill_manager.core.analytics as _analytics  # noqa: E402

for _name in ("capture_event", "capture_exception", "capture"):
    if hasattr(_analytics, _name):
        setattr(_analytics, _name, _noop)

from PySide6.QtCore import QCoreApplication  # noqa: E402  # noqa: I001

app = QCoreApplication(sys.argv)

from skill_manager.app import AppController  # noqa: E402

TIMINGS: list[tuple[str, float]] = []


def _time(label: str, fn):
    start = time.perf_counter()
    result = fn()
    elapsed = (time.perf_counter() - start) * 1000
    TIMINGS.append((label, elapsed))
    return result


def _make_world(projects: int, skills_per_project: int) -> list[Path]:
    """A realistic workspace: N projects, each with M skills, plus README noise."""
    roots: list[Path] = []
    for index in range(projects):
        root = SCRATCH / f"project{index}"
        skills = root / ".agents" / "skills"
        skills.mkdir(parents=True, exist_ok=True)
        for number in range(skills_per_project):
            folder = skills / f"skill-{number:03d}"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "SKILL.md").write_text(
                "---\n"
                f"name: Skill {number:03d}\n"
                f"description: Handles task category {number % 7} for project {index}.\n"
                "allowed-tools: Read, Write\n"
                "---\n\n"
                f"# Skill {number:03d}\n\n" + ("Body line.\n" * 40),
                encoding="utf-8",
            )
            (folder / "notes.md").write_text("notes\n", encoding="utf-8")
        (root / ".agents" / "commands").mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text("# project\n", encoding="utf-8")
        roots.append(root)
    return roots


def main() -> None:
    skills_per_project = 120
    for arg in sys.argv[1:]:
        if arg.startswith("--skills"):
            skills_per_project = int(arg.split("=")[-1]) if "=" in arg else skills_per_project
    if "--skills" in sys.argv:
        skills_per_project = int(sys.argv[sys.argv.index("--skills") + 1])

    roots = _make_world(3, skills_per_project)
    paths = [str(root) for root in roots]

    controller = AppController()
    controller._config.set("sources", paths)
    controller._config.set("projects", paths)
    controller._sources = paths
    controller._projects = paths
    controller.config_controller._invalidate_project_cache()

    _time("refreshSkills(cold)", lambda: controller.refreshSkills("perf", True))
    _time("refreshSkills(warm)", lambda: controller.refreshSkills("perf", False))

    labels = [controller.config_controller.getProjectLabel(path) for path in paths]
    for label in labels:
        _time(f"setCurrentProject({label})", lambda label=label: controller.setCurrentProject(label))

    count = len(controller._library_model._all_skills)
    for index in range(min(20, count)):
        _time(f"selectSkill(#{index})", lambda index=index: controller.selectSkill(index))

    for label in labels:
        controller.setCurrentProject(label)
        _time("CurrentProjectTasks", lambda: controller.tasks.currentProjectTasks)
        _time("projectTaskCounts", lambda: controller.tasks.projectTaskCounts)
        _time("activeTaskCount", lambda: controller.tasks.activeTaskCount)

    active = paths[0]
    for number in range(25):
        _time(
            f"addProjectTask(#{number})",
            lambda number=number: controller.tasks.addProjectTask(
                active, f"Task {number}", "medium", "notes"
            ),
        )
    from skill_manager.core import tasks as task_store

    task_id = task_store.get_tasks(active)[0].id
    _time("toggleProjectTask", lambda: controller.tasks.toggleProjectTask(active, task_id))
    _time("deleteProjectTask", lambda: controller.tasks.deleteProjectTask(active, task_id))

    for _ in range(3):
        _time(
            "setViewFilter(search)",
            lambda: controller.ui_controller.setViewFilter("query", "skill"),
        )
        _time(
            "setViewFilter(clear)",
            lambda: controller.ui_controller.setViewFilter("query", ""),
        )

    print("\n=== ACTION TIMINGS (ms) ===")
    for label, elapsed in TIMINGS:
        print(f"{label:44s} {elapsed:9.2f}")

    groups: dict[str, list[float]] = {}
    for label, elapsed in TIMINGS:
        key = label.split("(")[0]
        groups.setdefault(key, []).append(elapsed)
    print("\n=== GROUPED (ms) ===")
    for key, values in groups.items():
        print(f"{key:30s} n={len(values):3d} total={sum(values):8.2f} max={max(values):8.2f}")

    profiler = cProfile.Profile()
    profiler.enable()
    controller.refreshSkills("perf-profile", True)
    controller.setCurrentProject(labels[1])
    controller.setCurrentProject(labels[0])
    controller.tasks.projectTaskCounts
    controller.tasks.currentProjectTasks
    profiler.disable()

    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats(25)
    print("\n=== cProfile (refresh + project switches + task reads) ===")
    print(stream.getvalue())

    shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()
