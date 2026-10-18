"""QML accessibility audit for the MCP bridge.

The audit reads **Qt's accessible tree** — the objects Qt exposes to assistive
technology — instead of guessing from QML class names. That is what a screen
reader sees, so it is both accurate and low-noise: containers, layouts and
static text are simply not in it, and real controls report a role.

Qt assigns those roles itself (a QML ``Button`` is ``Button``, a ``TextField``
is ``EditableText``, a clickable ``MouseArea`` is ``Button``), so "this control
has no accessible name" is a real finding rather than a heuristic hit. Each
issue carries the node's path in the accessible tree and its window-relative
rect, so it can be located on a screenshot.

When a root exposes no accessible interface at all (unusual: non-QML roots or a
Qt build without the accessibility bridge) the audit degrades to a class-name
walk that still reports interactive-looking elements with no role.
"""

from __future__ import annotations

import re
from typing import Any

from ._controller import _controller_or_none
from ._qml_headless import ensure_qml_engine
from ._qml_object import (
    accessible_interface,
    interface_name,
    interface_rect,
    interface_role_name,
    qml_class_name,
)
from ._telemetry import _log_call

# Roles that must carry an accessible name: every one of them is a control a
# screen reader announces, so an empty name means it is announced as nothing.
_NAME_REQUIRED_ROLES = frozenset(
    {
        "Button",
        "CheckBox",
        "ComboBox",
        "EditableText",
        "Link",
        "MenuItem",
        "PageTab",
        "RadioButton",
        "Slider",
        "SpinBox",
        "Switch",
        "ToolButton",
    }
)

# ``Button`` gets its own issue type: it is the most common offender and
# ``unlabeled_button`` is this tool's established name for it.
_BUTTON_ROLE = "Button"

# --- class-name fallback (only for roots with no accessible interface) ------
# QML types report engine decorations: ``Button_QMLTYPE_42``, ``Foo_QML_109``.
_QML_DECORATION_RE = re.compile(r"_(?:qmltype|qml)_\d+$", re.IGNORECASE)
_CLASS_PREFIXES = ("qquick", "qml")
_BUTTON_SUFFIX = "button"
# ``dialogbuttonbox`` / ``buttonbox`` are containers that merely end in
# "button"-ish spellings, and flagging them was this audit's worst false
# positive (8 bogus issues on the real tree).
_CONTAINER_MARKERS = ("box",)
_INTERACTIVE_SUFFIXES = (
    "checkbox",
    "combobox",
    "dropdown",
    "radiobutton",
    "searchinput",
    "slider",
    "spinbox",
    "switch",
    "tabbutton",
    "textedit",
    "textfield",
    "textinput",
)


def _normalised_class_name(class_name: str) -> str:
    """Lower-case a QML type name with *all* engine decorations stripped.

    Decorations can stack — ``IconButton_QMLTYPE_16_QML_109`` is a component
    instantiated inside another QML-defined type — so this strips repeatedly.
    """
    name = (class_name or "").strip().lower()
    while True:
        stripped = _QML_DECORATION_RE.sub("", name)
        if stripped == name:
            break
        name = stripped
    for prefix in _CLASS_PREFIXES:
        if name.startswith(prefix) and len(name) > len(prefix):
            return name[len(prefix) :]
    return name


def _is_button_like(normalised: str) -> bool:
    """True for buttons, false for button *containers* (``dialogbuttonbox``)."""
    if not normalised.endswith(_BUTTON_SUFFIX):
        return False
    return not any(marker in normalised for marker in _CONTAINER_MARKERS)


def _is_interactive_like(normalised: str) -> bool:
    """True when a class name looks like an interactive control."""
    return _is_button_like(normalised) or normalised.endswith(_INTERACTIVE_SUFFIXES)


def _error(message: str) -> dict[str, Any]:
    """Build a degraded audit envelope."""
    return {
        "ok": False,
        "source": None,
        "element_count": 0,
        "accessible_nodes": 0,
        "issue_count": 0,
        "issue_counts_by_type": {},
        "issues": [],
        "error": message,
    }


