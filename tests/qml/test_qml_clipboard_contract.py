"""QML contract tests for the copy-to-clipboard surfaces.

Regression guard for the broken Copy buttons:
- ``ImageInspector.qml`` used to call ``AppController.clipboard.setText``
  (``_clipboard`` was a private Python attr, not QML-exposed -> silent ReferenceError).
- ``InspectorActionBar.qml`` used to call ``AppController.ui_controller.copyToClipboard``
  (no such method exists -> silent TypeError).

All QML copy actions must route through the QML-exposed slot
``AppController.ops_controller.copyTextToClipboard(...)``.
"""

from pathlib import Path

_SKILL_MANAGER_COMPONENTS = (
    Path(__file__).resolve().parents[2] / "src" / "skill_manager" / "SkillManagerComponents"
)

# QML files known to contain copy actions (any other file touching the
# clipboard must go through the same slot).
_COPY_QML_FILES = (
    "ImageInspector.qml",
    "InspectorActionBar.qml",
)


def _read_qml(name: str) -> str:
    return (_SKILL_MANAGER_COMPONENTS / name).read_text(encoding="utf-8")


def test_qml_copy_surfaces_do_not_use_non_exposed_apis():
    for name in _COPY_QML_FILES:
        source = _read_qml(name)
        assert "clipboard.setText" not in source, (
            f"{name}: AppController.clipboard is not QML-exposed; "
            "use AppController.ops_controller.copyTextToClipboard(...)"
        )
        assert "ui_controller.copyToClipboard" not in source, (
            f"{name}: ui_controller has no copyToClipboard; "
            "use AppController.ops_controller.copyTextToClipboard(...)"
        )


def test_qml_copy_surfaces_route_through_ops_controller():
    for name in _COPY_QML_FILES:
        source = _read_qml(name)
        assert "ops_controller.copyTextToClipboard" in source, (
            f"{name}: no copy path through AppController.ops_controller.copyTextToClipboard"
        )
