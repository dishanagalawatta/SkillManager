"""Unit tests for ``bridge/_qml_object.py`` — the shared QML/a11y primitives.

These never boot Qt: the helpers are pure reads over duck-typed objects, so the
tests use minimal fakes and monkeypatch ``PySide6.QtGui.QAccessible`` (real Qt
objects appear only in the integration tests).
"""

from __future__ import annotations

import sys
from typing import Any

import pytest
from PySide6 import QtGui

from skill_manager.mcp.bridge import _qml_object as qo


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _Meta:
    def __init__(self, name: str) -> None:
        self._name = name

    def className(self) -> str:  # noqa: N802 - Qt spelling
        return self._name


class _Obj:
    def __init__(self, class_name: str = "QQuickItem", object_name: str = "") -> None:
        self._meta = _Meta(class_name)
        self._object_name = object_name

    def metaObject(self) -> _Meta:  # noqa: N802 - Qt spelling
        return self._meta

    def objectName(self) -> str:  # noqa: N802 - Qt spelling
        return self._object_name


class _Rect:
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


class _Iface:
    """Accessible-interface double with per-test failure switches."""

    Name = 7

    def __init__(
        self,
        name: str = "",
        role: Any = None,
        *,
        break_role: bool = False,
        break_name: bool = False,
        break_rect: bool = False,
        rect: Any = None,
    ) -> None:
        self._name = name
        self._role = role
        self._break_role = break_role
        self._break_name = break_name
        self._break_rect = break_rect
        self._rect = rect

    def role(self) -> Any:
        if self._break_role:
            raise RuntimeError("role boom")
        return self._role

    def text(self, _kind: int) -> str:
        if self._break_name:
            raise RuntimeError("text boom")
        return self._name

    def rect(self) -> Any:
        if self._break_rect:
            raise RuntimeError("rect boom")
        return self._rect


class _Accessible:
    Name = 7

    def __init__(self, iface: Any, *, explode: bool = False) -> None:
        self._iface = iface
        self._explode = explode

    def queryAccessibleInterface(self, _obj: Any) -> Any:  # noqa: N802 - Qt spelling
        if self._explode:
            raise RuntimeError("query boom")
        return self._iface


def _install_accessible(monkeypatch: pytest.MonkeyPatch, accessible: Any) -> None:
    monkeypatch.setattr(QtGui, "QAccessible", accessible, raising=False)


# ---------------------------------------------------------------------------
# qml_class_name
# ---------------------------------------------------------------------------
def test_qml_class_name_prefers_the_meta_object() -> None:
    assert qo.qml_class_name(_Obj("IconButton_QMLTYPE_16")) == "IconButton_QMLTYPE_16"


def test_qml_class_name_falls_back_to_the_python_class() -> None:
    """PySide exposes every QML item as QQuickItem; the fallback is last resort."""

    class _Bare:
        pass

    assert qo.qml_class_name(_Bare()) == "_Bare"


def test_qml_class_name_survives_a_raising_meta_object() -> None:
    class _Broken:
        def metaObject(self) -> Any:  # noqa: N802 - Qt spelling
            raise RuntimeError("meta boom")

    assert qo.qml_class_name(_Broken()) == "_Broken"


def test_qml_class_name_falls_back_on_an_empty_class_name() -> None:
    assert qo.qml_class_name(_Obj("")) == "_Obj"


def test_qml_class_name_handles_a_missing_meta_object() -> None:
    class _NoMeta:
        def metaObject(self) -> None:  # noqa: N802 - Qt spelling
            return None

    assert qo.qml_class_name(_NoMeta()) == "_NoMeta"


# ---------------------------------------------------------------------------
# interface_role_name
# ---------------------------------------------------------------------------
def test_interface_role_name_reads_the_enum_name() -> None:
    class _Role:
        name = "Button"

    assert qo.interface_role_name(_Iface(role=_Role())) == "Button"


def test_interface_role_name_falls_back_to_the_string_form() -> None:
    """Non-enum roles (ints, dotted reprs) still yield a usable label."""

    class _Dotted:
        def __str__(self) -> str:
            return "Role.ComboBox"

    assert qo.interface_role_name(_Iface(role=_Dotted())) == "ComboBox"
    assert qo.interface_role_name(_Iface(role=9)) == "9"


def test_interface_role_name_returns_none_when_unavailable() -> None:
    assert qo.interface_role_name(None) is None
    assert qo.interface_role_name(_Iface(role=None)) is None
    assert qo.interface_role_name(_Iface(break_role=True)) is None


def test_interface_role_name_handles_an_unprintable_role() -> None:
    class _Empty:
        def __str__(self) -> str:
            return ""

    assert qo.interface_role_name(_Iface(role=_Empty())) is None


# ---------------------------------------------------------------------------
# interface_name
# ---------------------------------------------------------------------------
def test_interface_name_reads_the_name_text() -> None:
    assert qo.interface_name(_Iface("Save")) == "Save"


def test_interface_name_returns_none_for_an_empty_name() -> None:
    assert qo.interface_name(_Iface("")) is None


def test_interface_name_returns_none_without_the_name_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    class _NoName:
        """A QAccessible without the ``Name`` text kind."""

        def queryAccessibleInterface(self, _obj: Any) -> Any:  # noqa: N802 - Qt spelling
            return None

    _install_accessible(monkeypatch, _NoName())
    assert qo.interface_name(_Iface("Save")) is None


def test_interface_name_survives_a_raising_text() -> None:
    assert qo.interface_name(_Iface(break_name=True)) is None


def test_interface_name_returns_none_for_a_missing_interface() -> None:
    assert qo.interface_name(None) is None


# ---------------------------------------------------------------------------
# interface_rect
# ---------------------------------------------------------------------------
def test_interface_rect_returns_a_tuple() -> None:
    assert qo.interface_rect(_Iface(rect=_Rect(1, 2, 3, 4))) == (1, 2, 3, 4)


def test_interface_rect_returns_none_when_unavailable() -> None:
    assert qo.interface_rect(None) is None
    assert qo.interface_rect(_Iface(rect=None)) is None
    assert qo.interface_rect(_Iface(break_rect=True)) is None


# ---------------------------------------------------------------------------
# accessible_interface / accessible_info
# ---------------------------------------------------------------------------
def test_accessible_interface_returns_the_qt_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    iface = _Iface("Save")
    _install_accessible(monkeypatch, _Accessible(iface))
    assert qo.accessible_interface(_Obj()) is iface


def test_accessible_interface_returns_none_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_accessible(monkeypatch, _Accessible(None, explode=True))
    assert qo.accessible_interface(_Obj()) is None
    assert qo.accessible_interface(None) is None


def test_accessible_info_returns_role_and_name(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Role:
        name = "Button"

    _install_accessible(monkeypatch, _Accessible(_Iface("Save", _Role())))
    assert qo.accessible_info(_Obj()) == ("Button", "Save")


def test_helpers_degrade_when_qaccessible_is_unimportable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without the PySide6 accessibility module nothing raises, everything is None."""
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", None)

    assert qo._qaccessible() is None
    assert qo.accessible_interface(_Obj()) is None
    assert qo.interface_name(_Iface("Save")) is None
    assert qo.accessible_info(_Obj()) == (None, None)
