"""
Purpose: Manages skill sources, projects, and configuration state.
Usage: Accessed via AppController.config_mgr
"""

import os

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception


class ConfigController(BaseController):
    """Controller for project configuration and sources."""

    def add_source(self, url: str):
        """Adds a local skill source directory."""
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        raw_path = str(path or "").strip()
        if not raw_path:
            return

        try:
            # Resolve to absolute path to prevent CWD dependency issues
            resolved_path = os.path.abspath(os.path.expanduser(raw_path))
            if resolved_path not in self.app._sources:
                self.app._sources.append(resolved_path)
                self.config.set("sources", self.app._sources)
                self.app.sourcesChanged.emit()
                self.app._set_status(f"Added source: {resolved_path}")
                capture_event("skill_package_added", {"source_type": "local"})
        except Exception as e:
            self.app._set_status(f"Failed to add source: {e}")
            capture_exception(e)

    def remove_source(self, path: str):
        """Removes a local skill source directory."""
        if path in self.app._sources:
            self.app._sources.remove(path)
            self.config.set("sources", self.app._sources)
            self.app.sourcesChanged.emit()
            self.app._set_status(f"Removed source: {path}")
            capture_event("skill_package_removed", {"source_type": "local"})

    def add_project(self, url: str):
        """Adds a project directory."""
        if not url or not str(url).strip():
            return
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        if path not in self.app._projects:
            self.app._projects.append(path)
            self.config.set("projects", self.app._projects)
            self.app.projectsChanged.emit()
            self.app._set_status(f"Added project: {path}")
            capture_event("project_target_added", {"target_count": len(self.app._projects)})

    def remove_project(self, path: str):
        """Removes a project directory."""
        if path in self.app._projects:
            self.app._projects.remove(path)
            if path in self.app._syncing_projects:
                self.app._syncing_projects.remove(path)
            # Also remove alias if it exists
            if path in self.app._project_aliases:
                del self.app._project_aliases[path]
                self.config.set("project_aliases", self.app._project_aliases)
            self.config.set("projects", self.app._projects)
            self.app.projectsChanged.emit()
            self.app._set_status(f"Removed project: {path}")

    def get_project_label(self, path: str) -> str:
        """Returns the human-readable label for a project path."""
        if not path:
            return ""
        norm_path = path.replace("\\", "/")
        label = self.app._project_aliases.get(path) or self.app._project_aliases.get(norm_path)
        if not label:
            # Smart label detection for project folders
            if norm_path.endswith("/.agents/skills"):
                label = os.path.basename(os.path.dirname(os.path.dirname(path)))
            elif os.path.basename(path).lower() == "skills" and len(norm_path.split("/")) > 2:
                parent = norm_path.split("/")[-2]
                label = norm_path.split("/")[-3] if parent == ".agents" else parent
            else:
                label = os.path.basename(path)
        return label

    def get_update_projects(self):
        """Returns a list of project info with skill counts and sync status for the UI."""
        results = []
        from pathlib import Path

        for p in self.app._projects:
            count = 0
            try:
                # Dynamic Resolution for accurate skill count in UI
                resolved_path = Path(p)
                if resolved_path.name.lower() not in ("skills", ".agents"):
                    found = False
                    potential = resolved_path / ".agents" / "skills"
                    if potential.exists() and potential.is_dir():
                        resolved_path = potential
                        found = True
                    if not found:
                        resolved_path = resolved_path / ".agents" / "skills"

                scan_path = str(resolved_path)
                if os.path.exists(scan_path):
                    count = len(
                        [
                            d
                            for d in os.listdir(scan_path)
                            if os.path.isdir(os.path.join(scan_path, d))
                        ]
                    )
            except Exception:
                pass
            results.append(
                {
                    "name": self.get_project_label(p),
                    "path": p,
                    "skill_count": count,
                    "is_updating": p in self.app._syncing_projects,
                }
            )
        return results

    def set_project_alias(self, path: str, alias: str):
        """Sets a custom alias for a project."""
        if not path:
            return
        if not alias:
            if path in self.app._project_aliases:
                del self.app._project_aliases[path]
        else:
            self.app._project_aliases[path] = alias

        self.config.set("project_aliases", self.app._project_aliases)
        self.app.projectsChanged.emit()
        self.app.refreshSkills()
        self.app._set_status(f"Renamed project to: {alias or 'Default'}")

    def verify_git_package(self, url: str, token: str = None) -> str:
        """Verifies a git repository and returns its latest tag."""
        if not url:
            return ""
        from skill_manager.core.skill_packages import get_git_tag

        self.app._set_status(f"Verifying repository: {url}")
        tag = get_git_tag(url, is_remote=True, token=token)
        if tag:
            self.app._set_status(f"Repository verified. Latest version: {tag}")
        else:
            self.app._set_status(f"Verification failed for: {url}")
        return tag or ""

    def get_shortcut(self, key: str) -> str:
        """Gets a configured shortcut sequence."""
        return self.config.get("shortcuts", {}).get(key, "")

    def set_shortcut(self, action: str, sequence: str):
        """Sets a shortcut sequence for an action."""
        shortcuts = self.config.get("shortcuts", {})
        if action in shortcuts and shortcuts[action] != sequence:
            shortcuts[action] = sequence
            self.config.set("shortcuts", shortcuts)
            self.app.shortcutsChanged.emit()
            self.app._set_status(f"Shortcut for {action} set to: {sequence}")

    def reset_shortcuts(self):
        """Resets all shortcuts to defaults."""
        from skill_manager.core.config import DEFAULT_SHORTCUTS
        self.config.set("shortcuts", DEFAULT_SHORTCUTS.copy())
        self.app.shortcutsChanged.emit()
        self.app._set_status("All shortcuts reset to defaults")

    def save_cache(self, data: dict):
        """Saves discovered skills to cache for faster startup."""
        import json
        from pathlib import Path
        from skill_manager.core.config import SKILL_LIBRARY_CACHE_FILE

        try:
            excluded = {"raw_content", "body_content"}
            slim_data = dict(data)
            if "skills" in slim_data:
                slim_data["skills"] = [
                    {k: v for k, v in skill.items() if k not in excluded}
                    for skill in slim_data["skills"]
                ]
            print(f"[CACHE] Saving {len(slim_data.get('skills', []))} skills to {SKILL_LIBRARY_CACHE_FILE}...")
            with open(SKILL_LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(slim_data, f, indent=2, default=str)
            size_mb = Path(SKILL_LIBRARY_CACHE_FILE).stat().st_size / 1024 / 1024
            print(f"[CACHE] Save successful ({size_mb:.1f} MB).")
        except Exception as e:
            print(f"Error saving cache: {e}")

    def load_cache(self) -> dict:
        """Loads skills from cache."""
        import json
        import contextlib
        from pathlib import Path
        from skill_manager.core.config import SKILL_LIBRARY_CACHE_FILE

        cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            print(f"[CACHE] Corrupted cache deleted ({e}). Will rebuild on next scan.")
            with contextlib.suppress(OSError):
                cache_path.unlink(missing_ok=True)
        return None
