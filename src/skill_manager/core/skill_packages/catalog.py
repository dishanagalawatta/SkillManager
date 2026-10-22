"""Curated catalog of ready-to-install skill packages.

The catalog is a *starter* list of well-known agent-skill collections. It
exists so a user can install a popular package with one click instead of
hand-writing the repository URL, the install command and the target path.

Users can extend it: drop a ``package_catalog.json`` into the app data
directory and its entries are merged with the built-in ones (user entries
win on an id collision).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from skill_manager.core.config import resolve_data_file
from skill_manager.core.schemas import CatalogPackageTemplate

logger = logging.getLogger(__name__)

CATALOG_FILENAME = "package_catalog.json"

#: Built-in curated entries. ``install_command`` is what
#: :func:`infer_package_metadata` parses, so it must be a command the
#: installer can actually run.
BUILTIN_CATALOG: list[dict[str, Any]] = [
    {
        "id": "vercel-skills",
        "display_name": "Vercel Skills",
        "description": "The official skills collection from Vercel — web design, "
        "UI review and deployment helpers for coding agents.",
        "author": "Vercel",
        "category": "Engineering",
        "tags": ["frontend", "design", "deployment", "react"],
        "source_type": "git",
        "install_command": "https://github.com/vercel-labs/skills.git",
        "repository_url": "https://github.com/vercel-labs/skills.git",
        "featured": True,
    },
    {
        "id": "anthropic-skills",
        "display_name": "Anthropic Skills",
        "description": "Reference skills published by Anthropic — documents, "
        "slides, spreadsheets and PDFs.",
        "author": "Anthropic",
        "category": "Productivity",
        "tags": ["documents", "slides", "pdf", "spreadsheets"],
        "source_type": "git",
        "install_command": "https://github.com/anthropics/skills.git",
        "repository_url": "https://github.com/anthropics/skills.git",
        "featured": True,
    },
    {
        "id": "agentic-awesome-skills",
        "display_name": "Agentic Awesome Skills",
        "description": "A large community collection of agent skills covering "
        "development, testing and automation.",
        "author": "sickn33",
        "category": "Engineering",
        "tags": ["community", "automation", "testing"],
        "source_type": "git",
        "install_command": "https://github.com/sickn33/agentic-awesome-skills.git",
        "repository_url": "https://github.com/sickn33/agentic-awesome-skills.git",
        "featured": True,
    },
    {
        "id": "superpowers",
        "display_name": "Superpowers",
        "description": "A complete agent workflow: brainstorming, planning, "
        "implementation and verification skills.",
        "author": "obra",
        "category": "Workflow",
        "tags": ["workflow", "planning", "review"],
        "source_type": "git",
        "install_command": "https://github.com/obra/superpowers.git",
        "repository_url": "https://github.com/obra/superpowers.git",
        "featured": False,
    },
    {
        "id": "marketingskills",
        "display_name": "Marketing Skills",
        "description": "Marketing, copywriting and growth skills for content and campaign work.",
        "author": "coreyhaines31",
        "category": "Marketing",
        "tags": ["marketing", "copywriting", "seo"],
        "source_type": "git",
        "install_command": "https://github.com/coreyhaines31/marketingskills.git",
        "repository_url": "https://github.com/coreyhaines31/marketingskills.git",
        "featured": False,
    },
    {
        "id": "stitch-skills",
        "display_name": "Stitch Skills",
        "description": "Design-to-code skills for turning mockups and "
        "screenshots into production UI.",
        "author": "Google Labs",
        "category": "Design",
        "tags": ["design", "ui", "figma"],
        "source_type": "git",
        "install_command": "https://github.com/google-labs-code/stitch-skills.git",
        "repository_url": "https://github.com/google-labs-code/stitch-skills.git",
        "featured": False,
    },
    {
        "id": "devmarketing-skills",
        "display_name": "DevMarketing Skills",
        "description": "Developer-marketing skills for launch notes, changelogs "
        "and technical content.",
        "author": "jonathimer",
        "category": "Marketing",
        "tags": ["marketing", "launch", "content"],
        "source_type": "git",
        "install_command": "https://github.com/jonathimer/devmarketing-skills.git",
        "repository_url": "https://github.com/jonathimer/devmarketing-skills.git",
        "featured": False,
    },
    {
        "id": "skills-npx",
        "display_name": "Skills Installer (npx)",
        "description": "The community skills installer — install a curated "
        "skill with a single npx command.",
        "author": "skills",
        "category": "Utility",
        "tags": ["installer", "npx", "community"],
        "source_type": "npx",
        "install_command": "npx skills add vercel-labs/skills",
        "repository_url": "",
        "default_args": "--all",
        "featured": False,
    },
]


def _user_catalog_file() -> Path:
    return resolve_data_file(CATALOG_FILENAME)


def _load_user_entries() -> list[dict[str, Any]]:
    path = _user_catalog_file()
    try:
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read the user package catalog %s: %s", path, exc)
        return []

    if isinstance(raw, dict):
        raw = raw.get("packages", [])
    if not isinstance(raw, list):
        return []

    entries: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            entries.append(item)
    return entries


def get_catalog() -> list[CatalogPackageTemplate]:
    """Return the merged catalog (built-in entries plus the user's own)."""
    merged: dict[str, dict[str, Any]] = {}
    for entry in BUILTIN_CATALOG:
        merged[entry["id"]] = dict(entry)
    for entry in _load_user_entries():
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id:
            continue
        # A user entry with the same id replaces the built-in one.
        merged[entry_id] = {**merged.get(entry_id, {}), **entry}

    templates: list[CatalogPackageTemplate] = []
    for entry in merged.values():
        try:
            templates.append(CatalogPackageTemplate.model_validate(entry))
        except Exception as exc:
            logger.warning("Skipping invalid catalog entry %r: %s", entry.get("id"), exc)
    return templates


def find_catalog_entry(catalog_id: str) -> CatalogPackageTemplate | None:
    """Return the catalog entry with *catalog_id*, or None."""
    wanted = str(catalog_id or "").strip()
    if not wanted:
        return None
    for template in get_catalog():
        if template.id == wanted:
            return template
    return None


def _repo_key(url: str) -> str:
    """Normalise a repository URL to a comparable ``owner/repo`` key."""
    text = str(url or "").strip().lower()
    if not text:
        return ""
    text = text.removesuffix(".git")
    for prefix in ("https://", "http://", "git@", "ssh://git@", "git://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    if text.startswith("www."):
        text = text[4:]
    parts = [part for part in text.split("/") if part]
    if not parts:
        return ""
    # Drop the host segment ("github.com/owner/repo" -> "owner/repo").
    if len(parts) > 2 and "." in parts[0]:
        parts = parts[1:]
    owner = parts[0]
    repo = parts[1] if len(parts) > 1 else ""
    if ":" in repo:
        repo = repo.split(":", 1)[0]
    if not owner or not repo:
        return ""
    return f"{owner}/{repo}"


def _canonical_repo(url: str) -> str:
    """Apply the known repo aliases so a shorthand still matches."""
    from skill_manager.core.skill_packages.config import KNOWN_SKILL_REPO_ALIASES

    key = _repo_key(url)
    for alias, canonical in KNOWN_SKILL_REPO_ALIASES.items():
        if key == alias.lower():
            return canonical.lower()
        if key.endswith("/" + alias.lower()):
            return canonical.lower()
    return key


def matches_installed_package(
    template: CatalogPackageTemplate, installed: list[dict[str, Any]]
) -> str | None:
    """Return the id of the installed package that matches *template*.

    A package matches when it points at the same repository (after the
    known-alias canonicalisation) or at the same npm package name.
    """
    wanted_repo = _canonical_repo(template.repository_url or template.install_command)
    wanted_name = ""

    for package in installed or []:
        if not isinstance(package, dict):
            continue
        package_repo = _canonical_repo(
            package.get("repository_url") or package.get("update_command") or ""
        )
        if wanted_repo and package_repo and wanted_repo == package_repo:
            return str(package.get("package_id") or package.get("name") or "")

        package_name = str(package.get("package_name") or "").strip().lower()
        if not wanted_name and template.source_type == "npx":
            wanted_name = package_name
        if wanted_name and package_name and wanted_name == package_name:
            return str(package.get("package_id") or package.get("name") or "")
    return None


def catalog_with_status(installed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the catalog as dicts, enriched with the install status.

    Each entry gains ``is_installed`` (bool) and ``installed_package_id``
    (the id of the matching installed package, empty when not installed).
    """
    entries: list[dict[str, Any]] = []
    for template in get_catalog():
        data = template.model_dump()
        match = matches_installed_package(template, installed)
        data["is_installed"] = match is not None
        data["installed_package_id"] = match or ""
        entries.append(data)
    return entries


def template_to_package_data(
    template: CatalogPackageTemplate, target_path: str = ""
) -> dict[str, Any]:
    """Build the package-config dict for *template*.

    The install command is parsed with
    :func:`infer_package_metadata`, so the result is a normal package
    config that the existing add/update flow understands.
    """
    from skill_manager.core.skill_packages.config import infer_package_metadata

    inferred = infer_package_metadata(template.install_command)
    data: dict[str, Any] = {
        "name": template.display_name,
        "source_type": template.source_type or inferred.get("source_type", "git"),
        "repository_url": template.repository_url or inferred.get("repository_url", ""),
        "package_name": inferred.get("package_name", ""),
        "package_args": inferred.get("package_args", ""),
        "update_command": inferred.get("update_command", ""),
    }
    if template.default_args:
        data["package_args"] = f"{data.get('package_args', '')} {template.default_args}".strip()
    if target_path:
        data["package_path"] = target_path
    return data


__all__ = [
    "BUILTIN_CATALOG",
    "CATALOG_FILENAME",
    "catalog_with_status",
    "find_catalog_entry",
    "get_catalog",
    "matches_installed_package",
    "template_to_package_data",
]
