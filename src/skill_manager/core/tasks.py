"""Per-project task list persistence.

Tasks live in ``DATA_DIR / "project_tasks.json"`` and are written atomically
under the same cross-process lock the rest of the JSON persistence uses, so
a second SkillManager instance (or the headless MCP process) can never write
a half-written file.

Project keys are canonicalised the same way the rest of the app
canonicalises project paths, so a task list is never orphaned because the
path was stored with a different case or separator.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from skill_manager.core.config import DATA_DIR, resolve_data_file
from skill_manager.core.copier import canonical_key
from skill_manager.core.persistence import _atomic_write_json
from skill_manager.core.schemas import ProjectTaskRecord, ProjectTasksState
from skill_manager.utils.cooperative_lock import FileLock, LockTimeout

logger = logging.getLogger(__name__)

PROJECT_TASKS_FILENAME = "project_tasks.json"

PRIORITIES = ("low", "medium", "high")


def _tasks_file() -> Path:
    return resolve_data_file(PROJECT_TASKS_FILENAME)


def project_task_key(project_path: str | Path) -> str:
    """Canonical key for a project path.

    Uses the same resolution + Windows case folding as the skill caches,
    so ``C:\\Users\\ADMIN\\P`` and ``c:/users/admin/P`` address the same
    task list.
    """
    if project_path is None or str(project_path).strip() == "":
        return ""
    return canonical_key(project_path)


def load_state() -> ProjectTasksState:
    """Load the persisted task state; a missing/corrupt file yields empty state."""
    path = _tasks_file()
    try:
        if not path.exists():
            return ProjectTasksState()
        import orjson

        raw = orjson.loads(path.read_bytes())
        return ProjectTasksState.model_validate(raw)
    except Exception as exc:
        logger.warning("Failed to load project tasks from %s: %s", path, exc)
        return ProjectTasksState()


def save_state(state: ProjectTasksState) -> bool:
    """Persist the task state atomically. Returns False when a peer holds the lock."""
    path = _tasks_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Cannot create task data dir %s: %s", path.parent, exc)
        return False

    payload = {
        "projects": {
            key: [record.model_dump() for record in records]
            for key, records in state.projects.items()
        }
    }
    try:
        with FileLock(str(path)):
            _atomic_write_json(str(path), payload)
        return True
    except LockTimeout:
        logger.warning("Task state write skipped: another instance holds the lock")
        return False
    except Exception as exc:
        logger.warning("Failed to save project tasks to %s: %s", path, exc)
        return False


def _mutate(mutator) -> ProjectTasksState:
    """Apply *mutator* to the loaded state and persist the result."""
    state = load_state()
    mutator(state)
    save_state(state)
    return state


def get_tasks(project_path: str | Path) -> list[ProjectTaskRecord]:
    """Return the task list of *project_path* (empty when it has none)."""
    key = project_task_key(project_path)
    if not key:
        return []
    return list(load_state().projects.get(key, []))


def _ordered(records: list[ProjectTaskRecord]) -> list[ProjectTaskRecord]:
    """Sort by ``order`` then creation time, and renumber 0..n-1."""
    ordered = sorted(records, key=lambda r: (r.order, r.created_at, r.id))
    for index, record in enumerate(ordered):
        record.order = index
    return ordered


def add_task(
    project_path: str | Path,
    title: str,
    priority: str = "medium",
    description: str = "",
    linked_skills: list[str] | None = None,
) -> ProjectTaskRecord | None:
    """Create a task in *project_path* and persist it."""
    key = project_task_key(project_path)
    clean_title = (title or "").strip()
    if not key or not clean_title:
        return None

    if priority not in PRIORITIES:
        priority = "medium"

    now = time.time()
    record = ProjectTaskRecord(
        title=clean_title,
        description=description or "",
        priority=priority,
        linked_skills=list(linked_skills or []),
        created_at=now,
        updated_at=now,
    )

    def _apply(state: ProjectTasksState) -> None:
        records = state.projects.setdefault(key, [])
        record.order = len(records)
        records.append(record)

    _mutate(_apply)
    return record


def update_task(
    project_path: str | Path,
    task_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    linked_skills: list[str] | None = None,
) -> ProjectTaskRecord | None:
    """Update a task's fields. ``None`` arguments leave the field untouched."""
    key = project_task_key(project_path)
    if not key:
        return None
    found: ProjectTaskRecord | None = None

    def _apply(state: ProjectTasksState) -> None:
        nonlocal found
        for record in state.projects.get(key, []):
            if record.id != task_id:
                continue
            if title is not None:
                clean = title.strip()
                if clean:
                    record.title = clean
            if description is not None:
                record.description = description
            if priority is not None and priority in PRIORITIES:
                record.priority = priority
            if linked_skills is not None:
                record.linked_skills = list(linked_skills)
            record.updated_at = time.time()
            found = record
            break

    _mutate(_apply)
    return found


