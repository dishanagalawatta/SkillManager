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


def update_custom_command_file(
    *,
    local_path: str,
    name: str,
    body: str,
) -> CommandCreateResult:
    """Updates an existing command file in place. Renames file if name changed."""
    path = Path(local_path)
    if not path.is_file():
        return CommandCreateResult(False, f"Error: Command file not found at {local_path}")

    try:
        content = path.read_text(encoding="utf-8-sig")
        from skill_manager.core.parsing.base import split_frontmatter

        metadata, _ = split_frontmatter(content)
    except Exception as exc:
        return CommandCreateResult(False, f"Error reading command file: {exc}")

    category = metadata.get("category", "") if metadata else ""

    new_filename = build_command_filename(name)
    new_path = path.parent / new_filename

    if new_path.exists() and new_path != path:
        return CommandCreateResult(False, f"Error: Command {new_filename} already exists")

    new_content = build_command_content(name, body, category)

    try:
        new_path.write_text(new_content, encoding="utf-8")
        if new_path != path:
            path.unlink()
    except Exception as exc:
        return CommandCreateResult(False, f"Error updating command: {exc}", path)

    return CommandCreateResult(True, f"Updated command: {new_path.name}", new_path)


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
