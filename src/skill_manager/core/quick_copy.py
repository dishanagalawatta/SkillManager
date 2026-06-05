import logging
import os
import shutil
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pathspec

logger = logging.getLogger(__name__)

CLIENT_FORMATS = {"Codex", "Gemini CLI", "Antigravity", "Plain Text"}


def _resolve_resilient_path(path_str):
    """Resolve a skill path and auto-detect .agents/skills for project roots."""
    if not path_str:
        return Path()

    path = Path(os.path.expanduser(str(path_str).strip()))
    try:
        if path.exists():
            # Auto-detect .agents/skills if project root was provided
            if path.is_dir() and path.name.lower() not in ("skills", ".agents"):
                potential = path / ".agents" / "skills"
                if potential.exists() and potential.is_dir():
                    return potential.resolve()
            return path.resolve()
    except OSError:
        pass

    return path


def discover_package_skills(sources, parse_skill_md, categorize_skill, build_search_text):
    """Discover skills from master package folders (config['sources']).

    Returns a flat list of skill dicts, each tagged with ``is_source=True``.
    Deduplicates by resolved path so the same folder listed twice is only
    scanned once.

    Args:
        sources: Iterable of source folder paths (from config["sources"]).
        parse_skill_md: Callable(path) -> dict with skill metadata.
        categorize_skill: Callable(name, description) -> category string.
        build_search_text: Callable(skill_dict) -> search text string.

    Returns:
        List[dict] — one entry per discovered skill.
    """
    skills = []
    seen_sources = set()
    unique_sources = []

    for source in sources:
        resolved_source = _resolve_resilient_path(source)
        if not resolved_source or not resolved_source.is_dir():
            continue

        source_key = os.path.normcase(str(resolved_source))
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        unique_sources.append(resolved_source)

    if not unique_sources:
        return []

    def scan_source(resolved_source):
        source_skills = []
        ignore_spec = _load_ignore_spec(resolved_source)
        for child in sorted(resolved_source.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir():
                continue
            if _is_ignored(child, resolved_source, ignore_spec):
                continue
            skill_md_path = child / "SKILL.md"
            if not skill_md_path.is_file():
                continue

            skill_data = parse_skill_md(str(skill_md_path))
            # Minimal normalization if not already done by cached wrapper
            if not skill_data.get("name"):
                skill_data["name"] = child.name
            skill_data["folder_name"] = child.name
            skill_data["local_path"] = str(child)
            skill_data["skill_md_path"] = str(skill_md_path)
            skill_data["source_path"] = str(resolved_source)
            skill_data["project_path"] = str(resolved_source)
            skill_data["project_label"] = "Master Library"
            skill_data["project_root"] = str(resolved_source)
            skill_data["skill_base_relative"] = _skill_base_relative(resolved_source)
            skill_data["is_package"] = True
            skill_data["is_source"] = True  # Compatibility

            # These might be no-ops if parse_skill_md was our cached wrapper
            if not skill_data.get("main_category"):
                skill_data.setdefault("metadata", {})
                cat_info = categorize_skill(
                    skill_data.get("name", ""),
                    _classification_text(skill_data),
                    skill_data.get("metadata", {}),
                )
                skill_data["main_category"] = cat_info.get("main_category", "")
                skill_data["category"] = cat_info.get("sub_category", "")

            if not skill_data.get("search_text"):
                skill_data["search_text"] = build_search_text(skill_data)

            source_skills.append(skill_data)
        return source_skills

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(scan_source, src) for src in unique_sources]
        for future in futures:
            try:
                skills.extend(future.result())
            except Exception as e:
                logger.warning("[DISCOVERY] Error scanning source: %s", e)

    return skills


