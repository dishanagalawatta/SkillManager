import os
import re
from dataclasses import dataclass, field
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
    needs_confirm: bool = False
    pending_removals: list[str] = field(default_factory=list)
    set_membership: str = ""  # "canonical" | "fanout_add" | "fanout_skip" | "removal"


def find_project_path_by_label(
    project_label_name: str,
    project_paths: list[str],
    *,
    project_aliases: dict[str, str] | None = None,
) -> Path | None:
    for path in project_paths:
        project_path = Path(path)
        if project_label(project_path, project_aliases=project_aliases) == project_label_name:
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
    project_aliases: dict[str, str] | None = None,
    on_conflict: str | None = None,
) -> CommandUpdateResult:
    """Updates an existing command file in place.

    - Renames the file if ``name`` changed.
    - Moves the file to a different project's commands dir if
    - ``project_label_name`` resolves to a different project than the
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
        candidate = find_project_path_by_label(
            project_label_name, project_paths, project_aliases=project_aliases
        )
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
    new_content = build_command_content(name, body, effective_category)

    if new_path.exists() and new_path != path:
        if not on_conflict:
            try:
                existing_content = new_path.read_text(encoding="utf-8-sig")
            except Exception:
                existing_content = None
            if existing_content == new_content:
                return CommandUpdateResult(
                    ok=True,
                    message=f"Already up to date: {new_path.name}",
                    path=new_path,
                )
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
    project_aliases: dict[str, str] | None = None,
    created_on: date | None = None,
) -> CommandCreateResult:
    if not name:
        return CommandCreateResult(False, "Error: Command name is required")

    if not project_label_name or project_label_name == "All Projects":
        return CommandCreateResult(False, "Error: Please select a specific Project")

    project_path = find_project_path_by_label(
        project_label_name, project_paths, project_aliases=project_aliases
    )
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


def find_command_holder_projects(
    command_name: str,
    project_paths: list[str],
    *,
    project_aliases: dict[str, str] | None = None,
) -> list[str]:
    """Return the list of project labels whose .agents/commands/ contains ``command_name``.

    ``command_name`` is the stem (no extension). Each project is checked
    for ``<root>/.agents/commands/<safe_name>.md``.
    """
    safe_name = build_command_filename(command_name)
    holders: list[str] = []
    for pp in project_paths:
        project_path = Path(pp)
        commands_dir = project_root_for_project(project_path) / ".agents" / "commands"
        if (commands_dir / safe_name).exists():
            holders.append(project_label(project_path, project_aliases=project_aliases))
    return holders


def create_custom_command_files_multi(
    *,
    name: str,
    body: str,
    project_labels: list[str],
    category: str,
    project_paths: list[str],
    project_aliases: dict[str, str] | None = None,
    created_on: date | None = None,
) -> list[CommandCreateResult]:
    """Create one command file per selected project.

    Delegates to ``create_custom_command_file`` for each label.
    Returns a list of results — one per project. Callers aggregate.
    """
    return [
        create_custom_command_file(
            name=name,
            body=body,
            project_label_name=label,
            category=category,
            project_paths=project_paths,
            project_aliases=project_aliases,
            created_on=created_on,
        )
        for label in project_labels
    ]


def update_custom_command_file_multi(
    *,
    local_path: str,
    name: str,
    body: str,
    category: str | None = None,
    project_labels: list[str],
    project_paths: list[str],
    project_aliases: dict[str, str] | None = None,
    on_conflict: str | None = None,
    confirmed_removals: list[str] | None = None,
) -> list[CommandUpdateResult]:
    """Update a command across multiple projects.

    - Computes which projects currently hold the command and determines
      ``add_set``, ``keep_set``, and ``remove_set``.
    - Canonical project is chosen from ``keep_set`` (first label) or,
      if empty, from ``add_set`` (first label).
    - If ``remove_set`` is non-empty and ``confirmed_removals`` is None,
      returns early with ``needs_confirm=True`` and ``pending_removals``
      set — no files are deleted.
    - If ``confirmed_removals`` is provided, deletes files for the
      intersection ``remove_set ∩ confirmed_removals``.
    - Fan-out copies go to ``add_set`` only; ``keep_set`` labels are
      skipped.

    Returns a list of results — one per project.
    """
    results: list[CommandUpdateResult] = []

    if not project_labels:
        return [CommandUpdateResult(False, "No projects selected")]

    stem = Path(local_path).stem
    current_holders = find_command_holder_projects(
        stem, project_paths, project_aliases=project_aliases
    )
    add_set = sorted(set(project_labels) - set(current_holders))
    keep_set = sorted(set(current_holders) & set(project_labels))
    remove_set = sorted(set(current_holders) - set(project_labels))

    # Guard: need confirmation before any deletions
    if remove_set and confirmed_removals is None:
        return [
            CommandUpdateResult(
                ok=True,
                message="Confirmation required for project removals",
                needs_confirm=True,
                pending_removals=list(remove_set),
            )
        ]

    # Determine canonical label: prefer the original file's project to
    # avoid moving the file to a different project (which surprises users).
    # Find the raw project path whose root matches the local file's root,
    # then compute the label the same way find_command_holder_projects does.
    local_root = project_root_for_project(Path(local_path))
    original_project_label = None
    for pp in project_paths:
        if project_root_for_project(Path(pp)) == local_root:
            original_project_label = project_label(Path(pp), project_aliases=project_aliases)
            break
    if original_project_label is None:
        original_project_label = project_label(
            Path(local_path).parent, project_aliases=project_aliases
        )
    if original_project_label in keep_set:
        canonical_label = original_project_label
    elif keep_set:
        canonical_label = keep_set[0]
    elif add_set:
        canonical_label = add_set[0]
    else:
        # Nothing to add and nothing to keep — only removals remain
        canonical_label = project_labels[0]

    # Phase 1: canonical move/update
    canonical = update_custom_command_file(
        local_path=local_path,
        name=name,
        body=body,
        category=category,
        project_label_name=canonical_label,
        project_paths=project_paths,
        project_aliases=project_aliases,
        on_conflict=on_conflict,
    )
    results.append(
        CommandUpdateResult(
            ok=canonical.ok,
            message=canonical.message,
            path=canonical.path,
            needs_conflict_resolution=canonical.needs_conflict_resolution,
            conflicting_path=canonical.conflicting_path,
            suggested_rename=canonical.suggested_rename,
            needs_confirm=canonical.needs_confirm,
            pending_removals=canonical.pending_removals,
            set_membership="canonical",
        )
    )

    # Phase 2: fan-out to add_set (skip keep_set labels)
    if canonical.ok and canonical.path and canonical.path.is_file():
        new_content = canonical.path.read_text(encoding="utf-8")
        for label in add_set:
            # Skip the canonical label — already handled above
            if label == canonical_label:
                continue
            target = find_project_path_by_label(
                label, project_paths, project_aliases=project_aliases
            )
            if not target:
                results.append(
                    CommandUpdateResult(
                        False, f"Error: Could not find project directory for {label}"
                    )
                )
                continue
            target_dir = project_root_for_project(target) / ".agents" / "commands"
            target_file = target_dir / canonical.path.name
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                if target_file.exists():
                    existing = target_file.read_text(encoding="utf-8-sig")
                    if existing == new_content:
                        results.append(
                            CommandUpdateResult(
                                True,
                                f"Already up to date: {target_file.name}",
                                target_file,
                                set_membership="fanout_skip",
                            )
                        )
                        continue
                target_file.write_text(new_content, encoding="utf-8")
                results.append(
                    CommandUpdateResult(
                        True,
                        f"Updated command: {target_file.name}",
                        target_file,
                        set_membership="fanout_add",
                    )
                )
            except Exception as exc:
                results.append(
                    CommandUpdateResult(False, f"Error updating command in {label}: {exc}")
                )

    # Phase 3: confirmed removals
    if remove_set and confirmed_removals is not None:
        actual_removals = sorted(set(remove_set) & set(confirmed_removals))
        for label in actual_removals:
            target = find_project_path_by_label(
                label, project_paths, project_aliases=project_aliases
            )
            if not target:
                results.append(
                    CommandUpdateResult(
                        False, f"Error: Could not find project directory for {label}"
                    )
                )
                continue
            commands_dir = project_root_for_project(target) / ".agents" / "commands"
            removal_target = commands_dir / build_command_filename(name)
            try:
                if removal_target.is_file():
                    removal_target.unlink()
                    results.append(
                        CommandUpdateResult(
                            True,
                            f"Removed command from {label}: {removal_target.name}",
                            set_membership="removal",
                        )
                    )
                else:
                    results.append(
                        CommandUpdateResult(
                            True,
                            f"No command file to remove in {label}",
                            set_membership="removal",
                        )
                    )
            except Exception as exc:
                results.append(
                    CommandUpdateResult(False, f"Error removing command from {label}: {exc}")
                )

    return results


def find_referenced_skills_in_command(
    local_path: str,
    all_skills: list,
) -> list:
    """Parse a command ``.md`` file and return the skills it references.

    Returns an empty list if the file is missing, unreadable, or has no
    skill references.  Order is stable; duplicates are removed.
    """
    path = Path(local_path)
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    from skill_manager.core.parsing.base import split_frontmatter

    _, body = split_frontmatter(text)
    from skill_manager.core.skill_references import resolve_referenced_skills

    return resolve_referenced_skills(body, all_skills)