def audit_accessibility(max_depth: int = 10) -> dict[str, Any]:
    """Audit the UI for accessibility issues.

    Walks Qt's accessible tree up to *max_depth* and reports:

    - ``unlabeled_button`` — a button with no accessible name (high);
    - ``missing_name`` — another interactive control with no accessible name
      (high);
    - ``missing_role`` — an interactive element exposing no accessible
      interface at all (medium; class-name fallback only).

    Returns a dict with ``ok``, ``source``, ``element_count``,
    ``accessible_nodes``, ``issue_count``, ``issue_counts_by_type``, ``issues``
    and ``error``. ``source`` is ``accessible-tree``, ``class-name-fallback`` or
    ``mixed``, so a caller can tell which traversal produced the result.
    """
    _log_call("audit_accessibility")

    try:
        max_depth = int(max_depth)
        if max_depth < 1 or max_depth > 30:
            return _error("max_depth must be between 1 and 30")
    except (TypeError, ValueError) as exc:
        return _error(f"invalid max_depth: {exc}")

    controller = _controller_or_none()
    if controller is None:
        return _error("AppController unavailable")

    qml_engine = ensure_qml_engine()
    if qml_engine is None:
        return _error("QML engine not available")

    roots = qml_engine.rootObjects()
    if not roots:
        return _error("no QML root objects")

    issues: list[dict[str, Any]] = []
    element_count = 0
    accessible_nodes = 0
    fallback_nodes = 0

    def _label(obj_name: str, class_name: str, role: str | None, fallback: str) -> str:
        return obj_name or class_name or role or fallback

    def _add_issue(
        *,
        obj_name: str,
        class_name: str,
        role: str | None,
        issue_type: str,
        severity: str,
        description: str,
        suggestion: str,
        path: str,
        rect: tuple[int, int, int, int] | None,
    ) -> None:
        issue: dict[str, Any] = {
            "object_name": obj_name,
            "class_name": class_name,
            "role": role,
            "issue_type": issue_type,
            "severity": severity,
            "path": path,
            "description": description,
            "suggestion": suggestion,
        }
        if rect is not None:
            issue["x"], issue["y"], issue["width"], issue["height"] = rect
        issues.append(issue)

    def _object_identity(obj: Any) -> tuple[str, str]:
        """Return ``(object_name, qml_class_name)`` for an accessible object."""
        obj_name = ""
        if obj is not None:
            try:
                obj_name = str(obj.objectName() or "")
            except Exception:  # noqa: BLE001
                obj_name = ""
        return obj_name, (qml_class_name(obj) if obj is not None else "")

    def _walk_accessible(iface: Any, depth: int, path: str) -> None:
        """Walk Qt's accessible tree, flagging controls with no accessible name."""
        nonlocal element_count, accessible_nodes
        if depth > max_depth:
            return
        element_count += 1
        accessible_nodes += 1

        try:
            obj = iface.object()
        except Exception:  # noqa: BLE001
            obj = None
        obj_name, class_name = _object_identity(obj)

        role = interface_role_name(iface)
        name = interface_name(iface)
        rect = interface_rect(iface)

        if not name and role in _NAME_REQUIRED_ROLES:
            label = _label(obj_name, class_name, role, "element")
            source = class_name or role
            if role == _BUTTON_ROLE:
                _add_issue(
                    obj_name=obj_name,
                    class_name=class_name,
                    role=role,
                    issue_type="unlabeled_button",
                    severity="high",
                    description=f"Button '{label}' ({source}) has no accessible name.",
                    suggestion=("Set Accessible.name on this button, or give it visible text."),
                    path=path,
                    rect=rect,
                )
            else:
                _add_issue(
                    obj_name=obj_name,
                    class_name=class_name,
                    role=role,
                    issue_type="missing_name",
                    severity="high",
                    description=(
                        f"Interactive element '{label}' ({source}) has no accessible name."
                    ),
                    suggestion="Set Accessible.name on this element.",
                    path=path,
                    rect=rect,
                )

        try:
            count = int(iface.childCount())
        except Exception:  # noqa: BLE001
            count = 0
        for index in range(count):
            try:
                child = iface.child(index)
            except Exception:  # noqa: BLE001
                child = None
            if child is not None:
                _walk_accessible(child, depth + 1, f"{path}.{index}")

    def _walk_objects(obj: Any, depth: int, path: str) -> None:
        """Class-name fallback: walk QObject children when no interface exists."""
        nonlocal element_count, fallback_nodes
        if depth > max_depth:
            return
        element_count += 1
        fallback_nodes += 1

        obj_name, class_name = _object_identity(obj)
        normalised = _normalised_class_name(class_name)

        iface = accessible_interface(obj)
        role = interface_role_name(iface)
        name = interface_name(iface)
        rect = interface_rect(iface)

        if _is_interactive_like(normalised):
            label = _label(obj_name, class_name, role, normalised)
            if not name:
                if _is_button_like(normalised):
                    _add_issue(
                        obj_name=obj_name,
                        class_name=class_name,
                        role=role,
                        issue_type="unlabeled_button",
                        severity="high",
                        description=(
                            f"Button '{label}' ({class_name or normalised}) has no accessible name."
                        ),
                        suggestion=("Set Accessible.name on this button, or give it visible text."),
                        path=path,
                        rect=rect,
                    )
                else:
                    _add_issue(
                        obj_name=obj_name,
                        class_name=class_name,
                        role=role,
                        issue_type="missing_name",
                        severity="high",
                        description=(
                            f"Interactive element '{label}' ({class_name or normalised}) "
                            "has no accessible name."
                        ),
                        suggestion="Set Accessible.name on this element.",
                        path=path,
                        rect=rect,
                    )
            if role is None:
                _add_issue(
                    obj_name=obj_name,
                    class_name=class_name,
                    role=role,
                    issue_type="missing_role",
                    severity="medium",
                    description=(
                        f"Interactive element '{label}' ({class_name or normalised}) "
                        "exposes no accessible role."
                    ),
                    suggestion="Set Accessible.role on this element.",
                    path=path,
                    rect=rect,
                )

        try:
            children = obj.children()
        except Exception:  # noqa: BLE001
            children = []
        if not isinstance(children, (list, tuple)):
            children = []
        for index, child in enumerate(children):
            _walk_objects(child, depth + 1, f"{path}.{index}")

    for index, root in enumerate(roots):
        iface = accessible_interface(root)
        if iface is None:
            _walk_objects(root, 1, str(index))
        else:
            _walk_accessible(iface, 1, str(index))

    counts: dict[str, int] = {}
    for issue in issues:
        key = str(issue["issue_type"])
        counts[key] = counts.get(key, 0) + 1

    if accessible_nodes and fallback_nodes:
        source = "mixed"
    elif fallback_nodes:
        source = "class-name-fallback"
    else:
        source = "accessible-tree"

    return {
        "ok": True,
        "source": source,
        "element_count": element_count,
        "accessible_nodes": accessible_nodes,
        "issue_count": len(issues),
        "issue_counts_by_type": counts,
        "issues": issues,
        "error": None,
    }


__all__ = ["audit_accessibility"]
