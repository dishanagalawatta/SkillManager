"""Skill management and read-only accessors for the MCP bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._controller import _controller_or_none
from ._telemetry import _log_call, logger


# ---------------------------------------------------------------------------
# Read-only state accessors & Skill Management
# ---------------------------------------------------------------------------
def sync_skills(force_full_scan: bool = False) -> dict[str, Any]:
    """Re-scan configured skill sources and project directories, updating the library model."""
    _log_call("sync_skills")
    controller = _controller_or_none()
    if controller is None:
        return {"synced": False, "count": 0, "message": "AppController unavailable"}

    sources: list[str] = list(getattr(controller, "_sources", []) or [])
    projects: list[str] = list(getattr(controller, "_projects", []) or [])

    cwd = Path.cwd()
    candidate_sources = [
        cwd / ".agents" / "skills",
        cwd / "skills",
        Path.home() / ".agents" / "skills",
        Path.home() / ".claude" / "skills",
    ]
    for cs in candidate_sources:
        try:
            if cs.exists():
                s_str = str(cs.resolve())
                if s_str not in sources:
                    sources.append(s_str)
        except Exception:  # noqa: BLE001
            pass

    s_cwd = str(cwd.resolve())
    if s_cwd not in projects:
        projects.append(s_cwd)

    try:
        from skill_manager.core.discovery import DiscoveryService

        service = DiscoveryService(
            sources=sources,
            projects=projects,
            archive_paths=getattr(controller, "_archive_paths", set()),
            starred_paths=getattr(controller, "_starred_paths", set()),
            project_aliases=getattr(controller, "_project_aliases", {}),
        )
        res = service.discover_all(force_full_scan=force_full_scan)
        raw_skills = res.get("skills", [])
        if hasattr(controller, "_library_model"):
            controller._library_model.addOrUpdateSkills(raw_skills)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sync_skills error: %s", exc)

    all_skills = getattr(controller._library_model, "_all_skills", []) or []
    return {
        "synced": True,
        "count": len(all_skills),
        "message": f"Synchronized {len(all_skills)} skills into library model.",
    }


def list_skills(include_commands: bool = True, project_label: str = "") -> list[dict[str, Any]]:
    """Enumerate skills from ``AppController._library_model``.

    The model stores skills in ``_all_skills`` (a list of ``Skill`` dataclasses).
    We read that list read-only and project a safe subset of fields. There is no
    ``id``/``status``/``client_format`` field on ``Skill`` — we expose the real
    attributes (name, local_path, category, is_package, client, etc.).
    """
    _log_call("list_skills")
    controller = _controller_or_none()
    if controller is None:
        return []

    model = controller._library_model  # noqa: SLF001 - intentional bridge access
    skills: list[Any] = getattr(model, "_all_skills", []) or []
    if not skills:
        sync_skills()
        skills = getattr(model, "_all_skills", []) or []

    out: list[dict[str, Any]] = []
    for skill in skills:
        if not include_commands and getattr(skill, "is_command", False):
            continue
        if project_label and getattr(skill, "project_label", "") != project_label:
            continue
        out.append(
            {
                "name": getattr(skill, "name", ""),
                "local_path": getattr(skill, "local_path", ""),
                "category": getattr(skill, "category", ""),
                "project_label": getattr(skill, "project_label", ""),
                "is_package": getattr(skill, "is_package", False),
                "is_command": getattr(skill, "is_command", False),
                "is_starred": getattr(skill, "is_starred", False),
                "is_archived": getattr(skill, "is_archived", False),
                "client": getattr(skill, "client", ""),
                "risk": getattr(skill, "risk", "Unknown"),
                "source": getattr(skill, "source", "Unknown"),
            }
        )
    return out


def get_skill(skill_id: str) -> dict[str, Any]:
    """Retrieve full content and metadata for a skill by name, folder name, or path."""
    _log_call("get_skill")
    controller = _controller_or_none()
    if controller is None:
        return {"found": False, "skill": None}

    model = controller._library_model  # noqa: SLF001
    skills: list[Any] = getattr(model, "_all_skills", []) or []
    if not skills:
        sync_skills()
        skills = getattr(model, "_all_skills", []) or []

    found_skill: Any | None = None
    for skill in skills:
        name = getattr(skill, "name", "")
        path = getattr(skill, "local_path", "")
        if skill_id in (name, path) or skill_id == path or Path(path).name == skill_id:
            found_skill = skill
            break

    if found_skill is None:
        cand = Path(skill_id)
        if cand.exists():
            for skill in skills:
                if Path(getattr(skill, "local_path", "")).resolve() == cand.resolve():
                    found_skill = skill
                    break

    if found_skill is None:
        return {"found": False, "skill": None}

    local_path = getattr(found_skill, "local_path", "")
    folder = Path(local_path)

    content = ""
    files: list[str] = []
    if folder.exists():
        if folder.is_file():
            content = folder.read_text(encoding="utf-8", errors="replace")
            files = [folder.name]
        elif folder.is_dir():
            files = [str(f.relative_to(folder)) for f in folder.rglob("*") if f.is_file()]
            for cand_file in ("SKILL.md", "skill.md", "README.md"):
                p = folder / cand_file
                if p.is_file():
                    content = p.read_text(encoding="utf-8", errors="replace")
                    break

    skill_detail = {
        "name": getattr(found_skill, "name", ""),
        "local_path": local_path,
        "category": getattr(found_skill, "category", ""),
        "description": getattr(found_skill, "description", ""),
        "content": content,
        "project_label": getattr(found_skill, "project_label", ""),
        "is_package": getattr(found_skill, "is_package", False),
        "is_command": getattr(found_skill, "is_command", False),
        "is_starred": getattr(found_skill, "is_starred", False),
        "is_archived": getattr(found_skill, "is_archived", False),
        "client": getattr(found_skill, "client", ""),
        "risk": getattr(found_skill, "risk", "Unknown"),
        "source": getattr(found_skill, "source", "Unknown"),
        "files": files,
    }
    return {"found": True, "skill": skill_detail}


def search_skills(
    query: str,
    category: str = "",
    project_label: str = "",
    include_commands: bool = True,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search skills by query across name, description, category, and local_path."""
    _log_call("search_skills")
    controller = _controller_or_none()
    if controller is None:
        return []

    model = controller._library_model  # noqa: SLF001
    skills: list[Any] = getattr(model, "_all_skills", []) or []
    if not skills:
        sync_skills()
        skills = getattr(model, "_all_skills", []) or []

    q = query.lower().strip()
    out: list[dict[str, Any]] = []
    for skill in skills:
        if not include_commands and getattr(skill, "is_command", False):
            continue
        if category and getattr(skill, "category", "").lower() != category.lower():
            continue
        if project_label and getattr(skill, "project_label", "") != project_label:
            continue

        name = getattr(skill, "name", "").lower()
        desc = getattr(skill, "description", "").lower()
        cat = getattr(skill, "category", "").lower()
        tags = [str(t).lower() for t in getattr(skill, "tags", []) or []]
        path = getattr(skill, "local_path", "").lower()

        if (
            not q
            or q in name
            or q in desc
            or q in cat
            or q in path
            or any(q in tag for tag in tags)
        ):
            out.append(
                {
                    "name": getattr(skill, "name", ""),
                    "local_path": getattr(skill, "local_path", ""),
                    "category": getattr(skill, "category", ""),
                    "project_label": getattr(skill, "project_label", ""),
                    "is_package": getattr(skill, "is_package", False),
                    "is_command": getattr(skill, "is_command", False),
                    "is_starred": getattr(skill, "is_starred", False),
                    "is_archived": getattr(skill, "is_archived", False),
                    "client": getattr(skill, "client", ""),
                    "risk": getattr(skill, "risk", "Unknown"),
                    "source": getattr(skill, "source", "Unknown"),
                }
            )
            if len(out) >= limit:
                break
    return out


