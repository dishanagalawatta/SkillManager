"""Unit tests for the ``sm_accessibility_audit`` MCP tool handler and bridge.

These tests exercise the handler entry point directly while monkeypatching the
bridge function. They never boot Qt or construct ``AppController``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import skill_manager.mcp.bridge._accessibility as acc_bridge
from skill_manager.mcp.models import ToolResult
from skill_manager.mcp.tools import accessibility as acc_mod


def _explode(*_args: Any, **_kwargs: Any) -> Any:
    """Fail loudly if a guarded code path is reached."""
    raise AssertionError("should not be reached")


def test_accessibility_audit_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit returns the bridge's audit result."""
    fake = {
        "ok": True,
        "element_count": 25,
        "issue_count": 2,
        "issues": [
            {
                "object_name": "save_button",
                "class_name": "QPushButton",
                "issue_type": "missing_name",
                "severity": "high",
                "description": "Interactive element 'save_button' (QPushButton) has no Accessible name.",
                "suggestion": "Set Accessible.name on this element.",
            },
            {
                "object_name": "title_label",
                "class_name": "QLabel",
                "issue_type": "missing_name",
                "severity": "medium",
                "description": "Interactive element 'title_label' (QLabel) has no Accessible name.",
                "suggestion": "Set Accessible.name on this element.",
            },
        ],
        "error": None,
    }
    monkeypatch.setattr(
        acc_mod,
        "_bridge_audit_accessibility",
        lambda max_depth=10: fake,
    )

    result = acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 5})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_accessibility_audit"
    assert result.data == fake
    assert result.data["issue_count"] == 2


def test_accessibility_audit_forwards_max_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit forwards max_depth to the bridge."""
    captured: dict[str, Any] = {}

    def _fake(max_depth: int = 10) -> dict[str, Any]:
        captured["max_depth"] = max_depth
        return {
            "ok": True,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": None,
        }

    monkeypatch.setattr(acc_mod, "_bridge_audit_accessibility", _fake)

    acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 15})
    assert captured["max_depth"] == 15


def test_accessibility_audit_defaults_max_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit defaults max_depth to 10."""
    captured: dict[str, Any] = {}

    def _fake(max_depth: int = 10) -> dict[str, Any]:
        captured["max_depth"] = max_depth
        return {
            "ok": True,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": None,
        }

    monkeypatch.setattr(acc_mod, "_bridge_audit_accessibility", _fake)

    acc_mod.get_handlers()["sm_accessibility_audit"]({})
    assert captured["max_depth"] == 10


def test_accessibility_audit_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        acc_mod,
        "_bridge_audit_accessibility",
        lambda max_depth=10: {
            "ok": False,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": "qml_engine_unavailable",
        },
    )

    result = acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 10})

    assert result.ok is False
    assert result.error is not None
    assert "qml_engine_unavailable" in result.error


def test_accessibility_audit_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        acc_mod,
        "_bridge_audit_accessibility",
        lambda max_depth=10: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 10})

    assert result.ok is False
    assert result.error is not None
    assert "boom" in result.error


def test_accessibility_audit_tool_schema_declared() -> None:
    """sm_accessibility_audit is declared in TOOL_SCHEMAS with valid input schema."""
    assert "sm_accessibility_audit" in acc_mod.TOOL_SCHEMAS
    schema = acc_mod.TOOL_SCHEMAS["sm_accessibility_audit"]
    assert schema["description"]
    assert schema["inputSchema"]["type"] == "object"
    assert "max_depth" in schema["inputSchema"]["properties"]
    assert schema["annotations"]["readOnlyHint"] is True


# ---------------------------------------------------------------------------
# bridge.audit_accessibility — the walk itself
#
# The handler tests above stub the bridge out, so they never exercise the
# traversal, classification or graceful-degradation paths. These use plain
# Python fakes instead of a live QML tree: the accessible walk only needs
# role()/text()/childCount()/child()/object(), and the class-name fallback only
# needs metaObject()/objectName()/children().
# ---------------------------------------------------------------------------
class _FakeMeta:
    def __init__(self, class_name: str) -> None:
        self._class_name = class_name

    def className(self) -> str:  # noqa: N802 - Qt spelling
        return self._class_name


