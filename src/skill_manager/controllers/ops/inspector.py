"""CommandInspector support: referenced-skill lookups and text highlighting."""

import contextlib
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Slot

from skill_manager.core.diagnostics import (
    CATEGORY_COMMAND_REFERENCED_SKILLS_RENDERED,
    get_diagnostic_logger,
)
from skill_manager.core.skill_references import REF_PATTERN

logger = logging.getLogger(__name__)


def _iter_reference_matches(body: str) -> Iterator[tuple[Any, str]]:
    """Yield ``(match, raw_name)`` for every skill reference token in *body*.

    Shared by :meth:`InspectorMixin.getReferencedSkillsForCommand` and
    :meth:`InspectorMixin.getSkillReferenceRanges` so the token-extraction
    rules (``[$name](...)``, ``/folder``, ``@owner/name``) live in one place.
    """
    for m in REF_PATTERN.finditer(body):
        token = m.group(0)
        raw = ""
        if token.startswith("[$"):
            raw = m.group(1)
        elif token.startswith("/"):
            raw = token[1:]
        elif token.startswith("@"):
            parts = token.split("/")
            raw = parts[-2] if token.endswith("/SKILL.md") and len(parts) >= 2 else parts[-1]
            raw = raw.lstrip("@")

        if not raw:
            continue
        yield m, raw


