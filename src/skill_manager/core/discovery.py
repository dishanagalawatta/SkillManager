"""
Discovery service for finding and processing skills from sources and projects.
"""

import hashlib
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from diskcache import Cache
from joblib import Parallel, delayed

from skill_manager.core.config import DATA_DIR
from skill_manager.core.diagnostics import (
    CATEGORY_SOURCE_MISSING,
    get_diagnostic_logger,
)
from skill_manager.core.parsing import (
    build_skill_search_text,
    categorize_skill,
    parse_command_md,
    parse_skill_md,
)
from skill_manager.core.persistence import load_cache, save_cache
from skill_manager.core.schemas import CacheState, SkillRecord

logger = logging.getLogger(__name__)


def get_discovery_cache() -> Cache:
    """Returns a diskcache instance for discovery results."""
    cache_dir = DATA_DIR / "cache" / "discovery"
    return Cache(str(cache_dir))


def compute_dir_fingerprint(dir_path: Path) -> str:
    """Compute a lightweight fingerprint for a directory.

    Uses directory mtime + count of immediate child dirs containing SKILL.md
    + max mtime of those subdirs to detect internal file changes.
    """
    try:
        stat = dir_path.stat()
        skill_dirs = [
            child
            for child in dir_path.iterdir()
            if child.is_dir() and (child / "SKILL.md").is_file()
        ]
        skill_count = len(skill_dirs)

        # Max mtime of subdirs to help detect changes within them
        max_sub_mtime = 0.0
        if skill_dirs:
            max_sub_mtime = max(d.stat().st_mtime for d in skill_dirs)

        raw = f"{stat.st_mtime}:{stat.st_size}:{skill_count}:{max_sub_mtime}"
        return hashlib.md5(raw.encode()).hexdigest()
    except OSError as e:
        logger.debug("[DISCOVERY] Fingerprint error for %s: %s", dir_path, e)
        return ""


