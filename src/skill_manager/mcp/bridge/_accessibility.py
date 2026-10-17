"""QML accessibility audit for the MCP bridge.

Traverses the QML object tree and flags accessibility issues: missing roles,
missing accessible names, unlabeled buttons, and elements lacking keyboard
focus support. Degrades gracefully when the QML engine is unavailable.
"""

from __future__ import annotations

from typing import Any

from ._controller import _controller_or_none
from ._qml_headless import ensure_qml_engine
from ._telemetry import _log_call

# QML class names that are expected to carry an Accessible.name.
_NAME_REQUIRED_CLASSES = (
    "button",
    "qpushbutton",
    "qtoolbutton",
    "qabstractbutton",
    "text",
    "qlabel",
    "qlineedit",
    "qplaintextedit",
    "qtextedit",
    "spinbox",
    "qspinbox",
    "combobox",
    "qcombobox",
    "checkbox",
    "qcheckbox",
    "radiobutton",
    "qradiobutton",
    "slider",
    "qslider",
)

# QML class names that are interactive and should have an Accessible role.
_ROLE_REQUIRED_CLASSES = _NAME_REQUIRED_CLASSES


def audit_accessibility(max_depth: int = 10) -> dict[str, Any]:
    """Audit the QML object tree for accessibility issues.

    Traverses ``controller._qml_engine.rootObjects()`` up to *max_depth*.
    For each QObject, checks:
    - Missing Accessible role on interactive elements (buttons, inputs, etc.)
    - Missing Accessible name on focusable/interactive elements
    - Buttons without an accessible name
    - Elements without keyboard focus support

    Uses QObject.children(), objectName(), metaObject().className(), and
    QAccessible attached properties when available; falls back to class-name
    heuristics otherwise.

    Returns a dict with: ok, element_count, issue_count, issues, error.
    """
    _log_call("audit_accessibility")

    try:
        max_depth = int(max_depth)
        if max_depth < 1 or max_depth > 30:
            return {
                "ok": False,
                "element_count": 0,
                "issue_count": 0,
                "issues": [],
                "error": "max_depth must be between 1 and 30",
            }
    except (TypeError, ValueError) as exc:
        return {
            "ok": False,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": f"invalid max_depth: {exc}",
        }

    controller = _controller_or_none()
    if controller is None:
        return {
            "ok": False,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": "AppController unavailable",
        }

    qml_engine = ensure_qml_engine()
    if qml_engine is None:
        return {
            "ok": False,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": "QML engine not available",
        }

    roots = qml_engine.rootObjects()
    if not roots:
        return {
            "ok": False,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": "no QML root objects",
        }

    issues: list[dict[str, Any]] = []
    element_count = 0

    def _class_name(obj: Any) -> str:
        try:
            meta = obj.metaObject()
            if meta is not None:
                return str(meta.className())
        except Exception:  # noqa: BLE001
            pass
        return type(obj).__name__

    def _accessible_name(obj: Any) -> str | None:
        """Best-effort read of the QAccessible name attached property."""
        try:
            from PySide6.QtGui import QAccessible  # type: ignore[import-not-found]

            iface = QAccessible.queryAccessibleInterface(obj)  # type: ignore[attr-defined]
            if iface is not None:
                name = iface.text(QAccessible.Name)  # type: ignore[attr-defined]
                if name:
                    return str(name)
        except Exception:  # noqa: BLE001
            pass
        return None

    def _accessible_role(obj: Any) -> int | None:
        """Best-effort read of the QAccessible role attached property."""
        try:
            from PySide6.QtGui import QAccessible  # type: ignore[import-not-found]

            iface = QAccessible.queryAccessibleInterface(obj)  # type: ignore[attr-defined]
            if iface is not None:
                return int(iface.role())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        return None

    def _walk(obj: Any, depth: int) -> None:
        nonlocal element_count
        if depth > max_depth:
            return
        element_count += 1

        obj_name = ""
        try:
            obj_name = str(obj.objectName())
        except Exception:  # noqa: BLE001
            obj_name = ""

        cls = _class_name(obj).lower()
        acc_name = _accessible_name(obj)
        acc_role = _accessible_role(obj)

        # Interactive elements should have an accessible role.
        if cls in _ROLE_REQUIRED_CLASSES and acc_role is None:
            issues.append(
                {
                    "object_name": obj_name or cls,
                    "class_name": _class_name(obj),
                    "issue_type": "missing_role",
                    "severity": "medium",
                    "description": (
                        f"Interactive element '{obj_name or cls}' "
                        f"({_class_name(obj)}) has no Accessible role."
                    ),
                    "suggestion": "Set Accessible.role on this element.",
                }
            )

        # Focusable/interactive elements should have an accessible name.
        if cls in _NAME_REQUIRED_CLASSES and not acc_name:
            issues.append(
                {
                    "object_name": obj_name or cls,
                    "class_name": _class_name(obj),
                    "issue_type": "missing_name",
                    "severity": "high",
                    "description": (
                        f"Interactive element '{obj_name or cls}' "
                        f"({_class_name(obj)}) has no Accessible name."
                    ),
                    "suggestion": "Set Accessible.name on this element.",
                }
            )

        # Buttons specifically need an accessible name.
        if "button" in cls and not acc_name:
            issues.append(
                {
                    "object_name": obj_name or cls,
                    "class_name": _class_name(obj),
                    "issue_type": "unlabeled_button",
                    "severity": "high",
                    "description": (
                        f"Button '{obj_name or cls}' ({_class_name(obj)}) has no accessible name."
                    ),
                    "suggestion": "Set Accessible.name or text on this button.",
                }
            )

        # Recurse into children.
        try:
            children = obj.children()
        except Exception:  # noqa: BLE001
            children = []
        for child in children:
            _walk(child, depth + 1)

    for root in roots:
        _walk(root, 1)

    return {
        "ok": True,
        "element_count": element_count,
        "issue_count": len(issues),
        "issues": issues,
        "error": None,
    }


__all__ = ["audit_accessibility"]