def discover_single_project(
    project: str,
    parse_skill_md: Callable,
    categorize_skill: Callable,
    build_search_text: Callable,
    project_aliases: dict[str, str] = None,
) -> dict[str, Any] | None:
    """Discovers skills in a single project path.

    Args:
        project: Project path to discover.
        parse_skill_md: Callable to parse SKILL.md.
        categorize_skill: Callable to categorize a skill.
        build_search_text: Callable to build search text.
        project_aliases: Project name/alias mapping.

    Returns:
        dict with project metadata and discovered skills, or None.
    """
    if project_aliases is None:
        project_aliases = {}

    resolved_project = _resolve_resilient_path(project)
    if not resolved_project or not resolved_project.is_dir():
        return None

    project_key = os.path.normcase(str(resolved_project))
    skills = []
    ignore_spec = _load_ignore_spec(resolved_project)

    for child in sorted(resolved_project.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir():
            continue
        if _is_ignored(child, resolved_project, ignore_spec):
            continue
        skill_md_path = child / "SKILL.md"
        if not skill_md_path.is_file():
            continue

        skill_data = parse_skill_md(str(skill_md_path))
        if not skill_data.get("name"):
            skill_data["name"] = child.name
        skill_data["folder_name"] = child.name
        skill_data["local_path"] = str(child)
        skill_data["skill_md_path"] = str(skill_md_path)
        skill_data["project_key"] = project_key
        skill_data["project_path"] = str(resolved_project)
        skill_data["project_root"] = str(_project_root_for_project(resolved_project))
        skill_data["skill_base_relative"] = _skill_base_relative(resolved_project)
        skill_data["project_label"] = project_label(resolved_project, project_aliases, str(project))
        skill_data.setdefault("metadata", {})
        cat_info = categorize_skill(
            skill_data.get("name", ""),
            _classification_text(skill_data),
            skill_data.get("metadata", {}),
        )
        skill_data["main_category"] = cat_info.get("main_category", "")
        skill_data["category"] = cat_info.get("sub_category", "")
        skill_data["search_text"] = build_search_text(skill_data)
        skills.append(skill_data)

    if skills:
        project_root = _project_root_for_project(resolved_project)
        return {
            "project_path": str(resolved_project),
            "project_root": str(project_root),
            "project_label": project_label(resolved_project, project_aliases, str(project)),
            "skill_base_relative": _skill_base_relative(resolved_project),
            "project_key": project_key,
            "skills": skills,
        }
    return None


def discover_project_skills(
    projects: list[str],
    parse_skill_md: Callable,
    categorize_skill: Callable,
    build_search_text: Callable,
    project_aliases: dict[str, str] = None,
) -> list[dict[str, Any]]:
    """Discover skills from multiple project folders in parallel.

    Args:
        projects: List of project folder paths.
        parse_skill_md: Callable to parse SKILL.md.
        categorize_skill: Callable to categorize a skill.
        build_search_text: Callable to build search text.
        project_aliases: Project name/alias mapping.

    Returns:
        List of project dicts, each with discovered skills.
    """
    if project_aliases is None:
        project_aliases = {}

    seen_projects = set()
    unique_projects = []

    for project in projects:
        resolved_project = _resolve_resilient_path(project)
        if not resolved_project or not resolved_project.is_dir():
            continue
        project_key = os.path.normcase(str(resolved_project))
        if project_key in seen_projects:
            continue
        seen_projects.add(project_key)
        unique_projects.append(project)

    if not unique_projects:
        return []

    # Parallelize project discovery
    projects_list = []
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                discover_single_project,
                project,
                parse_skill_md,
                categorize_skill,
                build_search_text,
                project_aliases,
            )
            for project in unique_projects
        ]
        for future in futures:
            try:
                res = future.result()
                if res:
                    projects_list.append(res)
            except Exception as e:
                logger.warning("[DISCOVERY] Error scanning project: %s", e)

    return projects_list


def _normalize_path(path):
    if not path:
        return ""
    return os.path.normcase(os.path.normpath(path)).replace("\\", "/")


def _load_ignore_spec(root: Path):
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return None
    try:
        return pathspec.PathSpec.from_lines(
            "gitignore", gitignore.read_text(encoding="utf-8").splitlines()
        )
    except OSError:
        return None


def _is_ignored(path: Path, root: Path, spec) -> bool:
    if spec is None:
        return False
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return False
    return spec.match_file(relative) or spec.match_file(f"{relative}/")


def project_label(project_path, project_aliases=None, original_project=None):
    if project_aliases is None:
        project_aliases = {}

    norm_project = _normalize_path(project_path)
    norm_original = _normalize_path(original_project) if original_project else ""

    # Try using original project (exact or normalized)
    if original_project and original_project in project_aliases:
        return project_aliases[original_project]
    if norm_original and norm_original in project_aliases:
        return project_aliases[norm_original]

    # Try resolved path (exact or normalized)
    project_str = str(project_path)
    if project_str in project_aliases:
        return project_aliases[project_str]
    if norm_project in project_aliases:
        return project_aliases[norm_project]

    # Full scan for matching normalized keys
    for k, v in project_aliases.items():
        if _normalize_path(k) == norm_project or (
            norm_original and _normalize_path(k) == norm_original
        ):
            return v

    # Use standard format if no alias: "RootName (Base)"
    project_path_obj = Path(project_path)
    root = _project_root_for_project(project_path_obj)
    base = _skill_base_relative(project_path_obj)

    # Clean up the .agents/skills suffix if it exists
    if base == ".agents/skills" or base == ".agents\\skills":
        return f"{root.name}"
    if base.endswith("/.agents/skills") or base.endswith("\\.agents\\skills"):
        return f"{root.name} ({base[:-15]})"

    return f"{root.name} ({base})"