def list_sources() -> list[str]:
    """Return configured skill source directories."""
    _log_call("list_sources")
    controller = _controller_or_none()
    if controller is None:
        return []
    sources: list[str] = getattr(controller, "_sources", []) or []
    return list(sources)


def list_projects() -> list[str]:
    """Return configured project directories."""
    _log_call("list_projects")
    controller = _controller_or_none()
    if controller is None:
        return []
    projects: list[str] = getattr(controller, "_projects", []) or []
    return list(projects)


# ---------------------------------------------------------------------------
# Destructive / Mutating operations
# ---------------------------------------------------------------------------
def create_skill(
    name: str,
    content: str,
    source_path: str = "",
    description: str = "",
    category: str = "",
) -> dict[str, Any]:
    """Create a new skill folder with SKILL.md in a source or project path."""
    _log_call("create_skill")
    controller = _controller_or_none()
    if controller is None:
        raise RuntimeError("AppController unavailable; cannot create skill.")

    if not name or not name.strip():
        raise ValueError("Skill name is required and cannot be empty.")

    clean_name = name.strip()
    parent_dir: Path | None = None
    if source_path:
        parent_dir = Path(source_path)
    else:
        sources = list_sources()
        if sources:
            parent_dir = Path(sources[0])

    if parent_dir is None or not parent_dir.exists():
        parent_dir = Path.cwd() / ".agents" / "skills"
        parent_dir.mkdir(parents=True, exist_ok=True)

    skill_dir = parent_dir / clean_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    final_content = content
    if (description or category) and not final_content.startswith("---"):
        meta = ["---"]
        if description:
            meta.append(f"description: {description}")
        if category:
            meta.append(f"category: {category}")
        meta.append("---\n\n")
        final_content = "\n".join(meta) + final_content

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(final_content, encoding="utf-8")

    sync_skills()

    return {
        "created": True,
        "name": clean_name,
        "local_path": str(skill_dir),
        "message": f"Created skill '{clean_name}' at {skill_dir}",
    }