class DiscoveryService:
    # Cache key prefix for directory fingerprints
    _DIR_FP_PREFIX = "dir_fp:"

    def __init__(
        self,
        sources: list[str],
        projects: list[str],
        archive_paths: list[str] | None = None,
        starred_paths: list[str] | None = None,
        project_aliases: dict[str, str] | None = None,
    ):
        self.sources = sources
        self.projects = projects
        self.archive_paths = archive_paths or []
        self.starred_paths = starred_paths or []
        self.project_aliases = project_aliases or {}

    def discover_all(
        self, use_cache: bool = True, cache_callback: Callable[[dict[str, Any]], None] | None = None
    ) -> dict[str, Any]:
        """Performs full discovery of skills from all sources and projects.

        Uses incremental scanning: directories whose fingerprint (mtime + skill
        count) hasn't changed since the last scan are skipped, reusing the
        previously-discovered skills from the disk cache.
        """
        diag = get_diagnostic_logger()

        # Validate source paths early — missing sources cause zero-result
        # discovery which triggers the safety net downstream
        missing_sources: list[str] = []
        for src in self.sources:
            if not os.path.isdir(src):
                missing_sources.append(src)
                diag.log_event(
                    "WARNING",
                    CATEGORY_SOURCE_MISSING,
                    f"Source directory not found: {src}",
                    data={"source_path": src},
                )
        for proj in self.projects:
            if not os.path.isdir(proj):
                missing_sources.append(proj)
                diag.log_event(
                    "WARNING",
                    CATEGORY_SOURCE_MISSING,
                    f"Project directory not found: {proj}",
                    data={"source_path": proj},
                )
        if missing_sources:
            logger.warning(
                "[DISCOVERY] %d source/project directories not found: %s",
                len(missing_sources),
                missing_sources,
            )

        # 1. Try JSON index cache first for instant UI population
        if use_cache:
            try:
                cached_data = load_cache()
                if cached_data and cache_callback:
                    cache_callback(cached_data)
            except Exception as e:
                logger.warning("[DISCOVERY] Error loading index cache: %s", e)

        # 2. Discovery using diskcache for granular file-level caching
        with get_discovery_cache() as disk_cache:
            parse_fn = self._wrap_parse_skill_md(disk_cache)
            cat_fn = self._wrap_categorize_skill(disk_cache)

            # 2a. Discover from master packages (incremental)
            package_skills_raw = self.discover_packages_incremental(disk_cache, parse_fn, cat_fn)

            all_skills: list[SkillRecord] = []
            for skill in package_skills_raw:
                transformed = self.transform_skill(skill, is_package=True)
                all_skills.append(SkillRecord.model_validate(transformed))

            # 2b. Discover from project skill folders (incremental)
            projects_state = self.discover_projects_incremental(disk_cache, parse_fn, cat_fn)

            for p in projects_state:
                for skill in p.get("skills", []):
                    transformed = self.transform_skill(
                        skill, is_package=False, project_label=p.get("project_label")
                    )
                    all_skills.append(SkillRecord.model_validate(transformed))

                # Also discover commands in .agents/commands/ subdir
                project_root = Path(p["project_root"])
                commands_dir = project_root / ".agents" / "commands"
                if commands_dir.is_dir():
                    for cmd_file in commands_dir.glob("*.md"):
                        cmd_data = self._process_command_file(cmd_file, p, disk_cache)
                        if cmd_data:
                            all_skills.append(SkillRecord.model_validate(cmd_data))

        # 3. Pre-compute metadata
        cats = sorted({s.category for s in all_skills if s.category})
        proj_labels = sorted({p["project_label"] for p in projects_state})

        state = CacheState(
            skills=all_skills,
            projects=projects_state,
            categories=cats,
            project_labels=proj_labels,
            status=f"Found {len(all_skills)} skills in master library ({len(projects_state)} projects)",
        )

        result = state.model_dump()

        # 4. Update index cache
        save_cache(result)

        return result

    def discover_packages_incremental(
        self, disk_cache: Cache, parse_fn: Callable, cat_fn: Callable
    ) -> list[dict[str, Any]]:
        """Discover package skills, skipping directories with unchanged fingerprints."""
        from skill_manager.core.quick_copy import (
            classification_text,
            is_ignored,
            load_ignore_spec,
            resolve_resilient_path,
            skill_base_relative,
        )

        skills: list[dict[str, Any]] = []
        unique_sources: list[Path] = []
        seen_sources: set[str] = set()

        for source in self.sources:
            resolved = resolve_resilient_path(source)
            if not resolved or not resolved.is_dir():
                continue
            key = os.path.normcase(str(resolved))
            if key not in seen_sources:
                seen_sources.add(key)
                unique_sources.append(resolved)

        if not unique_sources:
            return []

        # Check fingerprints
        changed_sources: list[Path] = []
        cached_skills: list[dict[str, Any]] = []

        for src in unique_sources:
            fp_key = f"{self._DIR_FP_PREFIX}{os.path.normcase(str(src))}"
            current_fp = compute_dir_fingerprint(src)
            stored_fp = disk_cache.get(fp_key)  # type: ignore[arg-type]

            if current_fp and current_fp == stored_fp:
                cached = disk_cache.get(f"pkg_skills:{fp_key}")  # type: ignore[arg-type]
                if cached is not None:
                    cached_skills.extend(cached)  # type: ignore[arg-type]
                    continue

            changed_sources.append(src)

        if changed_sources:

            def _scan_one(resolved_source: Path) -> list[dict[str, Any]]:
                source_skills: list[dict[str, Any]] = []
                ignore_spec = load_ignore_spec(resolved_source)
                try:
                    for child in sorted(resolved_source.iterdir(), key=lambda i: i.name.lower()):
                        if not child.is_dir() or is_ignored(child, resolved_source, ignore_spec):
                            continue

                        skill_md_path = child / "SKILL.md"
                        if not skill_md_path.is_file():
                            continue

                        skill_data = parse_fn(str(skill_md_path))
                        skill_data.update(
                            {
                                "name": skill_data.get("name") or child.name,
                                "folder_name": child.name,
                                "local_path": str(child),
                                "skill_md_path": str(skill_md_path),
                                "source_path": str(resolved_source),
                                "project_path": str(resolved_source),
                                "project_label": "Master Library",
                                "project_root": str(resolved_source),
                                "skill_base_relative": skill_base_relative(resolved_source),
                                "is_package": True,
                                "is_source": True,
                            }
                        )

                        if not skill_data.get("main_category"):
                            cat_info = cat_fn(
                                skill_data.get("name", ""),
                                classification_text(skill_data),
                                skill_data.get("metadata", {}),
                            )
                            skill_data["main_category"] = cat_info.get("main_category", "")
                            skill_data["category"] = cat_info.get("sub_category", "")

                        skill_data["search_text"] = build_skill_search_text(skill_data)
                        source_skills.append(skill_data)
                except Exception as e:
                    logger.error("[DISCOVERY] Error scanning source %s: %s", resolved_source, e)
                return source_skills

            # Offload heavy parsing to separate processes to keep the PySide6 UI thread responsive.
            # Using loky (joblib's backend) correctly serializes nested closures like _scan_one.
            parallel_results = Parallel(n_jobs=-1, prefer="processes")(
                delayed(_scan_one)(src) for src in changed_sources
            )

            for src, new_skills in zip(changed_sources, parallel_results, strict=False):
                try:
                    skills.extend(new_skills)
                    fp_key = f"{self._DIR_FP_PREFIX}{os.path.normcase(str(src))}"
                    disk_cache.set(fp_key, compute_dir_fingerprint(src))
                    disk_cache.set(f"pkg_skills:{fp_key}", new_skills)
                except Exception as e:
                    logger.warning("[DISCOVERY] Scan failed for %s: %s", src, e)

        return cached_skills + skills

    def discover_projects_incremental(
        self, disk_cache: Cache, parse_fn: Callable, cat_fn: Callable
    ) -> list[dict[str, Any]]:
        """Discover project skills, skipping directories with unchanged fingerprints."""
        from skill_manager.core.quick_copy import resolve_resilient_path

        unique_projects: list[Path] = []
        seen_projects: set[str] = set()

        for project in self.projects:
            resolved = resolve_resilient_path(project)
            if not resolved or not resolved.is_dir():
                continue
            key = os.path.normcase(str(resolved))
            if key not in seen_projects:
                seen_projects.add(key)
                unique_projects.append(resolved)

        if not unique_projects:
            return []

        projects_state: list[dict[str, Any]] = []

        for resolved in unique_projects:
            fp_key = f"{self._DIR_FP_PREFIX}{os.path.normcase(str(resolved))}"
            current_fp = compute_dir_fingerprint(resolved)
            stored_fp = disk_cache.get(fp_key)  # type: ignore[arg-type]

            if current_fp and current_fp == stored_fp:
                cached = disk_cache.get(f"proj_skills:{fp_key}")  # type: ignore[arg-type]
                if cached is not None:
                    projects_state.append(cached)  # type: ignore[arg-type]
                    continue

            # Full scan for this project
            project_data = self._scan_single_project(str(resolved), resolved, parse_fn, cat_fn)
            if project_data:
                projects_state.append(project_data)
                disk_cache.set(fp_key, compute_dir_fingerprint(resolved))
                disk_cache.set(f"proj_skills:{fp_key}", project_data)

        return projects_state

    def _scan_single_project(
        self, project_path_str: str, resolved: Path, parse_fn: Callable, cat_fn: Callable
    ) -> dict[str, Any] | None:
        """Scan a single project directory for skills."""
        from skill_manager.core.quick_copy import (
            classification_text,
            is_ignored,
            load_ignore_spec,
            project_label,
            project_root_for_project,
            skill_base_relative,
        )

        project_key = os.path.normcase(str(resolved))
        skills: list[dict[str, Any]] = []
        ignore_spec = load_ignore_spec(resolved)

        try:
            for child in sorted(resolved.iterdir(), key=lambda i: i.name.lower()):
                if not child.is_dir() or is_ignored(child, resolved, ignore_spec):
                    continue

                skill_md_path = child / "SKILL.md"
                if not skill_md_path.is_file():
                    continue

                skill_data = parse_fn(str(skill_md_path))
                skill_data.update(
                    {
                        "name": skill_data.get("name") or child.name,
                        "folder_name": child.name,
                        "local_path": str(child),
                        "skill_md_path": str(skill_md_path),
                        "project_key": project_key,
                        "project_path": str(resolved),
                        "project_root": str(project_root_for_project(resolved)),
                        "skill_base_relative": skill_base_relative(resolved),
                        "project_label": project_label(
                            resolved, self.project_aliases, project_path_str
                        ),
                    }
                )

                if not skill_data.get("main_category"):
                    cat_info = cat_fn(
                        skill_data.get("name", ""),
                        classification_text(skill_data),
                        skill_data.get("metadata", {}),
                    )
                    skill_data["main_category"] = cat_info.get("main_category", "")
                    skill_data["category"] = cat_info.get("sub_category", "")

                skill_data["search_text"] = build_skill_search_text(skill_data)
                skills.append(skill_data)

            # Screenshots discovery
            project_root_path = project_root_for_project(resolved)
            screenshot_dir = project_root_path / ".agents" / "screenshots"
            if screenshot_dir.is_dir():
                for img in sorted(
                    screenshot_dir.iterdir(), key=lambda i: i.name.lower(), reverse=True
                ):
                    if img.is_file() and img.suffix.lower() in (".png", ".jpg", ".jpeg"):
                        skills.append(
                            {
                                "name": img.name,
                                "folder_name": ".agents/screenshots",
                                "local_path": str(img),
                                "skill_md_path": str(img),
                                "project_key": project_key,
                                "project_path": str(resolved),
                                "project_root": str(project_root_path),
                                "project_label": project_label(
                                    resolved, self.project_aliases, project_path_str
                                ),
                                "main_category": "Special",
                                "category": "Screenshots",
                                "search_text": f"screenshot capture {img.name}",
                                "is_screenshot": True,
                                "metadata": {"category": "Capture"},
                            }
                        )

        except Exception as e:
            logger.error("[DISCOVERY] Error scanning project %s: %s", resolved, e)

        if skills:
            project_root = project_root_for_project(resolved)
            return {
                "project_path": str(resolved),
                "project_root": str(project_root),
                "project_label": project_label(resolved, self.project_aliases, project_path_str),
                "skill_base_relative": skill_base_relative(resolved),
                "project_key": project_key,
                "skills": skills,
            }
        return None

    def _wrap_parse_skill_md(self, cache: Cache) -> Callable[[str], dict[str, Any]]:
        """Wraps parse_skill_md with disk caching based on file mtime/size hash.

        Also caches categorization results so that ``categorize_skill`` is
        skipped for files whose content hasn't changed since the last scan.
        """

        def cached_parse(path_str: str) -> dict[str, Any]:
            path = Path(path_str)
            if not path.is_file():
                return {}

            try:
                stat = path.stat()
                cache_key = f"skill:{path_str}:{stat.st_mtime}:{stat.st_size}"
                if len(cache_key) > 200:
                    cache_key = hashlib.md5(cache_key.encode()).hexdigest()

                result = cache.get(cache_key)  # type: ignore[arg-type,assignment]
                if result is not None:
                    return result  # type: ignore[return-value]

                result = parse_skill_md(path_str)
                cache.set(cache_key, result)  # type: ignore[arg-type]
                return result
            except Exception as e:
                logger.warning("[DISCOVERY] Cache error for %s: %s", path_str, e)
                return parse_skill_md(path_str)

        return cached_parse

    def _wrap_categorize_skill(self, cache: Cache) -> Callable[[str, str, dict], dict[str, str]]:
        """Wraps categorize_skill with disk caching.

        Keyed by the raw classification text so unchanged skills skip the
        rapidfuzz fuzzy-matching step entirely.
        """

        def cached_categorize(name: str, text: str, metadata: dict) -> dict[str, str]:
            # Build a stable cache key from the inputs
            raw = f"{name}|{text}"
            cache_key = f"cat:{hashlib.md5(raw.encode()).hexdigest()}"

            result = cache.get(cache_key)  # type: ignore[arg-type,assignment]
            if result is not None:
                return result  # type: ignore[return-value]

            result = categorize_skill(name, text, metadata)
            cache.set(cache_key, result)  # type: ignore[arg-type]
            return result

        return cached_categorize

    def transform_skill(
        self, skill: dict[str, Any], is_package: bool, project_label: str | None = None
    ) -> dict[str, Any]:
        """Normalizes raw skill data into the format expected by the UI models."""
        metadata = skill.get("metadata", {})
        local_path = skill.get("local_path", "")

        data = {
            "id": str(local_path),
            "name": skill.get("name", "Unknown"),
            "main_category": skill.get("main_category", "⚙️ System & Workflow"),
            "category": skill.get("category", "Uncategorized"),
            "description": skill.get("description", ""),
            "local_path": local_path,
            "project_label": skill.get("project_label")
            or project_label
            or ("Master Library" if is_package else "Unknown Project"),
            "project_root": skill.get("project_root", ""),
            "project_path": skill.get("project_path", ""),
            "is_starred": metadata.get("starred", False)
            or metadata.get("essential", False)
            or local_path in self.starred_paths,
            "is_bundle": skill.get("is_bundle", False),
            "commands": skill.get("commands", []),
            "is_selected": False,
            "is_archived": local_path in self.archive_paths,
            "search_text": skill.get("search_text", ""),
            "raw_content": skill.get("raw_content", ""),
            "body_content": skill.get("body_content", ""),
            "risk": metadata.get("risk", "Unknown"),
            "source": metadata.get("source", "Unknown"),
            "date": str(metadata.get("date_added") or metadata.get("date", "Unknown")),
            "is_package": is_package,
            "is_source": is_package,  # Compatibility
            "is_screenshot": skill.get("is_screenshot", False),
            "tags": metadata.get("tags") or skill.get("tags") or [],
            "metadata": metadata,
        }

        if not is_package:
            data.update(
                {
                    "skill_base_relative": skill.get("skill_base_relative", ""),
                    "folder_name": skill.get("folder_name", ""),
                    "skill_md_path": skill.get("skill_md_path", ""),
                }
            )

        return data

    def _process_command_file(
        self, cmd_file: Path, project: dict[str, Any], cache: Cache | None = None
    ) -> dict[str, Any] | None:
        """Parses a command markdown file and returns its normalized representation."""
        cmd_path_str = str(cmd_file)

        cmd_data_raw: dict[str, Any] | None = None
        if cache:
            try:
                stat = cmd_file.stat()
                cache_key = f"cmd:{cmd_path_str}:{stat.st_mtime}:{stat.st_size}"
                cmd_data_raw = cache.get(cache_key)  # type: ignore[assignment]
                if cmd_data_raw is None:
                    cmd_data_raw = parse_command_md(cmd_path_str)
                    cache.set(cache_key, cmd_data_raw)  # type: ignore[arg-type]
            except Exception as e:
                logger.warning("[DISCOVERY] Command cache error for %s: %s", cmd_path_str, e)

        if cmd_data_raw is None:
            cmd_data_raw = parse_command_md(cmd_path_str)

        if not cmd_data_raw:
            return None

        data = {
            "id": str(cmd_file),
            "name": cmd_data_raw.get("name") or cmd_file.stem,
            "main_category": cmd_data_raw.get("main_category") or "⚙️ System & Workflow",
            "category": cmd_data_raw.get("category") or "Custom Commands",
            "description": cmd_data_raw.get("description", ""),
            "local_path": str(cmd_file),
            "project_label": project.get("project_label", "Unknown Project"),
            "project_root": project.get("project_root", ""),
            "project_path": project.get("project_path", ""),
            "is_starred": False,
            "is_bundle": False,
            "commands": [],
            "is_selected": False,
            "is_archived": False,
            "raw_content": cmd_data_raw.get("raw_content", ""),
            "body_content": cmd_data_raw.get("body_content", ""),
            "risk": "Low",
            "source": "Custom",
            "date": str(cmd_data_raw.get("metadata", {}).get("date", "Unknown")),
            "is_package": False,
            "is_source": False,  # Compatibility
            "is_command": True,
        }
        data["search_text"] = build_skill_search_text(data)
        return data

    def discover_single(self, path: Path, project_path: Path) -> dict[str, Any] | None:
        """Parse and normalize a single skill or command file.

        Dispatches to the correct parser based on the path shape:

        * ``path`` is a ``.md`` file → command file parser
        * ``path`` is a directory containing ``SKILL.md`` → skill folder parser

        Returns ``None`` when the file/folder does not match either shape or
        parsing fails.
        """
        if path.is_file() and path.suffix.lower() == ".md":
            return self._discover_single_command(path, project_path)

        if path.is_dir():
            return self._discover_single_skill_folder(path, project_path)

        return None

    def discover_project(self, project_path: Path) -> list[dict]:
        """Discover all skills and commands in a project's ``.agents`` directory.

        Walks ``<project_path>/.agents/skills/`` and
        ``<project_path>/.agents/commands/``, skipping ``.git``,
        ``__pycache__``, and hidden directories.  Returns a list of
        non-``None`` skill/command dicts; returns ``[]`` on error.
        """
        diag = get_diagnostic_logger()
        results: list[dict] = []

        agents_dir = project_path / ".agents"
        if not agents_dir.is_dir():
            return results

        # --- Commands ---
        commands_dir = agents_dir / "commands"
        if commands_dir.is_dir():
            try:
                with os.scandir(commands_dir) as entries:
                    for entry in entries:
                        if not entry.is_file():
                            continue
                        if not entry.name.endswith(".md"):
                            continue
                        if entry.name.startswith("."):
                            continue
                        cmd_file = Path(entry.path)
                        result = self._discover_single_command(cmd_file, project_path)
                        if result is not None:
                            results.append(result)
            except OSError as e:
                diag.log_event(
                    "WARNING",
                    CATEGORY_SOURCE_MISSING,
                    f"Error scanning commands in {commands_dir}: {e}",
                    data={"commands_dir": str(commands_dir), "error": str(e)},
                )

        # --- Skills ---
        skills_dir = agents_dir / "skills"
        if skills_dir.is_dir():
            try:
                with os.scandir(skills_dir) as entries:
                    for entry in entries:
                        if not entry.is_dir():
                            continue
                        if entry.name.startswith(".") or entry.name == "__pycache__":
                            continue
                        skill_dir = Path(entry.path)
                        skill_md = skill_dir / "SKILL.md"
                        if skill_md.is_file():
                            result = self._discover_single_skill_folder(skill_dir, project_path)
                            if result is not None:
                                results.append(result)
            except OSError as e:
                diag.log_event(
                    "WARNING",
                    CATEGORY_SOURCE_MISSING,
                    f"Error scanning skills in {skills_dir}: {e}",
                    data={"skills_dir": str(skills_dir), "error": str(e)},
                )

        return results

    def _discover_single_command(self, cmd_file: Path, project_path: Path) -> dict[str, Any] | None:
        """Parse a single command ``.md`` file into a normalized dict."""
        effective_project = self._find_project_root_for_command(cmd_file, project_path)
        resolved = self._resolve_project_dict(effective_project)
        if not resolved:
            return None
        return self._process_command_file(cmd_file, resolved, cache=None)

    @staticmethod
    def _find_project_root_for_command(cmd_file: Path, project_path: Path) -> Path:
        """Walk up from *cmd_file* to locate the project root.

        Command files live under ``<project_root>/.agents/commands/``.
        If *project_path* is the ``commands`` dir (or any child of the project),
        we walk upward until we find a directory that contains ``.agents``.
        """
        # If project_path already looks like a project root (has .agents), use it
        if (project_path / ".agents").is_dir():
            return project_path

        # Walk up from the command file's parent looking for .agents/
        candidate = cmd_file.parent
        for _ in range(5):  # guard against runaway traversal
            if (candidate / ".agents").is_dir():
                return candidate
            parent = candidate.parent
            if parent == candidate:
                break
            candidate = parent

        # Fallback: use project_path as-is
        return project_path

    def _discover_single_skill_folder(
        self, skill_path: Path, project_path: Path
    ) -> dict[str, Any] | None:
        """Parse a single skill folder (containing ``SKILL.md``)."""
        data = discover_single_skill(skill_path, project_path, self.project_aliases)
        if data is None:
            return None
        return self.transform_skill(
            data, is_package=False, project_label=data.get("project_label", "")
        )

    def _resolve_project_dict(self, project_path: Path) -> dict[str, Any] | None:
        """Build the minimal project dict needed by ``_process_command_file``."""
        import os

        from skill_manager.core.quick_copy import (
            project_label,
            project_root_for_project,
            resolve_resilient_path,
        )

        resolved = resolve_resilient_path(project_path)
        if not resolved:
            return None
        return {
            "project_label": project_label(resolved, self.project_aliases, str(project_path)),
            "project_root": str(project_root_for_project(resolved)),
            "project_path": str(resolved),
            "project_key": os.path.normcase(str(resolved)),
        }

    def discover_single_skill(self, skill_path: Path, project_path: Path) -> dict[str, Any] | None:
        """Parses and normalizes a single skill at skill_path belonging to project_path."""
        return discover_single_skill(skill_path, project_path, self.project_aliases)


