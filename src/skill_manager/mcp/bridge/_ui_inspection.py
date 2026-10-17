"""UI inspection bridge functions: current QML view, QML tree snapshot, pixel color.

These are read-only accessors over the live SkillManager GUI. They never mutate
app state and degrade gracefully (return ``ok:false`` envelopes) when the Qt
application or controller is unavailable, so they are safe to call headless.
"""

from __future__ import annotations

import base64
import io
from typing import Any

from ._capture import capture_app_window_info
from ._controller import _APP_CONTROLLER_ERROR, _controller_or_none
from ._qml_headless import ensure_qml_engine
from ._telemetry import _log_call


def _attr(obj: Any, name: str, default: Any = "") -> Any:
    """Read an attribute, calling it if it is a callable (Qt objects expose
    properties as methods). Falls back to *default* on any failure."""
    try:
        val = getattr(obj, name, default)
    except Exception:  # noqa: BLE001
        return default
    if callable(val):
        try:
            return val()
        except Exception:  # noqa: BLE001
            return default
    return val


def _flag(obj: Any, *names: str, default: bool = True) -> bool:
    """Read the first available boolean property from *names*.

    ``QQuickItem`` exposes ``isVisible``/``isEnabled`` while ``QWindow``
    only has ``visible``/``enabled``; callers should not care which.
    """
    for name in names:
        value = getattr(obj, name, None)
        if value is None:
            continue
        if callable(value):
            try:
                value = value()
            except Exception:  # noqa: BLE001
                continue
        if value is not None:
            return bool(value)
    return default


def _child_items(obj: Any) -> list[Any]:
    """Return the QML children of *obj*, including a window's content item.

    A ``QQuickWindow``'s own ``childItems()`` list is empty — everything
    declared in QML lives under ``contentItem()`` — so walking only
    ``childItems`` would report a one-node tree for the application window.
    """
    children = _attr(obj, "childItems", []) or []
    if not isinstance(children, (list, tuple)):
        children = []
    children = list(children)

    content = getattr(obj, "contentItem", None)
    if callable(content):
        try:
            content = content()
        except Exception:  # noqa: BLE001
            content = None
    if content is not None and all(child is not content for child in children):
        children.append(content)
    return children


def _qml_node(obj: Any, depth: int, max_depth: int) -> dict[str, Any]:
    """Serialise a single QML object into a bounded node dict."""
    child_objects = _child_items(obj)
    truncated = depth >= max_depth and bool(child_objects)
    return {
        "object_name": str(_attr(obj, "objectName", "") or ""),
        "class_name": obj.__class__.__name__,
        "visible": _flag(obj, "isVisible", "visible"),
        "enabled": _flag(obj, "isEnabled", "enabled"),
        "x": int(_attr(obj, "x", 0) or 0),
        "y": int(_attr(obj, "y", 0) or 0),
        "width": int(_attr(obj, "width", 0) or 0),
        "height": int(_attr(obj, "height", 0) or 0),
        "child_count": len(child_objects),
        "truncated": truncated,
        "children": [_qml_node(child, depth + 1, max_depth) for child in child_objects]
        if not truncated
        else [],
    }


def _count_nodes(nodes: list[dict[str, Any]]) -> int:
    """Total number of serialised nodes in a tree snapshot."""
    return sum(1 + _count_nodes(node.get("children", [])) for node in nodes)


def get_current_view() -> dict[str, Any]:
    """Report the currently active QML view (Library / QuickCopy / Settings / …)."""
    _log_call("get_current_view")
    try:
        controller = _controller_or_none()
        if controller is None:
            return {
                "view": "unknown",
                "ok": False,
                "error": _APP_CONTROLLER_ERROR or "no_controller",
            }
        ui = getattr(controller, "ui", None)
        view = str(_attr(ui, "currentView", "unknown") or "unknown")
        return {"view": view, "ok": True, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"view": "unknown", "ok": False, "error": str(exc)}


def inspect_qml_tree(max_depth: int = 5) -> dict[str, Any]:
    """Capture a bounded snapshot of the QML object tree.

    In ``--mcp`` mode this lazily loads ``Main.qml`` offscreen (see
    ``_qml_headless``) so the tree is available without a running GUI.
    """
    _log_call("inspect_qml_tree")
    try:
        controller = _controller_or_none()
        if controller is None:
            return {
                "ok": False,
                "root_count": 0,
                "tree": [],
                "error": _APP_CONTROLLER_ERROR or "no_controller",
            }
        engine = ensure_qml_engine()
        if engine is None or not hasattr(engine, "rootObjects"):
            return {
                "ok": False,
                "root_count": 0,
                "tree": [],
                "error": "no_qml_engine",
            }
        roots = engine.rootObjects() or []
        tree = [_qml_node(root, depth=0, max_depth=max_depth) for root in roots]
        return {
            "ok": True,
            "root_count": len(tree),
            "node_count": _count_nodes(tree),
            "max_depth": max_depth,
            "tree": tree,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "root_count": 0, "tree": [], "error": str(exc)}


def get_pixel_color(x: int, y: int) -> dict[str, Any]:
    """Read the color of the pixel at (x, y) in the captured app window.

    Coordinates are relative to the captured image (its top-left is ``0, 0``),
    not to the desktop. The capture follows ``capture_app_window_info`` — live
    GUI over IPC, platform-native grab, or the headless offscreen render — and
    the returned ``source`` says which one produced the image.
    """
    _log_call("get_pixel_color")
    try:
        info = capture_app_window_info()
        b64 = info.get("image_b64")
        source = info.get("source")
        if b64 is None:
            return {
                "ok": False,
                "color": "#000000",
                "r": 0,
                "g": 0,
                "b": 0,
                "x": int(x),
                "y": int(y),
                "source": source,
                "error": info.get("error") or "capture_failed",
            }
        raw = base64.b64decode(b64)
        from PIL import Image  # type: ignore[import-not-found]

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        if not (0 <= int(x) < img.width and 0 <= int(y) < img.height):
            return {
                "ok": False,
                "color": "#000000",
                "r": 0,
                "g": 0,
                "b": 0,
                "x": int(x),
                "y": int(y),
                "width": img.width,
                "height": img.height,
                "source": source,
                "error": "coordinate_out_of_bounds",
            }
        r, g, b = img.getpixel((int(x), int(y)))
        return {
            "ok": True,
            "color": f"#{r:02x}{g:02x}{b:02x}",
            "r": int(r),
            "g": int(g),
            "b": int(b),
            "x": int(x),
            "y": int(y),
            "width": img.width,
            "height": img.height,
            "source": source,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "color": "#000000",
            "r": 0,
            "g": 0,
            "b": 0,
            "x": int(x),
            "y": int(y),
            "source": None,
            "error": str(exc),
        }
