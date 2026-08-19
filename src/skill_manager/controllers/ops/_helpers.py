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

    The 5-argument construction is identical at every call site; centralising
    it keeps the sources/projects/archive/starred/aliases wiring in one place.
    """
    from skill_manager.core.discovery import DiscoveryService

    return DiscoveryService(
        sources=list(app._sources),
        projects=app._projects,
        archive_paths=app._archive_paths,
        starred_paths=app._starred_paths,
        project_aliases=app._project_aliases,
    )