class InspectorMixin:
    """Referenced-skill resolution and body highlighting for CommandInspector."""

    @Slot(str, result=list)
    def getReferencedSkillsForCommand(self, command_path: str) -> list:
        """Return the skills referenced by the command at *command_path*.

        Each item is a dict::

            {"name": str, "folder_name": str, "category": str,
             "local_path": str, "occurrences": int}

        ``occurrences`` counts every distinct reference in the command
        body (not just the de-duplicated skill resolution).  Items are
        ordered by first appearance in the body.
        """
        if not command_path or not Path(command_path).is_file():
            return []

        from skill_manager.core.commands import find_referenced_skills_in_command
        from skill_manager.core.parsing.base import split_frontmatter

        diag = get_diagnostic_logger()

        try:
            content = Path(command_path).read_text(encoding="utf-8-sig")
        except OSError:
            return []

        _, body = split_frontmatter(content)

        # 1. Resolve unique skills (name → skill dict).
        all_skills = self.app._library_model._all_skills  # type: ignore[attr-defined]
        resolved = find_referenced_skills_in_command(command_path, all_skills)
        by_folder = {s.get("folder_name", "").lower(): s for s in resolved if s.get("folder_name")}
        by_name = {s.get("name", "").lower(): s for s in resolved if s.get("name")}

        # 2. Count raw occurrences per skill name (source order).
        seen_names: list[str] = []
        counts: dict[str, int] = {}
        for _, raw in _iter_reference_matches(str(body)):
            key = raw.lower()
            if key in counts:
                counts[key] += 1
            else:
                seen_names.append(raw)
                counts[key] = 1

        # 3. Build ordered result list.
        result: list[dict[str, Any]] = []
        for raw_name in seen_names:
            key = raw_name.lower()
            skill = by_folder.get(key) or by_name.get(key)
            if not skill:
                continue
            result.append(
                {
                    "name": skill.get("name", raw_name),
                    "folder_name": skill.get("folder_name", ""),
                    "category": skill.get("category", ""),
                    "local_path": skill.get("local_path", ""),
                    "occurrences": counts.get(key, 1),
                }
            )

        diag.log_event(
            "INFO",
            CATEGORY_COMMAND_REFERENCED_SKILLS_RENDERED,
            f"command={command_path} skills={len(result)}",
        )

        return result

    @Slot(str, result=list)
    def getSkillReferenceRanges(self, command_path: str) -> list:
        """Return the character offsets for each skill reference in *command_path*.

        Each item is a dict::

            {"name": str, "start": int, "end": int}

        Offsets are relative to the body content (excluding YAML
        frontmatter), so they can be used directly with
        ``TextArea.cursorPosition`` and ``positionToRectangle``.
        """
        if not command_path or not Path(command_path).is_file():
            return []

        from skill_manager.core.commands import find_referenced_skills_in_command
        from skill_manager.core.parsing.base import split_frontmatter

        try:
            content = Path(command_path).read_text(encoding="utf-8-sig")
        except OSError:
            return []

        all_skills = self.app._library_model._all_skills  # type: ignore[attr-defined]
        resolved = find_referenced_skills_in_command(command_path, all_skills)
        by_folder = {
            s.get("folder_name", "").lower(): s.get("name", "").lower()
            for s in resolved
            if s.get("folder_name")
        }
        by_name = {
            s.get("name", "").lower(): s.get("name", "").lower() for s in resolved if s.get("name")
        }

        _, body = split_frontmatter(content)

        ranges: list[dict[str, Any]] = []
        for m, raw in _iter_reference_matches(body):
            key = raw.lower()
            display_name = by_folder.get(key) or by_name.get(key)
            if display_name is None:
                continue

            ranges.append({"name": display_name, "start": m.start(), "end": m.end()})

        return ranges

    @Slot(QObject, str, int)
    @Slot(str, str, int)
    def applySkillHighlights(
        self, target: QObject | str, ranges_json: str, focused_index: int = -1
    ) -> None:
        """Apply QSyntaxHighlighter-based highlights to a QML TextArea.

        Parameters
        ----------
        target : QObject or str
            The target TextArea object or its objectName string.
        ranges_json : str
            JSON-encoded list of ``{"name", "start", "end"}`` dicts.
        focused_index : int
            Index to highlight with stronger focus.  ``-1`` = no focus.
        """
        if not target or not ranges_json:
            return

        try:
            ranges = json.loads(ranges_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("applySkillHighlights: invalid ranges_json")
            return

        if not isinstance(ranges, list):
            return

        text_edit = self._find_qml_text_edit(target) if isinstance(target, str) else target

        if text_edit is None:
            return

        quick_doc = None
        if hasattr(text_edit, "property"):
            with contextlib.suppress(RuntimeError):
                quick_doc = text_edit.property("textDocument")
        if quick_doc is None and hasattr(text_edit, "textDocument"):
            with contextlib.suppress(RuntimeError):
                quick_doc = getattr(text_edit, "textDocument", lambda: None)()

        if quick_doc is None:
            logger.warning("applySkillHighlights: textDocument() returned None")
            return

        # PySide6 wraps the underlying QTextDocument in a QQuickTextDocument
        try:
            doc = quick_doc.textDocument() if hasattr(quick_doc, "textDocument") else quick_doc
        except RuntimeError:
            logger.warning("applySkillHighlights: extracted textDocument is deleted")
            return

        if doc is None:
            logger.warning("applySkillHighlights: extracted textDocument is None")
            return

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        # Reuse existing highlighter if attached to this document
        highlighter = getattr(doc, "_skill_ref_highlighter", None)
        if highlighter is None:
            highlighter = SkillRefHighlighter(doc)
            doc._skill_ref_highlighter = highlighter  # type: ignore[attr-defined]

        highlighter.set_ranges(ranges, focused_index=focused_index)

    @Slot(QObject)
    @Slot(str)
    def clearSkillHighlights(self, target: QObject | str) -> None:
        """Remove all highlights from the TextArea."""
        if not target:
            return

        text_edit = self._find_qml_text_edit(target) if isinstance(target, str) else target

        if text_edit is None:
            return

        quick_doc = None
        if hasattr(text_edit, "property"):
            with contextlib.suppress(RuntimeError):
                quick_doc = text_edit.property("textDocument")
        if quick_doc is None and hasattr(text_edit, "textDocument"):
            with contextlib.suppress(RuntimeError):
                quick_doc = getattr(text_edit, "textDocument", lambda: None)()

        if quick_doc is None:
            return

        # PySide6 wraps the underlying QTextDocument in a QQuickTextDocument
        try:
            doc = quick_doc.textDocument() if hasattr(quick_doc, "textDocument") else quick_doc
        except RuntimeError:
            return

        if doc is None:
            return

        highlighter = getattr(doc, "_skill_ref_highlighter", None)
        if highlighter is not None:
            highlighter.clear()

    def _find_qml_text_edit(self, object_name: str):
        """Locate a QQuickTextEdit by objectName in the active QML window.

        Returns the object only if it has a textDocument property (i.e. is a
        QQuickTextEdit, not just any QQuickItem).
        """
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQuick import QQuickItem, QQuickWindow

        results = []
        seen = set()

        def dfs(obj, name):
            if obj is None:
                return

            obj_id = id(obj)
            if obj_id in seen:
                return
            seen.add(obj_id)

            # Safely check if C++ object is still alive
            try:
                obj_name = obj.objectName() if hasattr(obj, "objectName") else ""
            except RuntimeError:
                return

            if obj_name == name:
                has_doc = False
                with contextlib.suppress(RuntimeError):
                    has_doc = hasattr(obj, "textDocument") or (
                        hasattr(obj, "property") and obj.property("textDocument") is not None
                    )
                if has_doc:
                    results.append(obj)

            # 1. Search visual children (childItems)
            if isinstance(obj, QQuickItem):
                try:
                    children = obj.childItems()
                except RuntimeError:
                    children = []
                for child in children:
                    dfs(child, name)

            # 2. Search QObject children
            if hasattr(obj, "children"):
                try:
                    children = obj.children()
                except RuntimeError:
                    children = []
                for child in children:
                    dfs(child, name)

        for window in QGuiApplication.allWindows():
            try:
                is_qquick = isinstance(window, QQuickWindow)
            except RuntimeError:
                continue

            if not is_qquick:
                continue

            # Search QQuickWindow contentItem visual tree first
            try:
                root_item = window.contentItem()
            except RuntimeError:
                root_item = None

            if root_item is not None:
                dfs(root_item, object_name)

            # Fallback/supplement with standard QObject tree search
            dfs(window, object_name)

        if not results:
            logger.debug("_find_qml_text_edit: '%s' not found in any window", object_name)
            return None

        # Prioritize visible QQuickItem matching the name
        visible_results = []
        for r in results:
            try:
                is_quick = isinstance(r, QQuickItem)
                is_visible = False
                if is_quick:
                    is_visible = r.isVisible()
                elif hasattr(r, "property"):
                    is_visible = r.property("visible") is True
            except RuntimeError:
                continue

            if is_visible:
                visible_results.append(r)

        if visible_results:
            return visible_results[0]

        # Fallback to the first match if none are currently visible
        return results[0]
