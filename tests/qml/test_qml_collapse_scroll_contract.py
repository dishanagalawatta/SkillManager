"""Regression: collapse/expand must preserve list scroll instead of jumping to top.

Root cause: the restore path in the list views only ran while
``AppController.isLoading`` was true. Category collapse/expand emits
``layoutAboutToBeChanged``/``layoutChanged`` with ``isLoading == false``,
so the saved position was discarded and the ListView reset to the top.

The save/restore machine lives in exactly one place — ``SmoothListView``
(``preserveOnCollapse``/``collapseModel``). ``LibraryView`` and
``QuickCopyView`` only opt in. Filter/search passes never emit
``collapsedCategoriesChanged``, so they keep the jump-to-top behavior.

Contract enforced here:
1. ``SmoothListView`` owns the machine (flag, clamp, header anchor).
2. Both list views opt in and carry no duplicated machine.
3. Model ordering: ``toggleCategory`` emits ``collapsedCategoriesChanged``
   before ``layoutAboutToBeChanged`` so the QML flag is set in time.
4. ``firstVisibleRowForCategory`` resolves main (``"Main"``) and section
   (``"Main|Sub"``) names to the anchor row, -1 when absent.
"""

from pathlib import Path

from skill_manager.core.models.qt_model import SkillModel

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(path: str) -> str:
    return (QML_DIR / path).read_text(encoding="utf-8")


def test_scroll_machine_lives_in_smooth_list_view():
    qml = _read("SmoothListView.qml")
    assert "property bool preserveOnCollapse" in qml
    assert "property var collapseModel" in qml
    assert "function _noteCollapseToggled()" in qml
    assert "function _restoreScroll()" in qml
    assert "function _anchorToggledHeader()" in qml
    assert "firstVisibleRowForCategory" in qml
    assert "positionViewAtIndex" in qml
    # Clamp: collapsing shrinks contentHeight, a stale offset must not overshoot.
    assert "contentHeight - root.height" in qml
    # Restore runs for background refresh OR collapse/expand — never unconditionally,
    # so filter/search keeps jump-to-top.
    assert "AppController.isLoading || _collapsePreserve" in qml


def test_library_opts_in_without_duplicating_machine():
    qml = _read("views/LibraryView.qml")
    assert "preserveOnCollapse: true" in qml
    assert "collapseModel: AppController.libraryModel" in qml
    assert "function _restoreScroll()" not in qml
    assert "property real savedScrollPos" not in qml


def test_quickcopy_opts_in_without_duplicating_machine():
    qml = _read("views/QuickCopyView.qml")
    assert "preserveOnCollapse: true" in qml
    assert "collapseModel: AppController.quickCopyModel" in qml
    assert "function _restoreScroll()" not in qml
    assert "property real savedScrollPos" not in qml


def test_collapse_signal_precedes_layout_pair(qapp):
    """The QML flag depends on this ordering: collapse signal first."""
    model = SkillModel()
    model.setSkills(
        [
            {"name": "A1", "category": "Dev", "local_path": "/a1"},
            {"name": "B1", "category": "Ops", "local_path": "/b1"},
        ]
    )
    order: list[str] = []
    model.collapsedCategoriesChanged.connect(lambda: order.append("collapsed"))
    model.layoutAboutToBeChanged.connect(lambda: order.append("layoutAbout"))
    model.layoutChanged.connect(lambda: order.append("layout"))

    model.toggleCategory("Ops")

    assert order[0] == "collapsed"
    assert order.index("layoutAbout") > order.index("collapsed")
    assert model.isCategoryCollapsed("Ops") is True


def test_first_visible_row_for_category(qapp):
    model = SkillModel()
    model.setSkills(
        [
            {"name": "A1", "category": "Dev", "local_path": "/a1"},
            {"name": "A2", "category": "Dev", "local_path": "/a2"},
            {"name": "B1", "category": "Ops", "local_path": "/b1"},
        ]
    )
    main = "⚙️ System & Workflow"
    assert model.firstVisibleRowForCategory(f"{main}|Ops") == 2
    assert model.firstVisibleRowForCategory("Nope|Missing") == -1

    model.toggleCategory(f"{main}|Dev")
    # Collapsed Dev section keeps its single header sentinel row.
    assert model.firstVisibleRowForCategory(f"{main}|Dev") == 0
    assert model.firstVisibleRowForCategory(main) == 0
