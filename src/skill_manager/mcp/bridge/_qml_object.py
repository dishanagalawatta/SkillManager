"""Shared QML object introspection primitives for the MCP UI bridge.

Two facts every UI tool needs and must agree on:

* **QML type name** — ``metaObject().className()`` identifies a QML control
  (``Button_QMLTYPE_42``, ``IconButton_QMLTYPE_16``). ``type(obj).__name__``
  reports ``QQuickItem`` for *every* QML item, which tells an agent nothing.
* **accessible identity** — the role and name Qt's accessibility layer exposes
  for an object (``QAccessible.queryAccessibleInterface``). This is what
  assistive technology actually sees: containers, layouts and static text have
  no interface at all, while real controls report a role.

Every read is defensive: failures return ``None``/empty instead of raising, so a
single exotic object can never break a tree snapshot or an audit.
"""

from __future__ import annotations

from typing import Any


def _qaccessible() -> Any | None:
    """Return the ``QAccessible`` class, honouring monkeypatched test doubles."""
    try:
        from PySide6.QtGui import QAccessible  # type: ignore[import-not-found]

        return QAccessible
    except Exception:  # noqa: BLE001 - Qt may be unavailable
        return None


def qml_class_name(obj: Any) -> str:
    """Return the object's QML type name, falling back to its Python class.

    ``metaObject().className()`` gives the QML type (``TextField_QMLTYPE_18``);
    ``type(obj).__name__`` is a last resort because PySide exposes every QML
    item as ``QQuickItem``.
    """
    try:
        meta = obj.metaObject()
        if meta is not None:
            name = str(meta.className())
            if name:
                return name
    except Exception:  # noqa: BLE001
        pass
    try:
        return type(obj).__name__
    except Exception:  # noqa: BLE001
        return ""


def accessible_interface(obj: Any) -> Any | None:
    """Return Qt's accessible interface for *obj*, or ``None`` when it has none."""
    accessible = _qaccessible()
    if accessible is None or obj is None:
        return None
    try:
        return accessible.queryAccessibleInterface(obj)
    except Exception:  # noqa: BLE001
        return None


def interface_role_name(iface: Any) -> str | None:
    """Return an accessible interface's role name (``"Button"``), or ``None``."""
    if iface is None:
        return None
    try:
        role = iface.role()
    except Exception:  # noqa: BLE001
        return None
    if role is None:
        return None
    name = getattr(role, "name", None)
    if isinstance(name, str) and name:
        return name
    text = str(role)
    if not text:
        return None
    return text.rsplit(".", 1)[-1] or text


def interface_name(iface: Any) -> str | None:
    """Return an accessible interface's name, or ``None`` when it has none."""
    accessible = _qaccessible()
    if accessible is None or iface is None:
        return None
    try:
        kind = getattr(accessible, "Name", None)
        if kind is None:
            return None
        text = iface.text(kind)
    except Exception:  # noqa: BLE001
        return None
    text = str(text) if text else ""
    return text or None


def interface_rect(iface: Any) -> tuple[int, int, int, int] | None:
    """Return an accessible interface's ``(x, y, width, height)``, or ``None``.

    Coordinates are window-relative, which is what makes a reported issue
    locatable on a screenshot.
    """
    if iface is None:
        return None
    try:
        rect = iface.rect()
        return (int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
    except Exception:  # noqa: BLE001
        return None


def accessible_info(obj: Any) -> tuple[str | None, str | None]:
    """Return ``(role_name, name)`` for *obj* as accessibility exposes it."""
    iface = accessible_interface(obj)
    return (interface_role_name(iface), interface_name(iface))


__all__ = [
    "accessible_info",
    "accessible_interface",
    "interface_name",
    "interface_rect",
    "interface_role_name",
    "qml_class_name",
]