def discover_single_skill(
    skill_path: Path, project_path: Path, project_aliases: dict[str, str]
) -> dict[str, Any] | None:
    """Module-level helper: parse a skill folder containing ``SKILL.md``."""
    import os

    from skill_manager.core.parsing import (
        build_skill_search_text,
        categorize_skill,
        parse_skill_md,
    )
    from skill_manager.core.quick_copy import (
        classification_text,
        project_label,
        project_root_for_project,
        resolve_resilient_path,
        skill_base_relative,
    )

    skill_md_path = skill_path / "SKILL.md"
    if not skill_md_path.is_file():
        return None

    resolved_project = resolve_resilient_path(project_path)
    if not resolved_project:
        return None
    project_key = os.path.normcase(str(resolved_project))

    skill_data = parse_skill_md(str(skill_md_path))
    if not skill_data.get("name"):
        skill_data["name"] = skill_path.name
    skill_data["folder_name"] = skill_path.name
    skill_data["local_path"] = str(skill_path)
    skill_data["skill_md_path"] = str(skill_md_path)
    skill_data["project_key"] = project_key
    skill_data["project_path"] = str(resolved_project)
    skill_data["project_root"] = str(project_root_for_project(resolved_project))
    skill_data["skill_base_relative"] = skill_base_relative(resolved_project)
    skill_data["project_label"] = project_label(
        resolved_project, project_aliases, str(project_path)
    )
    skill_data.setdefault("metadata", {})
    cat_info = categorize_skill(
        skill_data.get("name", ""),
        classification_text(skill_data),
        skill_data.get("metadata", {}),
    )
    skill_data["main_category"] = cat_info.get("main_category", "")
    skill_data["category"] = cat_info.get("sub_category", "")
    skill_data["search_text"] = build_skill_search_text(skill_data)

    # Now transform it using public transform_skill
    # We need a DiscoveryService instance to call transform_skill, but this
    # is a module-level function.  For back-compat we just return the raw
    # normalized dict — callers that need the full transform can use the
    # instance method ``discover_single_skill`` on DiscoveryService.
    return skill_data