class _FakeQmlObject:
    """Minimal stand-in for a QML QObject in either accessibility walk."""

    def __init__(
        self, class_name: str, object_name: str = "", children: list[Any] | None = None
    ) -> None:
        self._meta = _FakeMeta(class_name)
        self._object_name = object_name
        self._children = list(children or [])

    def metaObject(self) -> _FakeMeta:  # noqa: N802 - Qt spelling
        return self._meta

    def objectName(self) -> str:  # noqa: N802 - Qt spelling
        return self._object_name

    def children(self) -> list[Any]:
        return list(self._children)


class _FakeEngine:
    def __init__(self, roots: list[Any]) -> None:
        self._roots = roots

    def rootObjects(self) -> list[Any]:  # noqa: N802 - Qt spelling
        return list(self._roots)


class _BrokenMeta:
    """Object whose ``metaObject()`` raises (class name falls back to type)."""

    def metaObject(self) -> Any:  # noqa: N802 - Qt spelling
        raise RuntimeError("meta boom")


class _BrokenObjectName(_FakeQmlObject):
    def objectName(self) -> str:  # noqa: N802 - Qt spelling
        raise RuntimeError("name boom")


class _BrokenChildren(_FakeQmlObject):
    def children(self) -> list[Any]:
        raise RuntimeError("children boom")


class _FakeRect:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self._x, self._y, self._width, self._height = x, y, width, height

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class _FakeRole:
    """Role stand-in: the classifier only reads ``.name``."""

    def __init__(self, name: str) -> None:
        self.name = name


class _FakeAccessibleInterface:
    """Accessible-interface double, for both the tree walk and object reads."""

    def __init__(
        self,
        name: str = "",
        role: Any = None,
        children: list[Any] | None = None,
        obj: Any = None,
        rect: _FakeRect | None = None,
    ) -> None:
        self._name = name
        self._role = role
        self._children = list(children or [])
        self._obj = obj
        self._rect = rect

    def text(self, kind: int) -> str:
        return self._name if kind == _FakeAccessible.Name else ""

    def role(self) -> Any:
        return self._role

    def childCount(self) -> int:  # noqa: N802 - Qt spelling
        return len(self._children)

    def child(self, index: int) -> Any:
        return self._children[index]

    def object(self) -> Any:
        return self._obj

    def rect(self) -> _FakeRect | None:
        return self._rect


class _BrokenAccessibleNode(_FakeAccessibleInterface):
    """Node whose ``object()`` and ``childCount()`` both fail."""

    def object(self) -> Any:
        raise RuntimeError("object boom")

    def childCount(self) -> int:  # noqa: N802 - Qt spelling
        raise RuntimeError("count boom")


class _FakeAccessible:
    """Stand-in for ``PySide6.QtGui.QAccessible`` (interface + name lookups)."""

    Name = 7

    def __init__(self, interfaces: dict[int, Any]) -> None:
        self._interfaces = interfaces

    def queryAccessibleInterface(self, obj: Any) -> Any:  # noqa: N802 - Qt spelling
        return self._interfaces.get(id(obj))


def _audit_with(
    monkeypatch: pytest.MonkeyPatch,
    roots: list[Any],
    *,
    controller: Any = "default",
    engine: Any = "default",
    accessible: _FakeAccessible | None = None,
    max_depth: int = 10,
) -> dict[str, Any]:
    """Run the real walk against *roots* with the engine/controller faked."""
    monkeypatch.setattr(
        acc_bridge,
        "_controller_or_none",
        (lambda: SimpleNamespace()) if controller == "default" else (lambda: controller),
    )
    monkeypatch.setattr(
        acc_bridge,
        "ensure_qml_engine",
        (lambda: _FakeEngine(roots)) if engine == "default" else (lambda: engine),
    )
    if accessible is not None:
        from PySide6 import QtGui

        monkeypatch.setattr(QtGui, "QAccessible", accessible, raising=False)
    return acc_bridge.audit_accessibility(max_depth)


