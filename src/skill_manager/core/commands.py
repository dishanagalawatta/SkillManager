import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from skill_manager.core.quick_copy import project_label, project_root_for_project


@dataclass(frozen=True)
class CommandCreateResult:
    ok: bool
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class CommandUpdateResult:
    ok: bool
    message: str
    path: Path | None = None
    needs_conflict_resolution: bool = False
    conflicting_path: Path | None = None
    suggested_rename: str | None = None


def find_project_path_by_label(project_label_name: str, project_paths: list[str]) -> Path | None:
    for path in project_paths:
        project_path = Path(path)
        if project_label(project_path) == project_label_name:
            return project_path
    return None


def build_command_filename(name: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return f"{safe_name}.md"


def build_command_content(
    name: str,
    body: str,
    category: str,
    created_on: date | None = None,
) -> str:
    created_on = created_on or date.today()
    return (
        "---\n"
        f"name: {name}\n"
        f"category: {category}\n"
        "type: command\n"
        f"date: {created_on.strftime('%Y-%m-%d')}\n"
        "---\n\n"
        f"{body}"
    )


def _next_non_conflicting(target_dir: Path, safe_name: str) -> str:
    stem, suffix = os.path.splitext(safe_name)
    i = 1
    while (target_dir / f"{stem}-{i}{suffix}").exists():
        i += 1
    return f"{stem}-{i}{suffix}"


def update_custom_command_file(
    *,
    local_path: str,
    name: str,
    body: str,
    category: str | None = None,
    project_label_name: str | None = None,
    project_paths: list[str] | None = None,
    on_conflict: str | None = None,
) -> CommandUpdateResult:
    """Updates an existing command file in place.

    - Renames the file if ``name`` changed.
    - Moves the file to a different project's commands dir if
      ``project_label_name`` resolves to a different project than the
      file's current project.
    - If ``category`` is falsy, preserves the existing frontmatter
      category; otherwise writes the new value.
    """
    path = Path(local_path)
    if not path.is_file():
        return CommandUpdateResult(False, f"Error: Command file not found at {local_path}")

    try:
        content = path.read_text(encoding="utf-8-sig")
        from skill_manager.core.parsing.base import split_frontmatter

        metadata, _ = split_frontmatter(content)
    except Exception as exc:
        return CommandUpdateResult(False, f"Error reading command file: {exc}")

    existing_category = metadata.get("category", "") if metadata else ""
    effective_category = category if category else existing_category

    new_filename = build_command_filename(name)

    # Resolve target project directory (None = "stay in current project").
    target_project_path: Path | None = None
    if project_label_name and project_paths is not None:
        candidate = find_project_path_by_label(project_label_name, project_paths)
        if candidate is None:
            return CommandUpdateResult(
                False, f"Error: Could not find project directory for {project_label_name}"
            )
        if candidate.resolve() != project_root_for_project(path.parent).resolve():
            target_project_path = candidate

    if target_project_path is not None:
        target_dir = project_root_for_project(target_project_path) / ".agents" / "commands"
    else:
        target_dir = path.parent

    new_path = target_dir / new_filename

    if new_path.exists() and new_path != path:
        if not on_conflict:
            return CommandUpdateResult(
                ok=False,
                message=f"File already exists: {new_path}",
                needs_conflict_resolution=True,
                conflicting_path=new_path,
                suggested_rename=_next_non_conflicting(target_dir, new_filename),
            )
        if on_conflict == "cancel":
            return CommandUpdateResult(False, "Cancelled by user", path=path)
        if on_conflict == "rename":
            new_path = target_dir / _next_non_conflicting(target_dir, new_filename)
        # "overwrite" → keep new_path; write_text will replace it

    new_content = build_command_content(name, body, effective_category)

    try:
        if target_project_path is not None:
            target_dir.mkdir(parents=True, exist_ok=True)
        new_path.write_text(new_content, encoding="utf-8")
        if new_path != path:
            path.unlink()
    except Exception as exc:
        return CommandUpdateResult(False, f"Error updating command: {exc}", path=path)

    return CommandUpdateResult(True, f"Updated command: {new_path.name}", new_path)


def create_custom_command_file(
    *,
    name: str,
    body: str,
    project_label_name: str,
    category: str,
    project_paths: list[str],
    created_on: date | None = None,
) -> CommandCreateResult:
    if not name:
        return CommandCreateResult(False, "Error: Command name is required")

    if not project_label_name or project_label_name == "All Projects":
        return CommandCreateResult(False, "Error: Please select a specific Project")

    project_path = find_project_path_by_label(project_label_name, project_paths)
    if not project_path:
        return CommandCreateResult(
            False, f"Error: Could not find project directory for {project_label_name}"
        )

    filename = build_command_filename(name)
    project_root = project_root_for_project(project_path)
    commands_dir = project_root / ".agents" / "commands"
    file_path = commands_dir / filename
    if file_path.exists():
        return CommandCreateResult(False, f"Error: Command {filename} already exists", file_path)

    try:
        commands_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            build_command_content(name, body, category, created_on),
            encoding="utf-8",
        )
    except Exception as exc:
        return CommandCreateResult(False, f"Error creating command: {exc}", file_path)

    return CommandCreateResult(True, f"Created command: {filename}", file_path)