def update_skill(
    skill_id: str,
    content: str = "",
    description: str = "",
    category: str = "",
) -> dict[str, Any]:
    """Update an existing skill's SKILL.md content or metadata."""
    _log_call("update_skill")
    controller = _controller_or_none()
    if controller is None:
        raise RuntimeError("AppController unavailable; cannot update skill.")

    model = controller._library_model  # noqa: SLF001
    skills: list[Any] = getattr(model, "_all_skills", []) or []
    resolved: str | None = None
    for skill in skills:
        name = getattr(skill, "name", "")
        path = getattr(skill, "local_path", "")
        if skill_id in (name, path) or skill_id == path or Path(path).name == skill_id:
            resolved = path
            break

    if not resolved:
        resolved = skill_id

    skill_path = Path(resolved)
    if not skill_path.exists():
        raise ValueError(f"Skill target {skill_id!r} does not exist.")

    skill_md = skill_path / "SKILL.md" if skill_path.is_dir() else skill_path

    final_content = content
    if (description or category) and final_content and not final_content.startswith("---"):
        meta = ["---"]
        if description:
            meta.append(f"description: {description}")
        if category:
            meta.append(f"category: {category}")
        meta.append("---\n\n")
        final_content = "\n".join(meta) + final_content

    if final_content:
        skill_md.write_text(final_content, encoding="utf-8")

    sync_skills()

    return {
        "updated": True,
        "skill_id": skill_id,
        "local_path": str(skill_path),
        "message": f"Updated skill '{skill_id}' at {skill_path}",
    }


def delete_skill(skill_id: str) -> dict[str, Any]:
    """Delete a skill by name or local_path."""
    _log_call("delete_skill")
    controller = _controller_or_none()
    if controller is None:
        raise RuntimeError("AppController unavailable; cannot delete skill.")

    model = controller._library_model  # noqa: SLF001
    skills: list[Any] = getattr(model, "_all_skills", []) or []

    resolved: str | None = None
    for skill in skills:
        name = getattr(skill, "name", "")
        path = getattr(skill, "local_path", "")
        if skill_id in (name, path) or skill_id == path:
            resolved = path
            break

    if not resolved:
        cand = Path(skill_id)
        if cand.exists():
            resolved = str(cand.resolve())

    if not resolved:
        raise ValueError(
            f"Skill id {skill_id!r} did not resolve to a known local_path; "
            "refusing to guess a deletion target."
        )

    ops = getattr(controller, "ops", None)
    if ops is not None and hasattr(ops, "deleteSkill"):
        ops.deleteSkill(resolved)
    else:
        target_path = Path(resolved)
        if target_path.exists():
            if target_path.is_dir():
                import shutil

                shutil.rmtree(target_path)
            else:
                target_path.unlink()

    sync_skills()

    return {
        "deleted": True,
        "skill_id": skill_id,
        "resolved_path": resolved,
        "message": f"Deleted skill at {resolved}",
    }


def deploy(skill_id: str, target: str) -> dict[str, Any]:
    """Deploy a skill or package to a target project directory."""
    _log_call("deploy")
    controller = _controller_or_none()
    if controller is None:
        raise RuntimeError("AppController unavailable; cannot deploy skill.")

    model = controller._library_model  # noqa: SLF001
    skills: list[Any] = getattr(model, "_all_skills", []) or []
    target_skill: Any | None = None
    for skill in skills:
        name = getattr(skill, "name", "")
        path = getattr(skill, "local_path", "")
        if skill_id in (name, path) or skill_id == path or Path(path).name == skill_id:
            target_skill = skill
            break

    if target_skill is None:
        raise ValueError(f"Skill id {skill_id!r} did not resolve to a known skill.")

    target_path: Path | None = None
    projects = list_projects()
    for proj in projects:
        if target == proj or Path(target).name == target or target in proj:
            target_path = Path(proj)
            break

    if target_path is None:
        target_path = Path(target)

    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)

    from skill_manager.core.copier import copy_skill_folders_to_projects

    skill_dict = {
        "name": getattr(target_skill, "name", ""),
        "local_path": getattr(target_skill, "local_path", ""),
        "is_package": getattr(target_skill, "is_package", False),
    }
    res = copy_skill_folders_to_projects([skill_dict], [str(target_path)])

    sync_skills()

    return {
        "deployed": res.get("copied", 0) > 0
        or res.get("merged", 0) > 0
        or res.get("failed", 0) == 0,
        "skill_id": skill_id,
        "target": str(target_path),
        "details": res.get("details", []),
        "message": f"Deployed {skill_id} to {target_path}",
    }