def test_bridge_audit_rejects_out_of_range_max_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """max_depth outside 1..30 is refused before anything Qt is touched."""
    monkeypatch.setattr(acc_bridge, "_controller_or_none", _explode)

    for bad in (0, 31):
        result = acc_bridge.audit_accessibility(bad)
        assert result["ok"] is False
        assert result["element_count"] == 0
        assert "max_depth must be between 1 and 30" in result["error"]


def test_bridge_audit_rejects_non_numeric_max_depth() -> None:
    """A non-numeric max_depth degrades instead of raising."""
    result = acc_bridge.audit_accessibility("deep")  # type: ignore[arg-type]

    assert result["ok"] is False
    assert "invalid max_depth" in result["error"]


def test_bridge_audit_requires_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    """No AppController means the audit cannot run."""
    result = _audit_with(monkeypatch, [], controller=None)

    assert result["ok"] is False
    assert result["error"] == "AppController unavailable"


def test_bridge_audit_requires_qml_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """No QML engine means the audit cannot run."""
    result = _audit_with(monkeypatch, [], engine=None)

    assert result["ok"] is False
    assert result["error"] == "QML engine not available"


def test_bridge_audit_requires_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    """An engine with no root objects reports that instead of an empty tree."""
    result = _audit_with(monkeypatch, [])

    assert result["ok"] is False
    assert result["error"] == "no QML root objects"


# ---------------------------------------------------------------------------
# Accessible-tree walk (the normal path on real Qt)
# ---------------------------------------------------------------------------
def test_bridge_audit_walks_the_accessible_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Roles come from Qt's accessible tree; unnamed controls are reported."""
    root_obj = _FakeQmlObject("Main_QMLTYPE_41", object_name="rootWindow")
    named_button = _FakeAccessibleInterface(
        name="Save",
        role=_FakeRole("Button"),
        obj=_FakeQmlObject("ActionButton_QMLTYPE_39"),
    )
    unnamed_button = _FakeAccessibleInterface(
        role=_FakeRole("Button"),
        obj=_FakeQmlObject("IconButton_QMLTYPE_16"),
        rect=_FakeRect(10, 20, 30, 40),
    )
    unnamed_dropdown = _FakeAccessibleInterface(
        role=_FakeRole("ComboBox"),
        obj=_FakeQmlObject("GlassDropdown_QMLTYPE_64"),
    )
    unnamed_scrollbar = _FakeAccessibleInterface(role=_FakeRole("ScrollBar"))
    unnamed_pane = _FakeAccessibleInterface(role=_FakeRole("Pane"))
    root_iface = _FakeAccessibleInterface(
        name="SkillManager",
        role=_FakeRole("Window"),
        obj=root_obj,
        children=[named_button, unnamed_button, unnamed_dropdown, unnamed_scrollbar, unnamed_pane],
    )

    result = _audit_with(
        monkeypatch,
        [root_obj],
        accessible=_FakeAccessible({id(root_obj): root_iface}),
    )

    assert result["ok"] is True
    assert result["source"] == "accessible-tree"
    assert result["element_count"] == 6
    assert result["accessible_nodes"] == 6
    assert result["issue_counts_by_type"] == {"unlabeled_button": 1, "missing_name": 1}

    by_type = {issue["issue_type"]: issue for issue in result["issues"]}
    button = by_type["unlabeled_button"]
    assert button["class_name"] == "IconButton_QMLTYPE_16"
    assert button["role"] == "Button"
    assert button["path"] == "0.1"
    assert (button["x"], button["y"], button["width"], button["height"]) == (10, 20, 30, 40)
    assert button["severity"] == "high"
    assert button["suggestion"]

    dropdown = by_type["missing_name"]
    assert dropdown["path"] == "0.2"
    assert dropdown["role"] == "ComboBox"
    assert "x" not in dropdown, "geometry must be omitted when the node has no rect"


