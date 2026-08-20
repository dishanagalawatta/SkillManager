"""Shared helpers for the ``ops`` controller mixins.

``QTimer`` lives here (rather than in each mixin) so that tests can
patch a single ``ops._helpers.QTimer.singleShot`` target and intercept
every mixin module at once.
"""

from typing import Any

from PySide6.QtCore import QTimer

__all__ = ["QTimer", "_build_discovery_service", "_get_item_attr"]


def _get_item_attr(item: Any, attr: str, default: Any = "") -> Any:
    """Safely retrieves an attribute from dataclasses, dicts, or objects."""
    if hasattr(item, attr):
        return getattr(item, attr)
    if isinstance(item, dict):
        return item.get(attr, default)
    return default


def _build_discovery_service(app: Any):
    """Build a :class:`DiscoveryService` configured from the app's current state.

    The construction matches DiscoveryController._run_pipeline; centralising
    it keeps the sources/projects/archive/starred/aliases wiring in one place.
    """
    import os

    from skill_manager.core.discovery import DiscoveryService

    discovery_sources = list(getattr(app, "_sources", []) or [])
    for src in getattr(app, "_update_packages", []) or []:
        pkg_path = (
            src.get("resolved_package_path") or src.get("package_path") or src.get("local_path")
        )
        if pkg_path and os.path.exists(pkg_path) and pkg_path not in discovery_sources:
            discovery_sources.append(pkg_path)

    return DiscoveryService(
        sources=discovery_sources,
        projects=getattr(app, "_projects", []) or [],
        archive_paths=getattr(app, "_archive_paths", []) or [],
        starred_paths=getattr(app, "_starred_paths", []) or [],
        project_aliases=getattr(app, "_project_aliases", {}) or {},
    )
