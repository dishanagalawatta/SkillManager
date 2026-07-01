"""
Purpose: Manages background discovery of skills and cache synchronization.
Usage: Accessed via AppController.discovery

All heavy computation (Skill construction, FilterEngine pass, SearchEngine
build, row preparation, visibility calculation) happens in the background
thread.  The main thread only performs a single ``replacePreparedState``
call per refresh, keeping the UI fluid.
"""

import logging
import os
import threading
import time
import traceback
from typing import Any

from PySide6.QtCore import Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.diagnostics import (
    CATEGORY_CACHE_PRESERVED,
    CATEGORY_DISCOVERY_EMPTY_RESULT,
    CATEGORY_REFRESH_BACKGROUND_START,
    CATEGORY_REFRESH_CANCELLED,
    CATEGORY_REFRESH_COMMITTED,
    get_diagnostic_logger,
)
from skill_manager.core.discovery import DiscoveryService
from skill_manager.core.models.entities import PreparedModelState, Skill
from skill_manager.core.models.filter_engine import FilterEngine
from skill_manager.core.schemas import CacheState
from skill_manager.core.search import SearchEngine

logger = logging.getLogger(__name__)


class DiscoveryController(BaseController):
    """Controller for background skill discovery and cache handling.

    All discovery work runs in a background thread.  Heavy computation
    (Skill construction, FilterEngine, SearchEngine, row preparation) is
    also done in the background so the main thread only performs a single
    ``modelReset`` when the result is committed.
    """

    _discoveryPrepared = Signal(object)  # PreparedModelState
    _discoveryError = Signal(str)
    skillsDeleted = Signal(list)

    def __init__(self, app):
        super().__init__(app)
        self._discoveryPrepared.connect(self._commit_prepared_state)
        self._discoveryError.connect(self._handle_loading_error)
        self._previous_skills: dict[str, Any] = {}  # path -> Skill or SkillRecord
        self.skillsDeleted.connect(self._on_skills_deleted)
        self._refresh_generation: int = 0
        self._refresh_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @Slot()
    def loadInitialData(
        self, force_full_scan: bool = False, silent: bool = True, skip_discovery: bool = False
    ):
        """Kick off a background discovery pipeline.

        Parameters
        ----------
        force_full_scan:
            When True, ignore cached fingerprints and re-scan every directory.
        silent:
            When True (the default), do **not** set ``is_loading`` or show
            a status message.  The UI stays completely fluid while the
            background thread works.
        skip_discovery:
            When True, load the existing cache without running a new
            discovery scan.  Used by the peer-heartbeat optimization:
            if a sibling instance recently wrote the cache, skip the
            expensive scan and load from disk directly.
        """
        with self._refresh_lock:
            self._refresh_generation += 1
            gen = self._refresh_generation

        diag = get_diagnostic_logger()
        diag.log_event(
            "INFO",
            CATEGORY_REFRESH_BACKGROUND_START,
            f"Discovery started (gen={gen}, force_full_scan={force_full_scan})",
            data={"generation": gen, "force_full_scan": force_full_scan},
        )

        if not silent:
            self.app._is_loading = True
            self.app.isLoadingChanged.emit()
            self.app._set_status("Scanning skills...")

        if skip_discovery:
            # Peer heartbeat: load from cache directly without scanning
            if hasattr(self.app, "task_runner"):
                self.app.task_runner.run(self._run_pipeline_from_cache, args=(gen,))
            else:
                threading.Thread(
                    target=self._run_pipeline_from_cache, args=(gen,), daemon=True
                ).start()
        elif hasattr(self.app, "task_runner"):
            self.app.task_runner.run(self._run_pipeline, args=(gen, force_full_scan))
        else:
            threading.Thread(
                target=self._run_pipeline, args=(gen, force_full_scan), daemon=True
            ).start()

    def cancel_inflight(self) -> bool:
        """Bump the generation counter to discard any in-flight result.

        Returns True if a pipeline was actually cancelled.
        """
        with self._refresh_lock:
            self._refresh_generation += 1
        return True

    # ------------------------------------------------------------------
    # Background pipeline (runs in a worker thread)
    # ------------------------------------------------------------------

    def _run_pipeline(self, generation: int, force_full_scan: bool) -> None:
        """Full background pipeline: discover → prepare → commit."""
        t0 = time.monotonic()

        # ---- Phase 1: build discovery sources ----
        discovery_sources = list(self.app._sources)
        for src in self.app._update_packages:
            pkg_path = src.get("package_path") or src.get("local_path")
            if pkg_path and os.path.exists(pkg_path) and pkg_path not in discovery_sources:
                discovery_sources.append(pkg_path)

        service = DiscoveryService(
            sources=discovery_sources,
            projects=self.app._projects,
            archive_paths=self.app._archive_paths,
            starred_paths=self.app._starred_paths,
            project_aliases=self.app._project_aliases,
        )

        try:
            # ---- Phase 2: discover (with incremental fingerprint cache) ----
            cache_state_dict = self._discover_all_background(service, force_full_scan)

            if self._is_cancelled(generation):
                self._log_cancelled(generation)
                return

            if isinstance(cache_state_dict, dict) and "error" in cache_state_dict:
                self._discoveryError.emit(f"Error scanning skills: {cache_state_dict['error']}")
                return

            # ---- Phase 3: build prepared states (still in background) ----
            prepared_states = self._build_prepared_states(cache_state_dict, generation)

            if self._is_cancelled(generation):
                self._log_cancelled(generation)
                return

            if prepared_states is None:
                return  # safety net triggered, nothing to commit

            # ---- Phase 4: hand to main thread ----
            # Queue commit — ``_commit_prepared_state`` runs on the main thread.
            self._discoveryPrepared.emit(prepared_states)

            elapsed = time.monotonic() - t0
            diag = get_diagnostic_logger()
            diag.log_event(
                "INFO",
                CATEGORY_REFRESH_COMMITTED,
                f"Prepared state committed (gen={generation}, "
                f"skills={len(prepared_states['library'].all_skills)}, elapsed={elapsed:.2f}s)",
                data={
                    "generation": generation,
                    "skill_count": len(prepared_states["library"].all_skills),
                    "elapsed_seconds": round(elapsed, 3),
                },
            )
            logger.info(
                "[DISCOVERY] Background pipeline complete: gen=%d, %d skills, %.2fs",
                generation,
                len(prepared_states["library"].all_skills),
                elapsed,
            )

        except Exception as exc:
            if self._is_cancelled(generation):
                return
            traceback.print_exc()
            self._discoveryError.emit(f"Discovery failed: {exc}")

    def _run_pipeline_from_cache(self, generation: int) -> None:
        """Load from cache directly without running a discovery scan.

        Used by the peer-heartbeat optimization: if a sibling instance
        recently wrote the cache, skip the expensive filesystem scan and
        load from disk directly.
        """
        from skill_manager.core.persistence import load_cache

        t0 = time.monotonic()

        try:
            cached = load_cache()
            if cached is None:
                logger.info("[HEARTBEAT] Cache miss — falling back to full discovery")
                self._run_pipeline(generation, force_full_scan=False)
                return

            cache_state = CacheState.model_validate(cached)

            prepared_states = self._build_prepared_states(cache_state, generation)

            if self._is_cancelled(generation):
                self._log_cancelled(generation)
                return

            if prepared_states is None:
                return

            self._discoveryPrepared.emit(prepared_states)

            elapsed = time.monotonic() - t0
            logger.info(
                "[HEARTBEAT] Cache load complete: gen=%d, %d skills, %.2fs",
                generation,
                len(prepared_states["library"].all_skills),
                elapsed,
            )

        except Exception as exc:
            if self._is_cancelled(generation):
                return
            logger.warning("[HEARTBEAT] Cache load failed, falling back to discovery: %s", exc)
            self._run_pipeline(generation, force_full_scan=False)

    def _discover_all_background(
        self,
        service: DiscoveryService,
        force_full_scan: bool,
    ) -> dict[str, Any] | CacheState:
        """Run ``service.discover_all`` without the cache_callback path.

        The original code dispatched cache_callback results to the main thread
        mid-scan; we skip that entirely.  The full result is returned once
        and the entire prepare + commit path runs after that.
        """
        # discover_all returns a dict (CacheState.model_dump()). We call it
        # with cache_callback=None to suppress the mid-flight callback.
        return service.discover_all(
            cache_callback=None,
            force_full_scan=force_full_scan,
        )

    # ------------------------------------------------------------------
    # Prepare everything in the background thread
    # ------------------------------------------------------------------

    def _build_prepared_states(
        self, result: dict[str, Any] | CacheState, generation: int
    ) -> dict[str, PreparedModelState] | None:
        """Construct a dict of PreparedModelStates in the calling (background) thread.

        All heavy work happens here: Skill construction, FilterEngine pass,
        SearchEngine build, row preparation, visibility calculation.
        Builds separate states for the library and quick copy models.
        """
        if self._is_cancelled(generation):
            return None

        # ---- Validate cache state ----
        if isinstance(result, dict):
            if "error" in result:
                return None
            try:
                cache_state = CacheState.model_validate(result)
            except Exception as ve:
                logger.error("[CACHE] Validation failed: %s", ve)
                return None
        else:
            cache_state = result

        # ---- Safety net: zero results but we had skills before ----
        new_skills_map = {s.local_path: s for s in cache_state.skills if s.local_path}
        if not new_skills_map and self._previous_skills:
            diag = get_diagnostic_logger()
            diag.log_event(
                "WARNING",
                CATEGORY_DISCOVERY_EMPTY_RESULT,
                "Discovery returned 0 skills but cache had skills — "
                "source directories may be missing. Preserving cached skills.",
                data={
                    "previous_skill_count": len(self._previous_skills),
                },
            )
            diag.log_event(
                "INFO",
                CATEGORY_CACHE_PRESERVED,
                f"Preserved {len(self._previous_skills)} cached skills "
                f"(discovery safety net triggered)",
            )
            logger.warning(
                "[DISCOVERY] Safety net: preserving %d cached skills",
                len(self._previous_skills),
            )
            # Return None — _commit_prepared_state will leave existing skills alone
            return None

        # ---- Convert CacheState SkillRecords to Skill entities ----
        all_skills: list[Skill] = [Skill.from_dict_fast(s.model_dump()) for s in cache_state.skills]

        if self._is_cancelled(generation):
            return None

        # ---- Build FilterEngine + filter for Library ----
        engine = FilterEngine()
        library_state_obj = self._build_filter_state_for_background(self.app._library_model)
        library_filtered = engine.filter_skills(all_skills, library_state_obj)
        library_filtered.sort(key=engine.sort_key)

        if self._is_cancelled(generation):
            return None

        # ---- Prepare rows (enrichment: section_name, is_first, etc.) ----
        library_all_filtered = engine.prepare_rows(library_filtered)

        if self._is_cancelled(generation):
            return None

        # ---- Build visible rows (collapse/expand logic) ----
        library_visible = engine.build_visible_rows(
            library_all_filtered, library_state_obj.collapsed_categories
        )

        if self._is_cancelled(generation):
            return None

        # ---- Build FilterEngine + filter for Quick Copy ----
        quick_copy_state_obj = self._build_filter_state_for_background(self.app._quick_copy_model)
        quick_copy_filtered = engine.filter_skills(all_skills, quick_copy_state_obj)
        quick_copy_filtered.sort(key=engine.sort_key)

        if self._is_cancelled(generation):
            return None

        quick_copy_all_filtered = engine.prepare_rows(quick_copy_filtered)

        if self._is_cancelled(generation):
            return None

        quick_copy_visible = engine.build_visible_rows(
            quick_copy_all_filtered, quick_copy_state_obj.collapsed_categories
        )

        if self._is_cancelled(generation):
            return None

        # ---- Build SearchEngine ----
        skills_for_index = [
            {
                "local_path": s.local_path,
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "metadata": {"tags": s.tags},
            }
            for s in all_skills
        ]
        search_engine = SearchEngine(skills_for_index)

        # ---- Categories ----
        categories = sorted({s.category for s in all_skills if s.category})

        status = cache_state.status or f"Found {len(all_skills)} skills"

        return {
            "library": PreparedModelState(
                all_skills=all_skills,
                search_engine=search_engine,
                all_filtered_skills=library_all_filtered,
                visible_rows=library_visible,
                categories=categories,
                status=status,
                generation=generation,
            ),
            "quick_copy": PreparedModelState(
                all_skills=all_skills,
                search_engine=search_engine,
                all_filtered_skills=quick_copy_all_filtered,
                visible_rows=quick_copy_visible,
                categories=categories,
                status=status,
                generation=generation,
            ),
        }

    def _build_filter_state_for_background(self, model) -> Any:
        """Construct a FilterState snapshot from the current app filter values.

        Reads from ``self.app`` which is safe because the caller only reads
        atomic values (strings, bools, sets) that are not mutated during
        the background scan.
        """
        from skill_manager.core.models.entities import FilterState

        return FilterState(
            filter_text=getattr(model.state, "filter_text", ""),
            show_archived=getattr(model.state, "show_archived", False),
            category_filter=getattr(model.state, "category_filter", ""),
            collection_filter=getattr(model.state, "collection_filter", False),
            project_filter=getattr(model.state, "project_filter", ""),
            client_filter=getattr(model.state, "client_filter", ""),
            filter_by_client=getattr(model.state, "filter_by_client", False),
            show_commands=getattr(model.state, "show_commands", True),
            show_starred=getattr(model.state, "show_starred", True),
            is_package_only=getattr(model.state, "is_package_only", None),
            collapsed_categories=set(getattr(model.state, "collapsed_categories", set())),
        )

    # ------------------------------------------------------------------
    # Main-thread commit
    # ------------------------------------------------------------------

    @Slot(object)
    def _commit_prepared_state(
        self, prepared_states: dict[str, PreparedModelState] | PreparedModelState
    ) -> None:
        """Commit fully pre-computed model states on the main thread.

        This is the only code that touches the Qt models.  All heavy
        work is already done — we just swap the internal lists in a
        single ``beginResetModel``/``endResetModel`` pair.
        """
        if isinstance(prepared_states, PreparedModelState):
            prepared_states = {"library": prepared_states, "quick_copy": prepared_states}

        diag = get_diagnostic_logger()

        library_prepared = prepared_states["library"]
        quick_copy_prepared = prepared_states["quick_copy"]

        # ---- Update categories if changed ----
        if self.app._categories != library_prepared.categories:
            self.app._categories = library_prepared.categories
            self.app.categoriesChanged.emit()

        # ---- Build a lookup for snapshot ----
        new_skills_map = {s.local_path: s for s in library_prepared.all_skills if s.local_path}

        # ---- Safety net: preserve previous skills on final discovery returning 0 ----
        # If this is a full (final) load and the new result is empty but we had
        # skills before, skip the update entirely to avoid wiping the cache.
        if (
            library_prepared.is_final
            and len(library_prepared.all_skills) == 0
            and self._previous_skills
        ):
            self.app._library_model.incubating = False
            self.app._quick_copy_model.incubating = False
            diag.log_event(
                "INFO",
                CATEGORY_CACHE_PRESERVED,
                "Safety net: preserving previous skills (final discovery returned 0)",
                data={"previous_count": len(self._previous_skills)},
            )
            return

        # ---- Apply prepared state to both models ----
        # Set incubating based on whether the new prepared state has skills.
        # This protects both initial startup populations and subsequent refreshes from
        # race conditions caused by subsequent synchronous filter operations.
        lib_incubating = bool(library_prepared.all_skills)
        qc_incubating = bool(quick_copy_prepared.all_skills)
        if lib_incubating:
            self.app._library_model.incubating = True
        if qc_incubating:
            self.app._quick_copy_model.incubating = True

        # Check cancellation one last time before committing
        if self._is_cancelled(library_prepared.generation):
            if lib_incubating:
                self.app._library_model.incubating = False
            if qc_incubating:
                self.app._quick_copy_model.incubating = False
            diag.log_event(
                "INFO",
                CATEGORY_REFRESH_CANCELLED,
                "Prepared state superseded — not committed",
                data={"generation": library_prepared.generation},
            )
            return

        self.app._library_model.replacePreparedState(library_prepared)
        self.app._quick_copy_model.replacePreparedState(quick_copy_prepared)

        # ---- Update client/project filters ----
        # These trigger _apply_filter which, while incubating, queues
        # the filter work onto _pending_signals.  The queue is drained
        # by QML's onIncubationReady() or the 5s safety timer, so both
        # the prepared state and the filter results are applied in one
        # coordinated batch.
        self.app._library_model.clientFilter = self.app._client_format
        self.app._quick_copy_model.clientFilter = self.app._client_format
        if self.app._current_project_label:
            self.app._quick_copy_model.projectFilter = self.app._current_project_label

        # Do NOT set incubating = False here.  The flag must remain True
        # until QML calls onIncubationReady() (or the 5s safety timer
        # fires).  Setting it to False would start replaying deferred
        # signals before QML has finished creating delegates, which is
        # exactly the race condition we're fixing.

        # ---- Snapshot current state for next diff ----
        self._previous_skills = new_skills_map

        self.app._set_status(library_prepared.status)

        diag.log_event(
            "INFO",
            CATEGORY_REFRESH_COMMITTED,
            f"Model commit complete: {len(library_prepared.all_skills)} skills, "
            f"{len(library_prepared.visible_rows)} visible rows",
            data={
                "generation": library_prepared.generation,
                "skill_count": len(library_prepared.all_skills),
                "visible_count": len(library_prepared.visible_rows),
            },
        )

    # ------------------------------------------------------------------
    # Error / deletion handlers
    # ------------------------------------------------------------------

    def _handle_loading_error(self, error_msg: str) -> None:
        """Handles discovery errors on the main thread."""
        self.app._set_status(error_msg)
        self.app._is_loading = False
        self.app.isLoadingChanged.emit()

    @Slot(list)
    def _on_skills_deleted(self, removed_paths: list[str]) -> None:
        """Apply targeted removal after deletion — O(1), no full scan."""
        path_set = set(removed_paths)
        self.app._library_model.removeSkillsByPath(list(path_set))
        self.app._quick_copy_model.removeSkillsByPath(list(path_set))
        self._previous_skills = {
            p: r for p, r in self._previous_skills.items() if p not in path_set
        }
        logger.info("[DELETE] applied targeted removal of %d paths", len(path_set))

    # ------------------------------------------------------------------
    # Cancellation helpers
    # ------------------------------------------------------------------

    def _is_cancelled(self, generation: int) -> bool:
        """Check if this generation has been superseded by a newer request."""
        with self._refresh_lock:
            return generation != self._refresh_generation

    def _log_cancelled(self, generation: int) -> None:
        diag = get_diagnostic_logger()
        diag.log_event(
            "INFO",
            CATEGORY_REFRESH_CANCELLED,
            f"Discovery pipeline cancelled (gen={generation})",
            data={"generation": generation},
        )
        logger.info("[DISCOVERY] Pipeline cancelled: gen=%d", generation)
