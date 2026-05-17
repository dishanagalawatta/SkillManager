import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from skill_manager.core.quick_copy import project_label


@dataclass(frozen=True)
class CommandCreateResult:
    ok: bool
    message: str
    path: Path | None = None


def find_target_for_project(project_label_name: str, targets: list[str]) -> Path | None:
    for target in targets:
        target_path = Path(target)
        if project_label(target_path) == project_label_name:
            return target_path
    return None


def build_command_filename(name: str, client: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return f"{safe_name}.{client}.md"


def build_command_content(
    name: str,
    client: str,
    body: str,
    category: str,
    created_on: date | None = None,
) -> str:
    created_on = created_on or date.today()
    return (
        "---\n"
        f"name: {name}\n"
        f"client: {client}\n"
        f"category: {category}\n"
        "type: command\n"
        f"date: {created_on.strftime('%Y-%m-%d')}\n"
        "---\n\n"
        f"{body}"
    )


def create_custom_command_file(
    *,
    name: str,
    client: str,
    body: str,
    project_label_name: str,
    category: str,
    targets: list[str],
    created_on: date | None = None,
) -> CommandCreateResult:
    if not name:
        return CommandCreateResult(False, "Error: Command name is required")

    if not project_label_name or project_label_name == "All Projects":
        return CommandCreateResult(False, "Error: Please select a specific Project")

    target_path = find_target_for_project(project_label_name, targets)
    if not target_path:
        return CommandCreateResult(False, f"Error: Could not find target for {project_label_name}")

    filename = build_command_filename(name, client)
    manuals_dir = target_path / "manuals"
    file_path = manuals_dir / filename
    if file_path.exists():
        return CommandCreateResult(False, f"Error: Command {filename} already exists", file_path)

    try:
        manuals_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            build_command_content(name, client, body, category, created_on),
            encoding="utf-8",
        )
    except Exception as exc:
        return CommandCreateResult(False, f"Error creating command: {exc}", file_path)

    return CommandCreateResult(True, f"Created command: {filename}", file_path)
