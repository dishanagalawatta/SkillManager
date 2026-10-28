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

import hashlib
import logging
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from skill_manager.core.config import DATA_DIR, get_app_data_dir, resolve_data_file
from skill_manager.core.copier import canonical_key
from skill_manager.core.persistence import _atomic_write_json
from skill_manager.core.schemas import ProjectTaskRecord, ProjectTasksState
from skill_manager.utils.cooperative_lock import FileLock, LockTimeout

logger = logging.getLogger(__name__)

PROJECT_TASKS_FILENAME = "project_tasks.json"

PRIORITIES = ("low", "medium", "high")

#: Attachments are images only — a task note is not a file manager.
ATTACHMENTS_DIRNAME = "task_attachments"
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


def _tasks_file() -> Path:
    return resolve_data_file(PROJECT_TASKS_FILENAME)


def attachments_root() -> Path:
    """Directory holding every task attachment, one subtree per project."""
    return get_app_data_dir() / ATTACHMENTS_DIRNAME


def _attachment_dir(project_path: str | Path) -> Path | None:
    """Per-project attachment directory, derived from the canonical key.

    The key is an absolute path, so it is hashed instead of used verbatim:
    that keeps the directory name filesystem-safe on every platform and
    stable across case/separator differences. ``None`` means "no project".
    """
    key = project_task_key(project_path)
    if not key:
        return None
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return attachments_root() / digest


def _source_path(source: Any) -> Path | None:
    """Turn a QML file URL (``file:///…``) or plain path into a local path."""
    raw = str(source or "").strip()
    if not raw:
        return None
    if raw.startswith("file:"):
        raw = unquote(urlparse(raw).path)
        # Windows file URLs arrive as /C:/dir/file.png.
        if len(raw) > 2 and raw[0] == "/" and raw[2] == ":":
            raw = raw[1:]
    try:
        return Path(raw).expanduser()
    except (OSError, ValueError):
        return None


def _store_bytes(project_path: str | Path, data: bytes, suffix: str) -> str:
    clean_suffix = ("." + str(suffix or "").lstrip(".")).lower()
    if clean_suffix not in IMAGE_SUFFIXES or not data:
        return ""
    if len(data) > MAX_ATTACHMENT_BYTES:
        logger.warning("Task attachment rejected: %d bytes is over the limit", len(data))
        return ""
    target_dir = _attachment_dir(project_path)
    if target_dir is None:
        return ""
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{uuid.uuid4().hex[:12]}{clean_suffix}"
        target.write_bytes(data)
    except OSError as exc:
        logger.warning("Could not store task attachment: %s", exc)
        return ""
    return str(target)


def store_attachment(project_path: str | Path, source: Any) -> str:
    """Copy an image *source* into the task attachment store.

    Returns the stored path, or ``""`` when the source is missing, not an
    image, or cannot be copied.
    """
    path = _source_path(source)
    if path is None or not path.is_file():
        return ""
    suffix = path.suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        return ""
    try:
        if path.stat().st_size > MAX_ATTACHMENT_BYTES:
            logger.warning("Task attachment rejected: %s is over the size limit", path)
            return ""
        data = path.read_bytes()
    except OSError as exc:
        logger.warning("Could not read task attachment %s: %s", path, exc)
        return ""
    return _store_bytes(project_path, data, suffix)


def store_attachment_bytes(project_path: str | Path, data: bytes, suffix: str = ".png") -> str:
    """Store in-memory image bytes (e.g. a pasted screenshot)."""
    return _store_bytes(project_path, data, suffix)


def _remove_attachment_files(paths: list[str] | None) -> None:
    """Delete attachment files, but only ones that live in the store."""
    root = attachments_root()
    try:
        root_resolved = root.resolve()
    except OSError:
        return
    for raw in paths or []:
        candidate = _source_path(raw)
        if candidate is None:
            continue
        try:
            candidate.resolve().relative_to(root_resolved)
        except (OSError, ValueError):
            continue
        try:
            candidate.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not delete task attachment %s: %s", candidate, exc)


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


def _clean_attachments(attachments: Any) -> list[str]:
    """Normalise an attachment list from QML (a JS array or ``None``)."""
    cleaned: list[str] = []
    for raw in attachments or []:
        text = str(raw or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def add_task(
    project_path: str | Path,
    title: str,
    priority: str = "medium",
    description: str = "",
    linked_skills: list[str] | None = None,
    attachments: list[str] | None = None,
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
        attachments=_clean_attachments(attachments),
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
    attachments: list[str] | None = None,
) -> ProjectTaskRecord | None:
    """Update a task's fields. ``None`` arguments leave the field untouched."""
    key = project_task_key(project_path)
    if not key:
        return None
    found: ProjectTaskRecord | None = None
    dropped: list[str] = []

    def _apply(state: ProjectTasksState) -> None:
        nonlocal found, dropped
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
            if attachments is not None:
                cleaned = _clean_attachments(attachments)
                dropped = [path for path in record.attachments if path not in cleaned]
                record.attachments = cleaned
            record.updated_at = time.time()
            found = record
            break

    _mutate(_apply)
    # Removed attachments should not linger on disk forever.
    _remove_attachment_files(dropped)
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
    orphaned: list[str] = []

    def _apply(state: ProjectTasksState) -> None:
        nonlocal removed, orphaned
        records = state.projects.get(key, [])
        kept = [record for record in records if record.id != task_id]
        removed = len(kept) != len(records)
        if removed:
            gone = [record for record in records if record.id == task_id]
            orphaned = [path for record in gone for path in record.attachments]
            state.projects[key] = _ordered(kept)

    _mutate(_apply)
    if removed:
        _remove_attachment_files(orphaned)
    return removed


def clear_completed_tasks(project_path: str | Path) -> int:
    """Remove every completed task. Returns the number of removed tasks."""
    key = project_task_key(project_path)
    if not key:
        return 0
    removed_count = 0
    orphaned: list[str] = []

    def _apply(state: ProjectTasksState) -> None:
        nonlocal removed_count, orphaned
        records = state.projects.get(key, [])
        kept = [record for record in records if not record.completed]
        removed_count = len(records) - len(kept)
        if removed_count:
            orphaned = [
                path for record in records if record.completed for path in record.attachments
            ]
            state.projects[key] = _ordered(kept)

    _mutate(_apply)
    if removed_count:
        _remove_attachment_files(orphaned)
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
    "ATTACHMENTS_DIRNAME",
    "DATA_DIR",
    "IMAGE_SUFFIXES",
    "MAX_ATTACHMENT_BYTES",
    "PRIORITIES",
    "PROJECT_TASKS_FILENAME",
    "add_task",
    "attachments_root",
    "clear_completed_tasks",
    "counts_for_project",
    "delete_task",
    "get_tasks",
    "load_state",
    "project_task_key",
    "records_to_dicts",
    "reorder_tasks",
    "save_state",
    "store_attachment",
    "store_attachment_bytes",
    "toggle_task",
    "update_task",
]
