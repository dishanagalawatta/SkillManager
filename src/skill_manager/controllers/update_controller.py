"""
Purpose: Manages skill updates, synchronization, and scanning.
Usage: Accessed via AppController.updates
"""

import contextlib
import json
import logging
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.schemas import UpdatePackageRecord
from skill_manager.core.update_service import UpdateService
from skill_manager.utils.qt_threading import schedule_on_ui_thread

logger = logging.getLogger(__name__)


def _safe_single_shot(msec: int, context, functor):
    ctx = context if isinstance(context, QObject) else None
    QTimer.singleShot(msec, ctx, functor)


class UpdateController(BaseController):
    """Controller for skill updates and synchronization."""

    # Toast signals consumed by the UpdateToast host in Main.qml.
    updatesAvailable = Signal(int)  # count of outdated packages
    autoUpdateFinished = Signal(int, int)  # updated, failed
    # Emitted whenever the package list changes; the curated catalog is
    # derived from it.
    catalogChanged = Signal()

    def __init__(self, app):
        super().__init__(app)
        self._auto_update_in_flight = False
        # Scan lifecycle (see _finish_scan): generation guards against a stale
        # watchdog or a late worker result mutating current state.
        self._scan_generation = 0
        self._scan_finished = False
        self._scan_watchdog = None

    # ── Curated catalog ───────────────────────────────────────────────

    def _emit_packages_changed(self) -> None:
        """Notify every listener that the package list changed.

        The curated catalog is derived from the package list, so it has to
        be refreshed together with it.
        """
        self.app.updatePackagesChanged.emit()
        self.catalogChanged.emit()

    @Property("QVariantList", notify=catalogChanged)
    def catalogPackages(self) -> list:
        """The curated package catalog, enriched with the install status.

        Each entry carries ``is_installed`` and ``installed_package_id`` so
        the UI can show an "Installed" badge and offer a reconfigure action.
        """
        from skill_manager.core.skill_packages import catalog_with_status

        try:
            return catalog_with_status(list(self.app._update_packages))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not build the package catalog: %s", exc)
            return []

    @Slot(str, result=dict)
    def catalogPackage(self, catalog_id: str) -> dict:
        """Return one catalog entry (as a dict) by id."""
        from skill_manager.core.skill_packages import find_catalog_entry

        entry = find_catalog_entry(catalog_id)
        if entry is None:
            return {}
        data = entry.model_dump()
        from skill_manager.core.skill_packages import matches_installed_package

        match = matches_installed_package(entry, list(self.app._update_packages))
        data["is_installed"] = match is not None
        data["installed_package_id"] = match or ""
        return data

    @Slot(str, result=str)
    def installCatalogPackageDefault(self, catalog_id: str) -> str:
        """Install a catalog entry with its default configuration.

        The catalog's install command is parsed into a normal package
        config, the default storage path is resolved, and the regular
        add-package flow takes over (version probe, save, background
        install). Returns a JSON dict with ``ok``/``error``/``name``.
        """
        from skill_manager.core.skill_packages import (
            find_catalog_entry,
            template_to_package_data,
        )

        entry = find_catalog_entry(catalog_id)
        if entry is None:
            error = f"Unknown catalog package: {catalog_id}"
            self.app._set_status(error)
            return json.dumps({"ok": False, "error": error, "name": ""})

        try:
            data = template_to_package_data(entry)
            target_path = self._default_package_storage_path(entry)
            if target_path:
                data["package_path"] = target_path

            self.app._set_status(f"Installing {entry.display_name}...")
            return self.addSkillPackage(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Catalog install failed for %s: %s", catalog_id, exc)
            error = str(exc)
            self.app._set_status(f"Install failed: {error}")
            return json.dumps({"ok": False, "error": error, "name": entry.display_name})

    def _default_package_storage_path(self, _entry=None) -> str:
        """The default storage location for a catalog package.

        Uses the same directory the other packages live in, so a catalog
        install lands next to the packages the user already has.
        """
        import os

        try:
            from skill_manager.core.config import DATA_DIR

            base = os.path.join(str(DATA_DIR), "packages")
            os.makedirs(base, exist_ok=True)
            return base
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not resolve the default package path: %s", exc)
            return ""

    def _publish_project_sync_state(self):
        """Publish a ``_syncing_projects`` change to every QML binding.

        ``ConfigController.updateProjects`` is cached and derives
        ``is_updating`` from ``app._syncing_projects``.  Emitting only
        ``projectsChanged`` leaves the cache stale, so project progress bars
        spin forever.  This helper invalidates + emits
        ``updateProjectsChanged`` first, then ``projectsChanged``.
        """
        self.app.config_mgr.publishProjectSyncState()
        self.app.projectsChanged.emit()

    def _resolvePackageStorageState(self):
        """Internal helper to refresh package state from config.

        Mutates ``app._update_packages`` in place so that every reference
        captured by QML delegates (``modelData``) or background workers
        stays valid.  Emits ``updatePackagesChanged`` once at the end.
        """
        from skill_manager.core.persistence import load_package_skill_inventory
        from skill_manager.core.skill_packages import (
            normalize_skill_package_config,
            resolve_package_storage,
        )

        packages = []
        for package in self.app._update_packages:
            try:
                # Ensure each package in memory is a valid record
                normalized = normalize_skill_package_config(package)
                record = UpdatePackageRecord.model_validate({**normalized, **package})
                packages.append(record.model_dump())
            except Exception as e:
                # Keep the record instead of dropping it.  Dropping shortened
                # the list, and because the write-back below is positional,
                # every later entry was repointed at the previous package's
                # storage path (and the tail was deleted outright).
                logger.error("Failed to normalize package during storage resolution: %s", e)
                packages.append(dict(package))

        refreshed = resolve_package_storage(packages, load_package_skill_inventory())

        # The write-back below is positional, so guard the invariant it relies
        # on: resolve_package_storage maps one input record to one output
        # record, in order.  If that ever changes, append rather than truncate.
        if len(refreshed) < len(self.app._update_packages):
            logger.error(
                "Storage resolution returned %d records for %d packages; "
                "appending the remainder instead of truncating.",
                len(refreshed),
                len(self.app._update_packages),
            )
            refreshed = refreshed + [dict(p) for p in self.app._update_packages[len(refreshed) :]]

        # Update each dict in place so that every captured reference (QML
        # modelData, background workers) keeps pointing at the same object.
        for i, item in enumerate(refreshed):
            if i < len(self.app._update_packages):
                self.app._update_packages[i].clear()
                self.app._update_packages[i].update(item)
            else:
                self.app._update_packages.append(item)

        # Remove excess entries when the resolved list is shorter.
        del self.app._update_packages[len(refreshed) :]

        self.config.set("skills", self.app._update_packages)
        self._emit_packages_changed()

    @Slot()
    def updateNow(self):
        """Starts a global update of all skills and projects."""
        if (
            any(s.get("is_updating") for s in self.app._update_packages)
            or self.app._syncing_projects
        ):
            self._auto_update_in_flight = False
            self.app._set_status("Update already in progress...")
            return

        self.app._set_status("Starting global update...")

        # Mark projects as syncing
        for p in self.app._projects:
            if p not in self.app._syncing_projects:
                self.app._syncing_projects.append(p)
        self._publish_project_sync_state()

        # Mark sources as updating
        for s in self.app._update_packages:
            s["is_updating"] = True
            s["just_finished"] = False
        self._emit_packages_changed()

        service = UpdateService(
            sources=self.app._sources,
            projects=self.app._projects,
            update_packages=self.app._update_packages,
            project_aliases=self.app._project_aliases,
            task_runner=self.app.task_runner,
        )

        def source_progress_callback(idx, data):
            def update_item():
                if 0 <= idx < len(self.app._update_packages):
                    self.app._update_packages[idx] = data
                    self._emit_packages_changed()

            _safe_single_shot(0, self.app, update_item)

        def completion_callback(result, _updated_sources):
            def finalize():
                # Belt-and-braces: progress callbacks normally clear each
                # package, but a missed/failed callback must never strand a
                # spinner.  just_finished is left as delivered per package.
                for s in self.app._update_packages:
                    s["is_updating"] = False
                self._emit_packages_changed()
                # Refresh the header/button immediately: updated packages
                # carry promoted versions, so the outdated count drops to 0
                # without waiting for the next scan.
                self.recalculateStats()

                self.app.loadInitialData()
                msg = (
                    f"Global update complete: {result['merged']} updated, {result['failed']} failed"
                )
                self.app._set_status(msg)

                # Capture analytics
                capture_event(
                    "skill_package_updated",
                    {"source_type": "global", "success": result["failed"] == 0},
                )

                # Notify via toast when this run was auto-triggered; manual
                # runs already surface the status pill message above.
                if self._auto_update_in_flight:
                    self._auto_update_in_flight = False
                    self.autoUpdateFinished.emit(result["merged"], result["failed"])

                self.config.set("skills", self.app._update_packages)
                self.app._syncing_projects = []
                self._publish_project_sync_state()

            _safe_single_shot(0, self.app, finalize)

        try:
            service.run_global_update(
                status_callback=self.app._set_status,
                source_progress_callback=source_progress_callback,
                completion_callback=completion_callback,
            )
        except Exception as e:
            capture_exception(e)
            self._auto_update_in_flight = False
            for s in self.app._update_packages:
                s["is_updating"] = False
            self._emit_packages_changed()
            self.app._syncing_projects = []
            self._publish_project_sync_state()
            self.app._set_status(f"Failed to start global update: {e}")

    # Hard ceiling for a whole scan.  Individual probes are bounded, but a
    # wedged worker thread would otherwise leave ``_is_loading`` True forever,
    # which made every later scan bail out with "Update scan already
    # running..." — indistinguishable from "updates stopped working".
    SCAN_WATCHDOG_MS = 90_000

    @Slot()
    def scanForUpdates(self):
        """Scans all sources and projects for potential updates."""
        if self.app._is_loading:
            self.app._set_status("Update scan already running...")
            return

        self._scan_generation += 1
        generation = self._scan_generation
        self._scan_finished = False

        self.app._set_status("Scanning for updates...")
        self.app._is_loading = True
        self.app.isLoadingChanged.emit()

        service = UpdateService(
            sources=self.app._sources,
            projects=self.app._projects,
            update_packages=self.app._update_packages,
            project_aliases=self.app._project_aliases,
            task_runner=self.app.task_runner,
        )

        self._arm_scan_watchdog(generation, service)

        def completion_callback(results, updated_sources):
            _safe_single_shot(
                0,
                self.app,
                lambda: self._finish_scan(
                    generation,
                    service=service,
                    results=results,
                    updated_sources=updated_sources,
                ),
            )

        try:
            service.scan_for_updates(
                status_callback=self.app._set_status, completion_callback=completion_callback
            )
        except Exception as e:
            capture_exception(e)
            self._finish_scan(generation, error=e)

    def _arm_scan_watchdog(self, generation: int, service) -> None:
        """Force-finish the scan if the worker never reports back.

        Uses a real ``QTimer`` instance rather than ``QTimer.singleShot`` so
        it can be cancelled the moment the scan completes, and so tests that
        stub the static helper cannot fire it by accident.
        """
        self._stop_scan_watchdog()
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self.SCAN_WATCHDOG_MS)
        timer.timeout.connect(
            lambda: self._finish_scan(generation, service=service, timed_out=True)
        )
        self._scan_watchdog = timer
        timer.start()

    def _stop_scan_watchdog(self) -> None:
        timer = self._scan_watchdog
        self._scan_watchdog = None
        if timer is not None:
            with contextlib.suppress(Exception):
                timer.stop()

    def _finish_scan(
        self,
        generation: int,
        *,
        service=None,
        results=None,
        updated_sources=None,
        error: BaseException | None = None,
        timed_out: bool = False,
    ):
        """Single exit path for a scan; always clears the loading flag.

        Guarded by ``generation`` so a watchdog firing after a scan already
        finished cannot clobber newer state, and so a late result from a
        timed-out scan is discarded instead of resurrecting a stale flag.
        """
        if generation != self._scan_generation or self._scan_finished:
            return
        self._scan_finished = True
        self._stop_scan_watchdog()

        if results is not None:
            self.app._update_results = results
        if updated_sources is not None:
            self.app._update_packages = updated_sources

        self.recalculateStats()
        self.app._is_loading = False
        self.app.isLoadingChanged.emit()
        self._emit_packages_changed()

        if timed_out:
            logger.warning(
                "Update scan exceeded %ss; finalised with partial results.",
                self.SCAN_WATCHDOG_MS // 1000,
            )
            self.app._set_status("Update scan failed: a repository did not respond in time.")
            return

        if error is not None:
            logger.error("Failed to start update scan: %s", error)
            self.app._set_status(f"Failed to start update scan: {error}")
            return

        # The service swallows its own exceptions so it can still emit a
        # completion; without this the failure showed up as
        # "Update scan complete: 0".  ``str`` check keeps mocks out.
        scan_error = getattr(service, "last_scan_error", None) if service is not None else None
        if isinstance(scan_error, str) and scan_error:
            logger.error("Update scan failed: %s", scan_error)
            self.app._set_status(f"Update scan failed: {scan_error}")
            return

        unchecked = [
            p for p in (self.app._update_packages or []) if p.get("check_status") == "failed"
        ]
        message = (
            f"Update scan complete: {len(self.app._update_results or [])} package skills processed"
        )
        if unchecked:
            message += f" — could not check {len(unchecked)} package(s)"
        self.app._set_status(message)

        # Auto-update decision point: Auto Update on applies updates in the
        # background; off notifies via toast instead.  Update checks always run
        # (startup + periodic) in both states.  Skipped when the scan did not
        # complete, so a partial scan cannot trigger updates on stale data.
        auto_update = self.config.get("skill_package_auto_update", False)
        if isinstance(auto_update, str):
            auto_update = auto_update.strip().lower() == "silent"
        outdated = getattr(self.app, "_stats_outdated", 0)
        if outdated <= 0:
            return
        if auto_update:
            logger.info("Auto-update triggered for outdated skill packages.")
            self._auto_update_in_flight = True
            self.updateNow()
        else:
            logger.info("Auto-update off: notifying %d available update(s).", outdated)
            self.updatesAvailable.emit(outdated)

    @Slot(str, str)
    def updateSkillInProject(self, skill_name: str, project_name: str):
        """Updates a specific skill in a specific project."""
        self.app._set_status(f"Updating {skill_name} in {project_name}...")

        def run_surgical_sync():
            try:
                # 1. Find source skill
                source_skill = next(
                    (
                        s
                        for s in self.app._library_model._all_skills
                        if s.get("is_source") and s.get("name") == skill_name
                    ),
                    None,
                )
                if not source_skill:
                    self.app._set_status(f"Error: Could not find source skill {skill_name}")
                    return

                # 2. Find project path
                project_path = next(
                    (p for p in self.app._projects if self.app.getProjectLabel(p) == project_name),
                    None,
                )
                if not project_path:
                    self.app._set_status(f"Error: Could not find project {project_name}")
                    return

                # 3. Perform copy
                from skill_manager.core.copier import copy_skill_folders_to_projects

                result = copy_skill_folders_to_projects(
                    [source_skill], [project_path], update_only=True
                )

                msg = f"Updated {skill_name} in {project_name}"
                if result["failed"] > 0:
                    msg = f"Failed to update {skill_name} in {project_name}"

                schedule_on_ui_thread(self.app, lambda: self.app._set_status(msg))
                schedule_on_ui_thread(self.app, self.scanForUpdates, delay_ms=500)
            except Exception as e:
                err_msg = f"Surgical update failed: {e}"
                capture_exception(e)
                schedule_on_ui_thread(self.app, lambda: self.app._set_status(err_msg))

        self.app.task_runner.run(run_surgical_sync)

    @Slot()
    def recalculateStats(self):
        """Recalculates the up-to-date/outdated/missing stats.

        ``_stats_outdated`` is the single source of truth behind the
        UpdatesView header (``N updates``), the Update All button, and the
        Silent/Prompt auto-update triggers — and it counts **outdated
        packages only** (``current_version != latest_version`` via
        :func:`is_package_outdated`).

        This 1:1 match with the package cards is intentional: each outdated
        package renders its own Update button, and Update All applies the
        same package updates, so the header, the button, and the cards can
        never disagree.  Skill-level content drift (a project copy edited
        by hand) stays in ``_update_results`` as inspector detail but does
        not arm the header — it is invisible in the Updates view (the skill
        inspector is never opened) and Update All would otherwise stay
        enabled with nothing actionable to do.

        ``_stats_up_to_date`` / ``_stats_missing`` remain skill-level scan
        detail for diagnostics and telemetry.
        """
        from skill_manager.core.skill_packages.versioning import (
            count_outdated_packages,
            count_unchecked_packages,
        )

        up_to_date = 0
        missing = 0
        for item in self.app._update_results:
            if item["status"] == "up_to_date":
                up_to_date += 1
            elif item["status"] == "missing":
                missing += 1

        try:
            package_outdated = count_outdated_packages(getattr(self.app, "_update_packages", []))
        except Exception:
            package_outdated = 0

        try:
            unchecked = count_unchecked_packages(getattr(self.app, "_update_packages", []))
        except Exception:
            unchecked = 0

        self.app._stats_up_to_date = up_to_date
        self.app._stats_outdated = package_outdated
        self.app._stats_missing = missing
        self.app._stats_unchecked = unchecked
        self.app.statsChanged.emit()

    def _register_package_watcher(self, package_path: str) -> None:
        """Watch a newly added package directory so its skills appear live.

        Deliberately does *not* refresh discovery: the install that follows an
        add ends with its own refresh, and the old immediate one walked every
        source and project *before* a single file of the package existed.
        """
        try:
            watcher = getattr(self.app, "_watcher", None)
            if watcher is not None and package_path:
                p = Path(package_path).expanduser().resolve()
                if p.is_dir():
                    watcher.add_path(str(p))
        except Exception as exc:
            logger.warning("[CONFIG] Failed to register package watcher path: %s", exc)

    # Adding several packages in a row, or an edit landing while an install
    # finishes, used to stack full filesystem scans.  Rapid repeats are folded
    # into one: discovery walks every source and project, and the end state is
    # identical whichever scan discovered it.
    REFRESH_COALESCE_MS = 400

    def _schedule_discovery_refresh(self) -> None:
        """Request a discovery refresh, folding rapid repeats into one run."""
        if getattr(self, "_refresh_scheduled", False):
            return
        self._refresh_scheduled = True

        def run_refresh():
            self._refresh_scheduled = False
            refresh = getattr(self.app, "loadInitialData", None)
            if refresh is None:
                return
            try:
                refresh()
            except Exception as exc:
                logger.warning("[CONFIG] Failed to trigger discovery refresh: %s", exc)

        _safe_single_shot(self.REFRESH_COALESCE_MS, self.app, run_refresh)

    @Slot(str)
    def addUpdatePackage(self, package_name: str):
        """Adds a basic NPX-style source."""
        if not package_name:
            return
        try:
            record = UpdatePackageRecord(
                name=package_name,
                source_type="npx",
                package_name=package_name,
            )
            self.app._update_packages.append(record.model_dump())
            self._resolvePackageStorageState()
            self.app._set_status(f"Added update package: {package_name}")

            new_index = len(self.app._update_packages) - 1
            pkg_record = self.app._update_packages[new_index]
            pkg_path = (
                pkg_record.get("resolved_package_path")
                or pkg_record.get("package_path")
                or pkg_record.get("local_path")
                or ""
            )
            # The install below runs its own discovery refresh; skipping the
            # immediate one avoids a redundant full filesystem scan per add.
            self._register_package_watcher(pkg_path)
            QTimer.singleShot(500, lambda idx=new_index: self.runPackageUpdate(idx))
        except Exception as e:
            logger.error("Failed to add update package: %s", e)
            self.app._set_status(f"Error adding package: {e}")

    @Slot(dict, result=str)
    def addSkillPackage(self, data: dict) -> str:
        """Adds a fully configured skill package (git/npx/custom).

        Returns a JSON-encoded dict with keys ``ok`` (bool), ``error``
        (str | None), and ``name`` (str).  QML callers should inspect the
        return value and show an inline error on failure instead of closing
        the dialog.
        """
        if not data:
            return json.dumps({"ok": False, "error": "No data provided.", "name": ""})

        from skill_manager.core.skill_packages import (
            RemoteProbeCache,
            check_skill_package_versions,
            normalize_skill_package_config,
        )

        try:
            # 1. Normalize and Validate
            normalized = normalize_skill_package_config(data)
            record = UpdatePackageRecord.model_validate(normalized)
            record.is_updating = False
            record.last_updated = "Never"

            # One cache for both phases below: phase 2 re-probes the same
            # remote as phase 1, which used to be a second blocking round-trip
            # on the UI thread.
            cache = RemoteProbeCache()

            # 2. Phase 1 — detect latest_version only (no snap yet)
            detected_data = check_skill_package_versions(record.model_dump(), remote_cache=cache)

            # 3. Block save only if package is completely unidentifiable and latest_version is undetectable
            if not detected_data.get("latest_version"):
                if record.package_name or record.repository_url or record.update_command:
                    detected_data["latest_version"] = "latest"
                else:
                    pkg_name = record.name or "unknown"
                    error_msg = (
                        f'Could not detect latest version for "{pkg_name}". '
                        "Provide a repository URL or a latest_version_command and try again."
                    )
                    self.app._set_status(f"Add failed: {error_msg}")
                    return json.dumps({"ok": False, "error": error_msg, "name": pkg_name})

            # A probe that could not reach the remote is not a clean add: tell
            # the caller so it can warn instead of silently pinning "latest".
            probe_warning = (
                str(detected_data.get("check_error") or "")
                if detected_data.get("check_status") == "failed"
                else ""
            )

            # 4. Phase 2 — snap current_version = latest_version on add
            synced_data = check_skill_package_versions(
                detected_data, sync_current_to_latest=True, remote_cache=cache
            )
            final_record = UpdatePackageRecord.model_validate(synced_data)

            # 5. Commit to state.  The install itself runs in the background a
            #    moment later, so the record starts from an explicit pending
            #    state rather than claiming to be installed and up to date.
            final_record.last_updated = "Installing…"
            final_record.update_error = ""
            self.app._update_packages.append(final_record.model_dump())
            self._resolvePackageStorageState()
            status = f"Added skill package: {final_record.name} (installing…)"
            if probe_warning:
                status += f" — could not check for updates: {probe_warning}"
            self.app._set_status(status)
            capture_event("skill_package_added", {"source_type": final_record.source_type})

            new_index = len(self.app._update_packages) - 1
            pkg_record = self.app._update_packages[new_index]
            pkg_path = (
                pkg_record.get("resolved_package_path")
                or pkg_record.get("package_path")
                or pkg_record.get("local_path")
                or ""
            )
            # The install below triggers its own discovery refresh, so the
            # immediate one is skipped — it used to walk every source and
            # project before a single file of this package existed on disk.
            self._register_package_watcher(pkg_path)

            # 6. Trigger initial install in background so skill files are
            #    actually downloaded/relocated into the resolved package
            #    storage path.  Without this the package metadata shows
            #    "Up to Date" (current_version == latest_version) but no
            #    skill folders exist on disk yet.
            new_index = len(self.app._update_packages) - 1
            QTimer.singleShot(500, lambda idx=new_index: self.runPackageUpdate(idx))

            # ``ok`` means "added and saved"; ``installing`` states that the
            # files are still being fetched, and ``warning`` carries a failed
            # version probe so the caller can surface it honestly.
            return json.dumps(
                {
                    "ok": True,
                    "error": None,
                    "name": final_record.name,
                    "installing": True,
                    "check_status": final_record.check_status,
                    "warning": probe_warning,
                }
            )
        except Exception as e:
            logger.error("Failed to add skill package: %s", e)
            self.app._set_status(f"Error adding skill package: {e}")
            return json.dumps({"ok": False, "error": str(e), "name": data.get("name", "")})

    @Slot(int, dict, result=str)
    def updateUpdatePackage(self, index: int, data: dict) -> str:
        """Updates configuration for an existing skill package.

        Returns a JSON-encoded dict with keys ``ok`` (bool), ``error``
        (str | None), and ``name`` (str).  QML callers should inspect the
        return value and show an inline error on failure instead of closing
        the dialog.
        """
        if not (0 <= index < len(self.app._update_packages)):
            return json.dumps({"ok": False, "error": "Invalid package index.", "name": ""})

        if not data:
            return json.dumps({"ok": False, "error": "No data provided.", "name": ""})

        from skill_manager.core.skill_packages import (
            RemoteProbeCache,
            check_skill_package_versions,
            normalize_skill_package_config,
        )

        try:
            # Preserve internal state from existing record
            existing = self.app._update_packages[index]
            is_updating = existing.get("is_updating", False)
            just_finished = existing.get("just_finished", False)
            last_updated = existing.get("last_updated", "Never")

            # One cache for both phases below: without it the same remote is
            # listed twice, doubling the latency of every edit.
            remote_cache = RemoteProbeCache()

            # 1. Normalize and Validate
            normalized = normalize_skill_package_config(data)
            record = UpdatePackageRecord.model_validate(normalized)
            record.is_updating = is_updating
            record.just_finished = just_finished
            record.last_updated = last_updated

            # 2. Phase 1 — detect latest_version only (no snap yet)
            detected_data = check_skill_package_versions(
                record.model_dump(), remote_cache=remote_cache
            )

            # 3. Block save only if package is completely unidentifiable and latest_version is undetectable
            if not detected_data.get("latest_version"):
                if record.package_name or record.repository_url or record.update_command:
                    detected_data["latest_version"] = existing.get("latest_version") or "latest"
                else:
                    pkg_name = record.name or "unknown"
                    error_msg = (
                        f'Could not detect latest version for "{pkg_name}". '
                        "Provide a repository URL or a latest_version_command and try again."
                    )
                    self.app._set_status(f"Edit failed: {error_msg}")
                    return json.dumps({"ok": False, "error": error_msg, "name": pkg_name})

            # 4. Phase 2 — snap current_version = latest_version on edit
            synced_data = check_skill_package_versions(
                detected_data, sync_current_to_latest=True, remote_cache=remote_cache
            )
            final_record = UpdatePackageRecord.model_validate(synced_data)

            # Re-apply internal state (model_validate defaults these)
            final_record.is_updating = is_updating
            final_record.just_finished = just_finished
            final_record.last_updated = last_updated

            # 5. Commit to state
            self.app._update_packages[index] = final_record.model_dump()
            self._resolvePackageStorageState()

            # Informative log: show what was saved and the version check result
            current_ver = final_record.current_version or "unknown"
            latest_ver = final_record.latest_version or "unknown"
            status_msg = (
                f"Package settings saved: {final_record.name} "
                f"(version check: {current_ver} → {latest_ver})"
            )
            self.app._set_status(status_msg)

            # Diagnostic log with full context
            from skill_manager.core.diagnostics import (
                CATEGORY_UPDATE_RESULT,
                get_diagnostic_logger,
            )

            get_diagnostic_logger().log_event(
                "INFO",
                CATEGORY_UPDATE_RESULT,
                f"Config saved for package: {final_record.name}",
                data={
                    "package_id": final_record.package_id,
                    "source_type": final_record.source_type,
                    "current_version": final_record.current_version,
                    "latest_version": final_record.latest_version,
                    "repository_url": final_record.repository_url,
                    "index": index,
                },
            )

            return json.dumps({"ok": True, "error": None, "name": final_record.name})
        except Exception as e:
            logger.error("Failed to update skill package: %s", e)
            self.app._set_status(f"Error updating skill package: {e}")
            return json.dumps({"ok": False, "error": str(e), "name": data.get("name", "")})

    @Slot(int)
    def removeUpdatePackage(self, index: int):
        """Removes a skill package and completely cleans up its local files."""
        if not (0 <= index < len(self.app._update_packages)):
            return

        import os

        from skill_manager.core.persistence import (
            load_package_skill_inventory,
            load_project_skill_ownership,
            patch_cache_remove,
            save_package_skill_inventory,
            save_project_skill_ownership,
        )
        from skill_manager.core.skill_packages import delete_package_storage

        source = dict(self.app._update_packages[index])
        pkg_name = source.get("name") or "package"
        pkg_id = source.get("package_id") or ""
        pkg_path = (
            source.get("resolved_package_path")
            or source.get("package_path")
            or source.get("local_path")
            or ""
        )

        # 1. Identify all skill paths belonging to this package across models and on disk
        deleted_skill_paths = set()
        if pkg_path:
            with contextlib.suppress(Exception):
                norm_pkg_path = str(Path(os.path.expanduser(pkg_path)).resolve()).casefold()
                for model in (
                    getattr(self.app, "_library_model", None),
                    getattr(self.app, "_quick_copy_model", None),
                ):
                    if model is not None and hasattr(model, "_all_skills"):
                        for s in model._all_skills:
                            lp = (
                                s.get("local_path", "")
                                if isinstance(s, dict)
                                else getattr(s, "local_path", "")
                            )
                            if lp:
                                with contextlib.suppress(Exception):
                                    if (
                                        str(Path(os.path.expanduser(lp)).resolve())
                                        .casefold()
                                        .startswith(norm_pkg_path)
                                    ):
                                        deleted_skill_paths.add(lp)

            for folder in source.get("managed_folders", []):
                with contextlib.suppress(Exception):
                    deleted_skill_paths.add(str(Path(os.path.expanduser(pkg_path)) / folder))

        inv = load_package_skill_inventory()
        if pkg_id and pkg_id in inv:
            for skill_info in inv[pkg_id].get("skills", {}).values():
                if isinstance(skill_info, dict) and skill_info.get("local_path"):
                    deleted_skill_paths.add(skill_info["local_path"])

        # 2. Safely clean up disk storage, clones, and manifests
        protected = list(getattr(self.app, "_projects", []) or []) + list(
            getattr(self.app, "_sources", []) or []
        )
        cleanup_result = delete_package_storage(source, protected_paths=protected)
        deletion_errors = list(cleanup_result.get("errors") or [])
        if deletion_errors:
            # Abort instead of dropping the record.  The old behaviour removed
            # the package from the list and config while its files stayed on
            # disk, leaving orphans with no way for the user to retry.
            logger.error(
                "Aborting removal of %s: %d storage error(s): %s",
                pkg_name,
                len(deletion_errors),
                "; ".join(str(e) for e in deletion_errors[:3]),
            )
            self.app._set_status(f"Could not remove {pkg_name}: {deletion_errors[0]}")
            return

        deleted_skill_paths.update(cleanup_result.get("deleted_skill_paths", []))

        # 3. Clean up persistence (inventory, ownership, cache)
        if pkg_id and pkg_id in inv:
            del inv[pkg_id]
            save_package_skill_inventory(inv)

        if pkg_id:
            ownership = load_project_skill_ownership()
            ownership_changed = False
            for proj_map in ownership.values():
                if isinstance(proj_map, dict):
                    folders_to_del = [f for f, pid in proj_map.items() if pid == pkg_id]
                    for f in folders_to_del:
                        del proj_map[f]
                        ownership_changed = True
            if ownership_changed:
                save_project_skill_ownership(ownership)

        if deleted_skill_paths:
            patch_cache_remove(list(deleted_skill_paths))

        # 4. Clean up in-memory UI models
        if deleted_skill_paths:
            if hasattr(self.app, "_library_model") and hasattr(
                self.app._library_model, "removeSkillsByPath"
            ):
                self.app._library_model.removeSkillsByPath(list(deleted_skill_paths))
            if hasattr(self.app, "_quick_copy_model") and hasattr(
                self.app._quick_copy_model, "removeSkillsByPath"
            ):
                self.app._quick_copy_model.removeSkillsByPath(list(deleted_skill_paths))

            # Reset selected skill if it was deleted
            cur_sel = getattr(self.app, "_selected_skill", None)
            cur_sel_path = ""
            if cur_sel is not None:
                cur_sel_path = (
                    cur_sel.get("local_path", "")
                    if isinstance(cur_sel, dict)
                    else getattr(cur_sel, "local_path", "")
                )
            if cur_sel_path and cur_sel_path in deleted_skill_paths:
                if hasattr(self.app, "ops") and hasattr(self.app.ops, "setSelectedSkill"):
                    self.app.ops.setSelectedSkill({})
                elif hasattr(self.app, "set_selected_skill"):
                    self.app.set_selected_skill({})

        # 5. Clean up file watcher
        if pkg_path and hasattr(self.app, "_watcher") and self.app._watcher:
            try:
                self.app._watcher.remove_path(pkg_path)
            except Exception as exc:
                logger.debug("Failed unwatching package path: %s", exc)

        # 6. Remove from _update_packages and update config
        self.app._update_packages.pop(index)
        self._resolvePackageStorageState()

        # 7. Clean up update scan results and recalculate stats
        if hasattr(self.app, "_update_results") and self.app._update_results:
            self.app._update_results = [
                r
                for r in self.app._update_results
                if r.get("package_id") != pkg_id
                and r.get("name") != pkg_name
                and r.get("package_name") != source.get("package_name")
            ]
            self.recalculateStats()

        self.app._set_status(f"Removed update package: {pkg_name}")
        capture_event(
            "skill_package_removed", {"source_type": source.get("source_type", "unknown")}
        )

    @Slot(int)
    def runPackageUpdate(self, index: int):
        """Runs update for a single skill package."""
        from skill_manager.core.diagnostics import (
            CATEGORY_UPDATE_RESULT,
            CATEGORY_UPDATE_SLOT,
            get_diagnostic_logger,
        )

        if 0 <= index < len(self.app._update_packages):
            diag = get_diagnostic_logger()
            diag.log_event(
                "INFO",
                CATEGORY_UPDATE_SLOT,
                f"runPackageUpdate({index}) invoked",
                data={"package_count": len(self.app._update_packages)},
            )

            self._resolvePackageStorageState()

            # Replace the dict (not mutate in-place) so QML's QVariantMap
            # snapshot is invalidated and delegate bindings re-evaluate.
            source = dict(self.app._update_packages[index])
            if source.get("is_updating"):
                self.app._set_status(f"Update already in progress for {source.get('name')}...")
                return
            package_id = source.get("package_id")
            source["is_updating"] = True
            source["just_finished"] = False
            source["update_error"] = ""
            self.app._update_packages[index] = source
            self._emit_packages_changed()
            self.app._set_status(f"Updating {source.get('name')}...")

            diag.log_event(
                "DEBUG",
                CATEGORY_UPDATE_SLOT,
                f"Package {source.get('name')} marked is_updating=True",
            )

            def run():
                from datetime import datetime
                from pathlib import Path

                from skill_manager.core.persistence import load_package_skill_inventory
                from skill_manager.core.skill_packages import package_project_path_conflicts
                from skill_manager.core.update_service import update_single_package

                try:
                    pkg_path = (
                        source.get("resolved_package_path")
                        or source.get("package_path")
                        or source.get("local_path")
                    )
                    if not pkg_path and self.app._sources:
                        potential_path = self.app._sources[0]
                        if Path(potential_path).resolve() == Path.cwd().resolve():
                            source["package_path"] = str(
                                Path(potential_path) / ".agents" / "skills"
                            )
                        else:
                            source["package_path"] = potential_path
                    else:
                        source["package_path"] = pkg_path

                    conflicts = package_project_path_conflicts([source], self.app._projects)
                    if conflicts:
                        conflict_path = conflicts[0]
                        raise RuntimeError(
                            f"Package storage path overlaps a project skills path: {conflict_path}"
                        )

                    def log_callback(msg):
                        _safe_single_shot(0, self.app, lambda: self.app._set_status(msg))

                    inventory = load_package_skill_inventory()
                    previous_inventory = inventory.get(source.get("package_id"), {})  # type: ignore[arg-type,call-overload]
                    updated_source = update_single_package(source, previous_inventory, log_callback)
                    source.update(updated_source)
                    source["update_error"] = ""
                    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    diag.log_event(
                        "INFO",
                        CATEGORY_UPDATE_RESULT,
                        f"Package {source.get('name')} updated successfully",
                    )
                    capture_event(
                        "skill_package_updated",
                        {"source_type": source.get("source_type", "unknown"), "success": True},
                    )
                except Exception as e:
                    err_detail = getattr(e, "output", "") or str(e)
                    source["update_error"] = str(e)
                    diag.log_event(
                        "ERROR",
                        CATEGORY_UPDATE_RESULT,
                        f"Package {source.get('name')} update failed: {e}",
                        data={"error": str(e)},
                    )
                    capture_event(
                        "skill_package_updated",
                        {"source_type": source.get("source_type", "unknown"), "success": False},
                    )
                    capture_exception(e)
                    err_msg = f"Update failed for {source.get('name')}: {err_detail}"
                    _safe_single_shot(0, self.app, lambda: self.app._set_status(err_msg))
                finally:

                    def finalize_ui():
                        source["is_updating"] = False
                        source["just_finished"] = True
                        # Commit by package_id, not the closed-over index: an
                        # add/remove while the worker ran shifts positions, and
                        # a positional write would corrupt a different row (or
                        # raise IndexError and strand the spinner).
                        target = self._resolve_package_index(index, package_id)
                        if target is None:
                            logger.debug(
                                "runPackageUpdate: package %r removed mid-flight, skipping commit",
                                source.get("name"),
                            )
                        else:
                            # Replace dict to force QML re-eval of final state.
                            self.app._update_packages[target] = dict(source)
                            self._emit_packages_changed()
                        # Refresh the header/button: a promoted version clears
                        # this package from the outdated count immediately.
                        self.recalculateStats()
                        if not source.get("update_error"):
                            self.app._set_status(f"Update finished for {source.get('name')}")

                        pkg_path = (
                            source.get("resolved_package_path")
                            or source.get("package_path")
                            or source.get("local_path")
                            or ""
                        )
                        if pkg_path:
                            try:
                                watcher = getattr(self.app, "_watcher", None)
                                if watcher is not None:
                                    p = Path(pkg_path).expanduser().resolve()
                                    if p.is_dir():
                                        watcher.add_path(str(p))
                            except Exception as exc:
                                logger.debug("Failed registering watcher path: %s", exc)

                        removed = source.get("removed_folders", [])
                        removals_verified = source.get("removals_verified", False)
                        if removed and removals_verified:
                            self.app._library_model.removeSkillsByPath(removed)
                            self.app._quick_copy_model.removeSkillsByPath(removed)

                        updated = source.get("updated_folders", [])
                        if updated:
                            from skill_manager.core.discovery import DiscoveryService
                            from skill_manager.core.persistence import patch_cache_add

                            service = DiscoveryService(
                                sources=[pkg_path] if pkg_path else [],
                                projects=[],
                                archive_paths=self.app._archive_paths,
                                starred_paths=self.app._starred_paths,
                                project_aliases=self.app._project_aliases,
                            )
                            discovered = []
                            for folder in updated:
                                try:
                                    folder_path = (
                                        Path(pkg_path) / folder if pkg_path else Path(folder)
                                    )
                                    if folder_path.is_dir():
                                        skill_data = service.discover_single(
                                            folder_path, folder_path, is_package=True
                                        )
                                        if skill_data:
                                            discovered.append(skill_data)
                                except Exception:
                                    pass

                            if discovered:
                                patch_cache_add(discovered)
                                self._merge_discovered_skills(discovered)
                                for skill_dict in discovered:
                                    self.app.ops._refresh_selected_skill(
                                        skill_dict.get("local_path", "")
                                    )

                        self.config.set("skills", self.app._update_packages)
                        # Coalesced: adding several packages in a row (or an
                        # edit landing mid-install) must not stack full scans.
                        self._schedule_discovery_refresh()

                    _safe_single_shot(0, self.app, finalize_ui)

            try:
                self.app.task_runner.run(run)
            except Exception as e:
                capture_exception(e)
                target = self._resolve_package_index(index, package_id)
                if target is not None:
                    self.app._update_packages[target]["is_updating"] = False
                    self._emit_packages_changed()
                self.app._set_status(f"Failed to start update for {source.get('name')}: {e}")

    def _resolve_package_index(self, index: int, package_id: str | None) -> int | None:
        """Resolve the current list position of a package.

        Prefers ``package_id`` match (stable across add/remove/reorder),
        falls back to the entry-time ``index`` when the record has no id.
        Returns ``None`` when the package no longer exists.
        """
        packages = self.app._update_packages
        if package_id:
            for i, p in enumerate(packages):
                if isinstance(p, dict) and p.get("package_id") == package_id:
                    return i
            return None
        if 0 <= index < len(packages):
            return index
        return None

    @Slot(str)
    def retryPackageCheck(self, package_id: str):
        """Re-probe one package's remote and refresh its stored check result.

        Runs on the shared task runner: a probe is allowed to take
        ``DEFAULT_GIT_TIMEOUT`` seconds, and the UI must keep painting while
        it does.  The row shows the outcome via ``check_status`` /
        ``check_error``, so a remote that could not be reached stops looking
        like "up to date".
        """
        from skill_manager.core.skill_packages import (
            RemoteProbeCache,
            check_skill_package_versions,
        )

        target = self._resolve_package_index(-1, package_id)
        if target is None:
            return

        package = dict(self.app._update_packages[target])
        label = package.get("name") or package_id
        self.app._set_status(f"Checking {label} for updates...")

        def run():
            try:
                result = check_skill_package_versions(
                    package, force_refresh=True, remote_cache=RemoteProbeCache()
                )
            except Exception as exc:
                logger.error("Version re-check failed for %s: %s", package_id, exc)
                capture_exception(exc)
                result = dict(package)
                result["check_status"] = "failed"
                result["check_error"] = f"version check failed: {exc}"

            def finalize_ui():
                # Re-resolve: an add or remove while the probe ran shifts rows.
                current = self._resolve_package_index(-1, package_id)
                if current is None:
                    return
                self.app._update_packages[current].clear()
                self.app._update_packages[current].update(result)
                self.config.set("skills", self.app._update_packages)
                self.recalculateStats()
                self._emit_packages_changed()
                if result.get("check_status") == "failed":
                    reason = result.get("check_error") or "unknown error"
                    self.app._set_status(f"Could not check {label}: {reason}")
                else:
                    self.app._set_status(f"Checked {label}")

            _safe_single_shot(0, self.app, finalize_ui)

        try:
            self.app.task_runner.run(run)
        except Exception as e:
            capture_exception(e)
            self.app._set_status(f"Could not start version check for {label}: {e}")

    @Slot(str)
    def syncProject(self, path: str):
        """Synchronizes and updates all skills in a specific project."""
        if path not in self.app._projects:
            return

        self.app._set_status(f"Updating {self.app.getProjectLabel(path)}...")
        if path not in self.app._syncing_projects:
            self.app._syncing_projects.append(path)
            self._publish_project_sync_state()

        def run_sync():
            try:
                from skill_manager.core.discovery import DiscoveryService
                from skill_manager.core.parsing import (
                    build_skill_search_text,
                    categorize_skill,
                    parse_skill_md,
                )
                from skill_manager.core.persistence import patch_cache_add
                from skill_manager.core.quick_copy import discover_package_skills

                source_skills = discover_package_skills(
                    sources=self.app._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                )

                from skill_manager.core.copier import copy_skill_folders_to_projects

                result = copy_skill_folders_to_projects(source_skills, [path], update_only=True)

                discovered_skills = []
                if result["details"]:
                    service = DiscoveryService(
                        sources=list(self.app._sources),
                        projects=self.app._projects,
                        archive_paths=self.app._archive_paths,
                        starred_paths=self.app._starred_paths,
                        project_aliases=self.app._project_aliases,
                    )
                    for detail in result["details"]:
                        if detail["status"] in ("copied", "merged") and detail.get("message"):
                            skill_path = Path(detail["message"])
                            proj_path = Path(detail["project"])
                            try:
                                skill_data = service.discover_single(skill_path, proj_path)
                                if skill_data:
                                    discovered_skills.append(skill_data)
                            except Exception as exc:
                                logger.error("[SYNC SCAN] Failed scanning %s: %s", skill_path, exc)

                if discovered_skills:
                    patch_cache_add(discovered_skills)

                    def update_ui():
                        self._merge_discovered_skills(discovered_skills)
                        for skill_dict in discovered_skills:
                            self.app.ops._refresh_selected_skill(skill_dict.get("local_path", ""))

                    _safe_single_shot(0, self.app, update_ui)

                msg = f"Update complete for {self.app.getProjectLabel(path)}: {result['merged']} updated, {result['failed']} failed"
                _safe_single_shot(0, self.app, lambda: self.app._set_status(msg))
            except Exception as e:
                err_msg = f"Update failed for {path}: {e}"
                _safe_single_shot(0, self.app, lambda: self.app._set_status(err_msg))
            finally:
                if path in self.app._syncing_projects:
                    self.app._syncing_projects.remove(path)
                _safe_single_shot(0, self.app, self._publish_project_sync_state)

        try:
            self.app.task_runner.run(run_sync)
        except Exception as e:
            capture_exception(e)
            if path in self.app._syncing_projects:
                self.app._syncing_projects.remove(path)
            self._publish_project_sync_state()
            self.app._set_status(f"Failed to start sync for {path}: {e}")

    @Slot()
    def updateAllOutdated(self):
        """Updates all skills that are marked as outdated."""
        # This was missing in the restored version, let's add it.
        self.app._set_status("Updating all outdated skills...")
        # Placeholder for implementation if needed, or call updateNow
        self.updateNow()

    @Slot(int)
    def clearPackageJustFinished(self, index: int):
        if 0 <= index < len(self.app._update_packages):
            self.app._update_packages[index]["just_finished"] = False
            self._emit_packages_changed()