def format_project_skill_reference(skill, client_format):
    is_command = skill.get("is_command", False)
    local_path = Path(skill.get("local_path", ""))

    if is_command:
        # For commands, we want the path relative to the project root
        project_root = skill.get("project_root")
        if not project_root:
            # Fallback: try to find commands/ in the path
            try:
                command_idx = local_path.parts.index("commands")
                relative_path = "/".join(local_path.parts[command_idx:])
            except ValueError:
                relative_path = local_path.name
        else:
            try:
                relative_path = local_path.relative_to(project_root).as_posix()
            except ValueError:
                relative_path = local_path.name

        if client_format == "Codex":
            name = skill.get("name") or local_path.name
            return f"[${name}]({relative_path})"
        if client_format == "Antigravity":
            name = skill.get("name") or local_path.name
            return f"/skill:{name}"
        if client_format == "Gemini CLI":
            return f"@{relative_path}"
        return relative_path

    if client_format == "Codex":
        name = skill.get("name") or local_path.name
        path = skill.get("skill_md_path") or ""
        return f"[${name}]({path})"

    relative_path = project_skill_relative_path(skill)
    if client_format == "Antigravity":
        name = skill.get("name") or local_path.name
        return f"/skill:{name}"
    if client_format == "Gemini CLI":
        return f"@{relative_path}"
    return relative_path


def normalize_command_references(text):
    references = []
    seen = set()
    for line in str(text or "").splitlines():
        reference = normalize_command_reference(line)
        if not reference:
            continue
        key = reference.casefold()
        if key in seen:
            continue
        seen.add(key)
        references.append(reference)
    return references


def normalize_command_reference(value):
    reference = str(value or "").strip()
    if not reference:
        return ""
    if _looks_like_explicit_reference(reference):
        return reference
    return f"@{reference.lstrip('@')}"


def merge_command_references(existing, additions):
    merged = []
    seen = set()
    for reference in list(existing or []) + list(additions or []):
        normalized = normalize_command_reference(reference)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def _looks_like_explicit_reference(reference):
    lowered = reference.lower()
    if reference.startswith(("@", "[", ".", "/", "~")):
        return True
    if lowered.endswith(".md") or "/" in reference or "\\" in reference:
        return True
    return ":" in reference


def project_skill_relative_path(skill):
    base = str(skill.get("skill_base_relative") or "").replace("\\", "/").strip("/")
    folder = (
        str(skill.get("folder_name") or Path(skill.get("local_path", "")).name)
        .replace("\\", "/")
        .strip("/")
    )
    return f"{base}/{folder}/SKILL.md" if base else f"{folder}/SKILL.md"


def delete_project_skill_folders(skills):
    result = {"deleted": 0, "skipped": 0, "failed": 0, "details": []}
    for skill in skills:
        label = skill.get("name") or skill.get("folder_name") or "Unknown"
        source_path = Path(os.path.expanduser(str(skill.get("local_path") or ""))).resolve()
        project_path = Path(os.path.expanduser(str(skill.get("project_path") or ""))).resolve()
        error = _delete_validation_error(source_path, project_path)

        if error:
            result["skipped"] += 1
            result["details"].append(
                {"skill": label, "path": str(source_path), "status": "skipped", "message": error}
            )
            continue

        try:
            shutil.rmtree(source_path)
        except Exception as exc:
            result["failed"] += 1
            result["details"].append(
                {"skill": label, "path": str(source_path), "status": "failed", "message": str(exc)}
            )
            continue

        result["deleted"] += 1
        result["details"].append(
            {
                "skill": label,
                "path": str(source_path),
                "status": "deleted",
                "message": str(source_path),
            }
        )

    return result


def _delete_validation_error(source_path, project_path):
    if not project_path.is_dir():
        return f"Project folder does not exist: {project_path}"
    if not source_path.is_dir():
        return f"Skill folder does not exist: {source_path}"
    if source_path.parent != project_path:
        return f"Skill folder is not a direct child of project: {project_path}"
    if not (source_path / "SKILL.md").is_file():
        return f"Skill folder is missing SKILL.md: {source_path}"
    return ""


def _project_root_for_project(project_path):
    parts = project_path.parts
    for marker in (".agents", ".codex", ".gemini"):
        if marker in parts:
            marker_index = parts.index(marker)
            if marker_index > 0:
                return Path(*parts[:marker_index])
    return project_path.parent


def _skill_base_relative(project_path):
    root = _project_root_for_project(project_path)
    try:
        return project_path.relative_to(root).as_posix()
    except ValueError:
        return project_path.name


def _classification_text(skill_data):
    parts = [skill_data.get("description", "")]
    metadata = skill_data.get("metadata") or {}
    for key in ("category", "source", "risk", "tags", "use_cases"):
        value = metadata.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts)
