"""Interactive offscreen test: collapsing a section must not jump to top.

Loads the real ``SmoothListView`` with a real ``SkillModel`` (60 rows),
scrolls mid-list, toggles a below-viewport section, and asserts the
viewport is preserved. A ``preserveOnCollapse: false`` control harness
demonstrates the original bug (viewport resets to 0).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine

from skill_manager.core.models.qt_model import SkillModel

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)

MAIN = "⚙️ System & Workflow"
DEV_SECTION = f"{MAIN}|Dev"
OPS_SECTION = f"{MAIN}|Ops"

_HARNESS = """
import QtQuick
import SkillManagerComponents 1.0

SmoothListView {
    width: 400
    height: 600
    model: testModel
    collapseModel: testModel
    preserveOnCollapse: __PRESERVE__
    delegate: Item {
        width: 400
        height: 40
        Text { text: (model && model.name) ? model.name : "" }
    }
}
"""


def _make_model(n_dev: int = 30, n_ops: int = 30) -> SkillModel:
    skills = [
        {"name": f"D{i:02d}", "category": "Dev", "local_path": f"/dev{i:02d}"} for i in range(n_dev)
    ] + [
        {"name": f"O{i:02d}", "category": "Ops", "local_path": f"/ops{i:02d}"} for i in range(n_ops)
    ]
    model = SkillModel()
    model.setSkills(skills)
    assert model.rowCount() == n_dev + n_ops
    return model


def _make_view(qapp, qtbot, model: SkillModel, preserve: bool):
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("testModel", model)
    engine.addImportPath(str(QML_DIR.parent))
    component = QQmlComponent(engine)
    component.setData(
        _HARNESS.replace("__PRESERVE__", "true" if preserve else "false").encode(),
        QUrl(""),
    )
    errors = [e.toString() for e in component.errors()]
    assert not errors, f"harness compilation errors: {errors}"
    view = component.create()
    assert view is not None
    QQmlEngine.setObjectOwnership(view, QQmlEngine.CppOwnership)
    qtbot.wait(200)
    qapp.processEvents()
    assert view.property("contentHeight") == 60 * 40
    # Lifetime constraint: created objects die with their QQmlComponent.
    return engine, component, view


def _settle(qapp, qtbot, ms: int = 200) -> None:
    qtbot.wait(ms)
    qapp.processEvents()


def test_collapse_below_viewport_preserves_scroll(qapp, qtbot, app_controller):
    """Toggling a section below the fold keeps the viewport (the reported bug)."""
    model = _make_model()
    _engine, _component, view = _make_view(qapp, qtbot, model, preserve=True)

    view.setProperty("contentY", 200.0)
    _settle(qapp, qtbot, 50)
    assert view.property("contentY") == 200.0

    model.toggleCategory(OPS_SECTION)
    assert model.rowCount() == 31  # 30 Dev + 1 Ops header sentinel
    _settle(qapp, qtbot)

    content_y = view.property("contentY")
    assert content_y is not None and abs(content_y - 200.0) <= 5.0
    # The preserve machine ran (position captured) and disarmed afterwards.
    assert view.property("savedScrollPos") == 200.0
    assert view.property("_collapsePreserve") is False

    # Expanding again keeps the viewport too.
    model.toggleCategory(OPS_SECTION)
    assert model.rowCount() == 60
    _settle(qapp, qtbot)
    assert abs(view.property("contentY") - 200.0) <= 5.0


def test_expand_above_viewport_compensates_shift(qapp, qtbot, app_controller):
    """Expanding a section above the fold shifts contentY down by the added height."""
    model = _make_model()
    _engine, _component, view = _make_view(qapp, qtbot, model, preserve=True)

    model.toggleCategory(DEV_SECTION)  # collapse Dev at top: 60 -> 31 rows
    assert model.rowCount() == 31
    view.setProperty("contentY", 400.0)
    _settle(qapp, qtbot, 50)
    assert view.property("contentY") == 400.0

    model.toggleCategory(DEV_SECTION)  # expand: +29 rows x 40px = +1160 above
    assert model.rowCount() == 60
    _settle(qapp, qtbot)

    # Absolute restore alone would strand the viewport at 400 (wrong content);
    # compensation tracks the shifted content: 400 + 1160 = 1560.
    assert abs(view.property("contentY") - 1560.0) <= 5.0


def test_collapse_above_viewport_compensates_shift(qapp, qtbot, app_controller):
    """Collapsing a fully-above section shifts contentY up by the removed height."""
    # Small head section: Dev rows span 0..400, fully above y0=500 yet inside
    # the instantiate cache, so the removed range is exactly measurable.
    model = _make_model(n_dev=10, n_ops=50)
    _engine, _component, view = _make_view(qapp, qtbot, model, preserve=True)

    view.setProperty("contentY", 500.0)
    _settle(qapp, qtbot, 50)
    assert view.property("contentY") == 500.0

    model.toggleCategory(DEV_SECTION)  # remove Dev rows above: -9 x 40px = -360
    assert model.rowCount() == 51
    _settle(qapp, qtbot)

    # Same Ops row as before, now 360px higher: 500 - 360 = 140.
    assert abs(view.property("contentY") - 140.0) <= 5.0


def test_distant_section_falls_back_to_clamped_restore(qapp, qtbot, app_controller):
    """Beyond the instantiate cache the section is unmeasurable: no yank, no crash."""
    model = _make_model()
    _engine, _component, view = _make_view(qapp, qtbot, model, preserve=True)

    view.setProperty("contentY", 1500.0)  # Dev start (y=0) is outside the cache
    _settle(qapp, qtbot, 50)

    model.toggleCategory(DEV_SECTION)
    _settle(qapp, qtbot)

    # Graceful fallback: clamped to the shrunken content (1240 - 600 = 640).
    assert view.property("contentY") == 640.0


def test_collapse_straddling_viewport_snaps_to_section_start(qapp, qtbot, app_controller):
    """Viewport top inside removed rows snaps to the section start (0)."""
    model = _make_model()
    _engine, _component, view = _make_view(qapp, qtbot, model, preserve=True)

    view.setProperty("contentY", 800.0)  # inside Dev rows (0..1200)
    _settle(qapp, qtbot, 50)

    model.toggleCategory(DEV_SECTION)
    _settle(qapp, qtbot)

    assert view.property("contentY") == 0.0


def test_visible_header_stays_pinned(qapp, qtbot, app_controller):
    """Collapsing the section in view keeps its header visible (anchor)."""
    model = _make_model()
    _engine, _component, view = _make_view(qapp, qtbot, model, preserve=True)

    view.setProperty("contentY", 0.0)
    _settle(qapp, qtbot, 50)

    model.toggleCategory(DEV_SECTION)
    _settle(qapp, qtbot)

    assert view.property("contentY") == 0.0
    assert model.firstVisibleRowForCategory(DEV_SECTION) == 0


def test_control_without_preserve_jumps_to_top(qapp, qtbot, app_controller):
    """Control: with the machine off, the layout reset drops the viewport to 0."""
    model = _make_model()
    _engine, _component, view = _make_view(qapp, qtbot, model, preserve=False)

    view.setProperty("contentY", 200.0)
    _settle(qapp, qtbot, 50)
    assert view.property("contentY") == 200.0

    model.toggleCategory(OPS_SECTION)
    _settle(qapp, qtbot)

    assert view.property("contentY") == 0.0