def toggle_task(project_path: str | Path, task_id: str) -> ProjectTaskRecord | None:
    """Flip a task's completed flag."""
    key = project_task_key(project_path)
    if not key:
        return None
    found: ProjectTaskRecord | None = None

    def _apply(state: ProjectTasksState) -> None:
        nonlocal found
        for record in state.projects.get(key, []):
            if record.id == task_id:
                record.completed = not record.completed
                record.updated_at = time.time()
                found = record
                break

    _mutate(_apply)
    return found


def delete_task(project_path: str | Path, task_id: str) -> bool:
    """Delete a task. Returns True when a task was removed."""
    key = project_task_key(project_path)
    if not key:
        return False
    removed = False

    def _apply(state: ProjectTasksState) -> None:
        nonlocal removed
        records = state.projects.get(key, [])
        kept = [record for record in records if record.id != task_id]
        removed = len(kept) != len(records)
        if removed:
            state.projects[key] = _ordered(kept)

    _mutate(_apply)
    return removed


def clear_completed_tasks(project_path: str | Path) -> int:
    """Remove every completed task. Returns the number of removed tasks."""
    key = project_task_key(project_path)
    if not key:
        return 0
    removed_count = 0

    def _apply(state: ProjectTasksState) -> None:
        nonlocal removed_count
        records = state.projects.get(key, [])
        kept = [record for record in records if not record.completed]
        removed_count = len(records) - len(kept)
        if removed_count:
            state.projects[key] = _ordered(kept)

    _mutate(_apply)
    return removed_count


def reorder_tasks(project_path: str | Path, ordered_ids: list[str]) -> bool:
    """Reorder the task list to match *ordered_ids*.

    Tasks that are not named in *ordered_ids* keep their relative order and
    are appended after the named ones.
    """
    key = project_task_key(project_path)
    if not key:
        return False
    changed = False

    def _apply(state: ProjectTasksState) -> None:
        nonlocal changed
        records = state.projects.get(key, [])
        by_id = {record.id: record for record in records}
        ordered: list[ProjectTaskRecord] = []
        seen: set[str] = set()
        for task_id in ordered_ids or []:
            record = by_id.get(task_id)
            if record is not None and task_id not in seen:
                ordered.append(record)
                seen.add(task_id)
        for record in records:
            if record.id not in seen:
                ordered.append(record)
                seen.add(record.id)
        # The requested order is authoritative — renumber it without
        # re-sorting (sorting by the OLD order field would undo the move).
        changed = [r.id for r in ordered] != [r.id for r in records]
        for index, record in enumerate(ordered):
            record.order = index
        state.projects[key] = ordered

    _mutate(_apply)
    return changed


def counts_for_project(project_path: str | Path) -> tuple[int, int]:
    """Return ``(active, completed)`` task counts for *project_path*."""
    records = get_tasks(project_path)
    active = sum(1 for record in records if not record.completed)
    completed = len(records) - active
    return active, completed


def records_to_dicts(records: list[ProjectTaskRecord]) -> list[dict[str, Any]]:
    """Convert task records to plain dicts for the QML layer."""
    return [record.model_dump() for record in records]


__all__ = [
    "DATA_DIR",
    "PRIORITIES",
    "PROJECT_TASKS_FILENAME",
    "add_task",
    "clear_completed_tasks",
    "counts_for_project",
    "delete_task",
    "get_tasks",
    "load_state",
    "project_task_key",
    "records_to_dicts",
    "reorder_tasks",
    "save_state",
    "toggle_task",
    "update_task",
]
