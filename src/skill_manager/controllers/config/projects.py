"""Project CRUD, labels, caches, and aliases for the ConfigController facade."""

import logging
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot

from skill_manager.core.analytics import capture_event
from skill_manager.core.diagnostics import get_diagnostic_logger

logger = logging.getLogger(__name__)


class ProjectsMixin:
    """Project directory CRUD, label resolution, and cached properties.

    The ``updateProjectsChanged``/``clientFormatsChanged`` signals are
    re-declared here for the ``@Property(notify=...)`` decorators; the
    facade class re-declares them as its canonical class attributes.
    """

    updateProjectsChanged = Signal()
    clientFormatsChanged = Signal()

    @Property(dict, notify=updateProjectsChanged)
    def project_aliases(self):
        return self.app._project_aliases

    @Slot(str)
    def addProject(self, url: str):
        """Adds a project directory with robust validation and normalization."""
        if not url or not str(url).strip():
            return

        from skill_manager.core.copier import normalize_project_skills_path

        clean_path = self.normalize_path(url)
        resolved_path_obj, error = normalize_project_skills_path(clean_path)
        resolved_str = str(resolved_path_obj) if resolved_path_obj else clean_path

        p = Path(resolved_str)
        # Validate that the target path or its parent project root exists on disk
        if not p.exists():
            root_exists = False
            if p.name == "skills" and p.parent.name == ".agents":
                root_exists = p.parent.parent.is_dir()
            elif p.parent.is_dir():
                root_exists = True

            if not root_exists and not p.is_dir():
                msg = f"Project directory does not exist: {resolved_str}"
                logger.warning("[CONFIG] %s", msg)
                self.app._set_status(msg)
                get_diagnostic_logger().log_event(
                    "WARNING",
                    "project_add_invalid_path",
                    msg,
                    data={"raw_input": url, "resolved_path": resolved_str, "error": error},
                )
                return

        if resolved_str and resolved_str not in self.app._projects:
            self.app._projects.append(resolved_str)
            self.config.set("projects", self.app._projects)
            self._emit_projects_changed()
            self.app._set_status(f"Added project: {resolved_str}")
            capture_event("project_target_added", {"target_count": len(self.app._projects)})
            self._refresh_after_project_add(resolved_str)

            get_diagnostic_logger().log_event(
                "INFO",
                "project_added",
                f"Project added: {resolved_str}",
                data={
                    "raw_input": url,
                    "normalized": resolved_str,
                    "error": error,
                },
            )

    @Slot(str)
    def removeProject(self, path: str):
        """Removes a project directory."""
        if path in self.app._projects:
            self.app._projects.remove(path)
            if path in self.app._syncing_projects:
                self.app._syncing_projects.remove(path)
            if path in self.app._project_aliases:
                del self.app._project_aliases[path]
                self.config.set("project_aliases", self.app._project_aliases)
            self.config.set("projects", self.app._projects)
            self._emit_projects_changed()
            self.app._set_status(f"Removed project: {path}")

    @Slot(int, int)
    def reorderProjects(self, from_index: int, to_index: int):
        """Moves a project from one position to another in the list."""
        projects = self.app._projects
        if (
            not projects
            or from_index == to_index
            or from_index < 0
            or from_index >= len(projects)
            or to_index < 0
            or to_index >= len(projects)
        ):
            return

        project = projects.pop(from_index)
        projects.insert(to_index, project)
        self.config.set("projects", projects)
        self._emit_projects_changed()

    @Slot(int)
    def removeUpdateProject(self, index: int):
        """Removes a project by its index in the updates view."""
        if 0 <= index < len(self.app._projects):
            self.removeProject(self.app._projects[index])

    @Property(list, notify=clientFormatsChanged)
    def topBarClients(self):  # type: ignore[reportRedeclaration]
        return self.config.get(
            "top_bar_clients", ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]
        )

    @topBarClients.setter  # type: ignore[func-attr]
    def topBarClients(self, value):
        self._set_config_value("top_bar_clients", value, self.clientFormatsChanged)

    @Property(list, notify=clientFormatsChanged)
    def availableClientFormats(self):
        return ["Plain Text", "Gemini CLI", "Antigravity", "Codex", "OpenCode"]

    @Property(list, notify=clientFormatsChanged)
    def clientFormats(self):
        return self.topBarClients

    @Slot(str, result=str)
    def getProjectPath(self, label: str) -> str:
        """Returns the project path for a given label."""
        for p in self.app._projects:
            if self.getProjectLabel(p) == label:
                return p
        return ""

    @Slot(str, result=str)
    def getProjectLabel(self, path: str) -> str:
        """Returns the human-readable label for a project path.

        Delegates to the canonical ``project_label()`` so that the dropdown
        labels always match the ``project_label`` stored on each skill.
        """
        if not path:
            return ""
        from skill_manager.core.quick_copy import project_label

        return project_label(path, project_aliases=self.app._project_aliases)

    @Property(list, notify=updateProjectsChanged)
    def updateProjects(self):
        """Returns a list of project info with skill counts and sync status for the UI."""
        if self._cached_update_projects is not None:
            return self._cached_update_projects
        results = []

        for p in self.app._projects:
            count = 0
            try:
                resolved_path = Path(p)
                if resolved_path.name.lower() not in ("skills", ".agents"):
                    potential = resolved_path / ".agents" / "skills"
                    if potential.exists() and potential.is_dir():
                        resolved_path = potential
                    else:
                        resolved_path = resolved_path / ".agents" / "skills"

                if resolved_path.exists():
                    count = len([d for d in resolved_path.iterdir() if d.is_dir()])
            except Exception:
                pass
            results.append(
                {
                    "name": self.getProjectLabel(p),
                    "path": p,
                    "skill_count": count,
                    "is_updating": p in self.app._syncing_projects,
                }
            )
        self._cached_update_projects = results
        return results

    @Property(list, notify=updateProjectsChanged)
    def projectLabels(self):
        """Returns a list of human-readable labels for all projects."""
        if self._cached_project_labels is not None:
            return self._cached_project_labels
        self._cached_project_labels = [self.getProjectLabel(p) for p in self.app._projects]
        return self._cached_project_labels

    def _invalidate_project_cache(self):
        """Invalidate cached project data so properties recompute on next access."""
        self._cached_update_projects = None
        self._cached_project_labels = None

    def _emit_projects_changed(self):
        """Emit both project signals and invalidate cache."""
        self.app.projectsChanged.emit()
        self._invalidate_project_cache()
        self.updateProjectsChanged.emit()

    def _refresh_after_project_add(self, project_path: str) -> None:
        """Register the new project's folders with the file watcher, trigger a
        silent background discovery refresh, and link pre-existing skills that
        exactly match a package skill — so the UI updates without a manual
        refresh or restart."""
        try:
            from skill_manager.core.copier import get_commands_dir, get_skills_dir

            watcher = getattr(self.app, "_watcher", None)
            if watcher is not None:
                watcher.add_path(str(get_skills_dir(project_path)))
                watcher.add_path(str(get_commands_dir(project_path)))
        except Exception as exc:
            logger.warning("[CONFIG] Failed to register watcher paths: %s", exc)

        try:
            refresh = getattr(self.app, "loadInitialData", None)
            if refresh is not None:
                refresh()
        except Exception as exc:
            logger.warning("[CONFIG] Failed to trigger discovery refresh: %s", exc)

        task_runner = getattr(self.app, "task_runner", None)
        if task_runner is not None:
            task_runner.run(self._link_added_project_skills, args=(project_path,))

    def _link_added_project_skills(self, project_path: str) -> None:
        """Link pre-existing project skills to package skills when folder name
        and contents match exactly. Runs in the background task runner."""
        from skill_manager.core.update_service import UpdateService

        try:
            update_packages = list(getattr(self.app, "_update_packages", []) or [])
            sources = list(getattr(self.app, "_sources", []) or [])
            for package in update_packages:
                package_path = package.get("package_path") or package.get("local_path")
                if package_path and package_path not in sources:
                    sources.append(package_path)
            UpdateService.link_exact_match_project_skills(
                project_paths=[project_path],
                sources=sources,
                update_packages=update_packages,
                project_aliases=dict(getattr(self.app, "_project_aliases", {}) or {}),
            )
        except Exception:
            logger.exception("[CONFIG] Failed to link added project skills")

    @Slot(str, str)
    def setProjectAlias(self, path: str, alias: str):
        """Sets a custom alias for a project."""
        if not path:
            return
        if not alias:
            if path in self.app._project_aliases:
                del self.app._project_aliases[path]
        else:
            self.app._project_aliases[path] = alias

        self.config.set("project_aliases", self.app._project_aliases)
        self._emit_projects_changed()

        new_label = self.getProjectLabel(path)
        for model in (self.app._library_model, self.app._quick_copy_model):
            model._begin_batch()
            try:
                all_skills = getattr(model, "_all_skills", None)
                if isinstance(all_skills, list):
                    for skill in all_skills:
                        sp = (
                            skill.get("project_path")
                            if isinstance(skill, dict)
                            else getattr(skill, "project_path", None)
                        )
                        if sp and str(sp) == str(path):
                            if isinstance(skill, dict):
                                skill["project_label"] = new_label
                            else:
                                skill.project_label = new_label
            finally:
                model._end_batch()

        self.app._set_status(f"Renamed project to: {alias or 'Default'}")