def test_bridge_audit_ignores_containers_and_static_text_on_the_accessible_walk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Roles outside the interactive set (Pane/Client/StaticText) are not issues."""
    root_obj = _FakeQmlObject("Main_QMLTYPE_41")
    container = _FakeAccessibleInterface(
        role=_FakeRole("Client"), obj=_FakeQmlObject("DialogButtonBox_QMLTYPE_52")
    )
    label = _FakeAccessibleInterface(role=_FakeRole("StaticText"), obj=_FakeQmlObject("QQuickText"))
    root_iface = _FakeAccessibleInterface(
        role=_FakeRole("Window"), obj=root_obj, children=[container, label]
    )

    result = _audit_with(
        monkeypatch, [root_obj], accessible=_FakeAccessible({id(root_obj): root_iface})
    )

    assert result["issue_count"] == 0
    assert result["issues"] == []
    assert result["issue_counts_by_type"] == {}


def test_bridge_audit_honours_max_depth_on_the_accessible_walk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The accessible walk stops at max_depth like the fallback walk."""
    deep = _FakeAccessibleInterface(role=_FakeRole("Button"))
    for _ in range(5):
        deep = _FakeAccessibleInterface(role=_FakeRole("Window"), children=[deep])
    root_obj = _FakeQmlObject("Main_QMLTYPE_41")

    result = _audit_with(
        monkeypatch, [root_obj], accessible=_FakeAccessible({id(root_obj): deep}), max_depth=3
    )

    assert result["element_count"] == 3


def test_bridge_audit_tolerates_a_broken_accessible_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raising childCount()/object() degrades instead of aborting the walk."""
    root_obj = _FakeQmlObject("Main_QMLTYPE_41")
    broken = _BrokenAccessibleNode(role=_FakeRole("Button"))

    result = _audit_with(
        monkeypatch, [root_obj], accessible=_FakeAccessible({id(root_obj): broken})
    )

    assert result["ok"] is True
    assert result["element_count"] == 1
    assert result["accessible_nodes"] == 1
    assert result["issues"][0]["issue_type"] == "unlabeled_button"
    assert result["issues"][0]["class_name"] == ""
    assert result["issues"][0]["object_name"] == ""
    assert result["issues"][0]["role"] == "Button"


def test_bridge_audit_falls_back_for_roots_without_an_interface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A root with no accessible interface is class-name audited, not skipped."""
    window = _FakeQmlObject("Main_QMLTYPE_41")
    orphan = _FakeQmlObject(
        "IconButton_QMLTYPE_16",
        object_name="orphan_button",
        children=[_FakeQmlObject("QQuickItem")],
    )

    result = _audit_with(
        monkeypatch,
        [window, orphan],
        accessible=_FakeAccessible(
            {id(window): _FakeAccessibleInterface(role=_FakeRole("Window"), obj=window)}
        ),
    )

    assert result["source"] == "mixed"
    assert result["accessible_nodes"] == 1
    assert result["element_count"] == 3
    assert sorted(issue["issue_type"] for issue in result["issues"]) == [
        "missing_role",
        "unlabeled_button",
    ]
    assert all(issue["object_name"] == "orphan_button" for issue in result["issues"])


# ---------------------------------------------------------------------------
# Class-name fallback walk
# ---------------------------------------------------------------------------
def test_bridge_audit_flags_interactive_element_without_name_or_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unnamed, role-less button is reported as unlabeled with no role."""
    button = _FakeQmlObject("QPushButton", object_name="save_button")
    root = _FakeQmlObject("QQuickItem", object_name="root", children=[button])

    result = _audit_with(monkeypatch, [root])

    assert result["ok"] is True
    assert result["source"] == "class-name-fallback"
    assert result["element_count"] == 2
    assert sorted(issue["issue_type"] for issue in result["issues"]) == [
        "missing_role",
        "unlabeled_button",
    ]
    assert all(issue["object_name"] == "save_button" for issue in result["issues"])
    assert all(issue["severity"] in {"high", "medium"} for issue in result["issues"])
    assert all(issue["suggestion"] for issue in result["issues"])


def test_bridge_audit_accepts_labelled_element_with_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A named element exposing an Accessible role produces no issues."""
    button = _FakeQmlObject("QPushButton", object_name="save_button")
    accessible = _FakeAccessible({id(button): _FakeAccessibleInterface("Save", 9)})

    result = _audit_with(
        monkeypatch,
        [_FakeQmlObject("QQuickItem", children=[button])],
        accessible=accessible,
    )

    assert result["ok"] is True
    assert result["element_count"] == 2
    assert result["issues"] == []
    assert result["issue_count"] == 0


