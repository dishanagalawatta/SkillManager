import os
import shutil
from pathlib import Path

CLIENT_FORMATS = {"Codex", "Gemini CLI", "Antigravity", "Plain Path"}


def _resolve_resilient_path(path_str):
    """Try to resolve a path, being resilient to .agent vs .agents pluralization mismatches."""
    if not path_str:
        return Path()

    path = Path(os.path.expanduser(str(path_str).strip()))
    try:
        if path.exists():
            return path.resolve()
    except OSError:
        pass

    # Try swapping .agent <-> .agents
    s = str(path)
    # Normalize slashes for detection but keep original for replacement to avoid breaking windows paths more than needed
    s_norm = s.replace("\\", "/")

    alt_s = None
    if "/.agent/" in s_norm:
        alt_s = s.replace("/.agent/", "/.agents/").replace("\\.agent\\", "\\.agents\\")
    elif "/.agents/" in s_norm:
        alt_s = s.replace("/.agents/", "/.agent/").replace("\\.agents\\", "\\.agent\\")
    elif s_norm.endswith("/.agent"):
        alt_s = s + "s"
    elif s_norm.endswith("/.agents"):
        alt_s = s[:-1]

    if alt_s:
        alt_path = Path(alt_s)
        try:
            if alt_path.exists():
                return alt_path.resolve()
        except OSError:
            pass

    return path