def test_bridge_audit_ignores_button_containers(monkeypatch: pytest.MonkeyPatch) -> None:
    """``DialogButtonBox`` is a container, not an unlabeled button.

    Regression: the old substring classifier flagged every
    ``DialogButtonBox_QMLTYPE_<n>`` in the real tree (8 bogus issues) while
    missing the genuinely unnamed controls.
    """
    container = _FakeQmlObject(
        "DialogButtonBox_QMLTYPE_52", object_name="dialogbuttonbox_qmltype_52"
    )
    real_button = _FakeQmlObject("TitleBarButton", object_name="close_window")

    result = _audit_with(
        monkeypatch, [_FakeQmlObject("QQuickItem", children=[container, real_button])]
    )

    assert [issue["object_name"] for issue in result["issues"]] == ["close_window"] * 2
    assert sorted(issue["issue_type"] for issue in result["issues"]) == [
        "missing_role",
        "unlabeled_button",
    ]


def test_bridge_audit_strips_stacked_qml_decorations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nested QML types stack decorations (``Foo_QMLTYPE_16_QML_109``)."""
    nested = _FakeQmlObject("IconButton_QMLTYPE_16_QML_109", object_name="nested_button")
    plain = _FakeQmlObject("TextField_QMLTYPE_17", object_name="argField")

    result = _audit_with(monkeypatch, [_FakeQmlObject("QQuickItem", children=[nested, plain])])

    assert sorted(issue["issue_type"] for issue in result["issues"]) == [
        "missing_name",
        "missing_role",
        "missing_role",
        "unlabeled_button",
    ]
    assert {issue["object_name"] for issue in result["issues"]} == {"nested_button", "argField"}


def test_bridge_audit_descends_into_children_of_broken_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Objects that raise on metaObject/objectName/children() are tolerated."""
    leaf = _FakeQmlObject("QPushButton", object_name="leaf")
    broken_children = _BrokenChildren(
        "QQuickItem", children=[_FakeQmlObject("QPushButton", object_name="unreachable")]
    )
    broken_name = _BrokenObjectName("QQuickItem", children=[leaf, broken_children])
    root = _FakeQmlObject("QQuickItem", children=[_BrokenMeta(), broken_name])

    result = _audit_with(monkeypatch, [root])

    assert result["ok"] is True
    # root + _BrokenMeta + broken_name + the leaf + broken_children itself; the
    # unreachable child under broken_children is never walked.
    assert result["element_count"] == 5
    assert [issue["object_name"] for issue in result["issues"]] == ["leaf"] * 2


def test_bridge_audit_tolerates_non_list_children(monkeypatch: pytest.MonkeyPatch) -> None:
    """A children() that is not a list/tuple is ignored, not iterated blindly."""

    class _WeirdChildren(_FakeQmlObject):
        def children(self) -> Any:
            return "not-a-list"

    result = _audit_with(
        monkeypatch, [_FakeQmlObject("QQuickItem", children=[_WeirdChildren("QQuickItem")])]
    )

    assert result["ok"] is True
    assert result["element_count"] == 2


def test_bridge_audit_honours_max_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """The walk stops at max_depth instead of traversing the whole tree."""
    deep = _FakeQmlObject("QQuickItem")
    for _ in range(5):
        deep = _FakeQmlObject("QQuickItem", children=[deep])

    result = _audit_with(monkeypatch, [deep], max_depth=3)

    assert result["element_count"] == 3