def discover_source_skills(sources, parse_skill_md, categorize_skill, build_search_text):
    """Discover skills from master source folders (config['sources']).

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

    for source in sources:
        resolved_source = _resolve_resilient_path(source)
        if not resolved_source or not resolved_source.is_dir():
            continue

        source_key = os.path.normcase(str(resolved_source))
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        for child in sorted(resolved_source.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir():
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
            skill_data["source_path"] = str(resolved_source)
            skill_data["target_path"] = str(resolved_source)  # source IS the target for library items
            skill_data["project_label"] = "Master Library"
            skill_data["project_root"] = str(resolved_source)
            skill_data["skill_base_relative"] = _skill_base_relative(resolved_source)
            skill_data["is_source"] = True
            skill_data.setdefault("metadata", {})
            skill_data["category"] = categorize_skill(
                skill_data.get("name", ""),
                _classification_text(skill_data),
            )
            skill_data["search_text"] = build_search_text(skill_data)
            skills.append(skill_data)

    return skills


def discover_project_skills(targets, parse_skill_md, categorize_skill, build_search_text, target_aliases=None):
    if target_aliases is None:
        target_aliases = {}
    projects = []
    seen_targets = set()

    for target in targets:
        resolved_target = _resolve_resilient_path(target)
        if not resolved_target or not resolved_target.is_dir():
            continue

        target_key = os.path.normcase(str(resolved_target))
        if target_key in seen_targets:
            continue
        seen_targets.add(target_key)

        skills = []
        for child in sorted(resolved_target.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir():
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
            skill_data["project_key"] = target_key
            skill_data["target_path"] = str(resolved_target)
            skill_data["project_root"] = str(_project_root_for_target(resolved_target))
            skill_data["skill_base_relative"] = _skill_base_relative(resolved_target)
            skill_data["project_label"] = project_label(resolved_target, target_aliases, str(target))
            skill_data.setdefault("metadata", {})
            skill_data["category"] = categorize_skill(
                skill_data.get("name", ""),
                _classification_text(skill_data),
            )
            skill_data["search_text"] = build_search_text(skill_data)
            skills.append(skill_data)

        if skills:
            project_root = _project_root_for_target(resolved_target)
            projects.append({
                "target_path": str(resolved_target),
                "project_root": str(project_root),
                "project_label": project_label(resolved_target, target_aliases, str(target)),
                "skill_base_relative": _skill_base_relative(resolved_target),
                "project_key": target_key,
                "skills": skills,
            })

    return projects


def _normalize_path(path):
    if not path:
        return ""
    return os.path.normcase(os.path.normpath(path)).replace("\\", "/")


def project_label(target_path, target_aliases=None, original_target=None):
    if target_aliases is None:
        target_aliases = {}

    norm_target = _normalize_path(target_path).lower()
    norm_original = _normalize_path(original_target).lower() if original_target else ""

    # We lower keys for fuzzy matching on Posix/Windows paths
    lower_aliases = {k.lower(): v for k, v in target_aliases.items()}

    # Try using original target (exact or normalized)
    if original_target and str(original_target).lower() in lower_aliases:
        return lower_aliases[str(original_target).lower()]
    if norm_original and norm_original in lower_aliases:
        return lower_aliases[norm_original]

    # Try resolved path (exact or normalized)
    target_str = str(target_path).lower()
    if target_str in lower_aliases:
        return lower_aliases[target_str]
    if norm_target in lower_aliases:
        return lower_aliases[norm_target]

    # Full scan for matching normalized keys
    for k, v in target_aliases.items():
        if _normalize_path(k).lower() == norm_target or (norm_original and _normalize_path(k).lower() == norm_original):
            return v

    # Use standard format if no alias: "RootName (Base)"
    target_path_obj = Path(target_path)
    root = _project_root_for_target(target_path_obj)
    base = _skill_base_relative(target_path_obj)

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
            # Fallback: try to find manuals/ in the path
            try:
                manual_idx = local_path.parts.index("manuals")
                relative_path = "/".join(local_path.parts[manual_idx:])
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


def normalize_manual_references(text):
    references = []
    seen = set()
    for line in str(text or "").splitlines():
        reference = normalize_manual_reference(line)
        if not reference:
            continue
        key = reference.casefold()
        if key in seen:
            continue
        seen.add(key)
        references.append(reference)
    return references


def normalize_manual_reference(value):
    reference = str(value or "").strip()
    if not reference:
        return ""
    if _looks_like_explicit_reference(reference):
        return reference
    return f"@{reference.lstrip('@')}"


def merge_manual_references(existing, additions):
    merged = []
    seen = set()
    for reference in list(existing or []) + list(additions or []):
        normalized = normalize_manual_reference(reference)
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
    folder = str(skill.get("folder_name") or Path(skill.get("local_path", "")).name).replace("\\", "/").strip("/")
    return f"{base}/{folder}/SKILL.md" if base else f"{folder}/SKILL.md"


def delete_project_skill_folders(skills):
    result = {"deleted": 0, "skipped": 0, "failed": 0, "details": []}
    for skill in skills:
        label = skill.get("name") or skill.get("folder_name") or "Unknown"
        source_path = Path(os.path.expanduser(str(skill.get("local_path") or ""))).resolve()
        target_path = Path(os.path.expanduser(str(skill.get("target_path") or ""))).resolve()
        error = _delete_validation_error(source_path, target_path)
        if error:
            result["skipped"] += 1
            result["details"].append({"skill": label, "path": str(source_path), "status": "skipped", "message": error})
            continue

        try:
            shutil.rmtree(source_path)
        except Exception as exc:
            result["failed"] += 1
            result["details"].append({"skill": label, "path": str(source_path), "status": "failed", "message": str(exc)})
            continue

        result["deleted"] += 1
        result["details"].append({"skill": label, "path": str(source_path), "status": "deleted", "message": str(source_path)})

    return result


def _delete_validation_error(source_path, target_path):
    if not target_path.is_dir():
        return f"Target folder does not exist: {target_path}"
    if not source_path.is_dir():
        return f"Skill folder does not exist: {source_path}"
    if source_path.parent != target_path:
        return f"Skill folder is not a direct child of target: {target_path}"
    if not (source_path / "SKILL.md").is_file():
        return f"Skill folder is missing SKILL.md: {source_path}"
    return ""


def _project_root_for_target(target_path):
    parts = target_path.parts
    for marker in (".agent", ".agents", ".codex", ".gemini"):
        if marker in parts:
            marker_index = parts.index(marker)
            if marker_index > 0:
                return Path(*parts[:marker_index])
    return target_path.parent


def _skill_base_relative(target_path):
    root = _project_root_for_target(target_path)
    try:
        return target_path.relative_to(root).as_posix()
    except ValueError:
        return target_path.name


def _classification_text(skill_data):
    parts = [skill_data.get("description", "")]
    metadata = skill_data.get("metadata") or {}
    for key in ("category", "source", "risk", "tags", "use_cases"):
        value = metadata.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts)
