"""Contracts for the 2026-10-28 top-bar/nav reshuffle and client selectors.

Covers the user-facing changes from the TODO batch:

* the nav labels read Workbench / Hub while the view keys stay
  ``QuickCopy`` / ``Updates``;
* Snap is an icon button in the actions cluster, immediately left of
  Refresh, and folds into the overflow menu when the bar is narrow;
* the top bar shows two client selectors by default and accepts up to four.
"""

from pathlib import Path

from skill_manager.core.schemas import AppConfig

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return QML_DIR.joinpath(*parts).read_text(encoding="utf-8")


# --------------------------------------------------------------- nav labels
def test_nav_labels_read_workbench_and_hub():
    top_bar = _read("TopBar.qml")
    sidebar = _read("Sidebar.qml")

    for source in (top_bar, sidebar):
        assert 'labelText: "Workbench"' in source
        assert 'labelText: "Hub"' in source
        # The persisted view keys never change.
        assert 'root.currentView === "Updates"' in source

    assert 'navigationChanged("Updates")' in top_bar
    assert 'navigationChanged("Quick Copy")' in top_bar


def test_top_bar_has_no_text_snap_tab():
    top_bar = _read("TopBar.qml")
    assert 'labelText: "Snap"' not in top_bar
    assert 'objectName: "topSnapBtn"' in top_bar
    # ...it is an icon button in the actions cluster now.
    snap_block = top_bar[top_bar.index('objectName: "topSnapBtn"') - 400 :]
    assert "IconButton {" in snap_block
    assert "AppController.snap_controller.takeSnap()" in snap_block


def test_snap_sits_immediately_left_of_refresh():
    top_bar = _read("TopBar.qml")
    snap = top_bar.index('objectName: "topSnapBtn"')
    refresh = top_bar.index("id: topRefreshBtn")
    overflow = top_bar.index("id: topOverflowBtn")
    nav = top_bar.index("id: navRow")
    assert nav < snap < refresh < overflow, "snap must precede refresh in the actions row"


def test_narrow_bar_folds_snap_into_overflow():
    top_bar = _read("TopBar.qml")
    assert "var snapW = phase >= 3 ? 0 : _wSnap" in top_bar
    # The overflow menu keeps Snap reachable once the icon is gone.
    assert 'text: "Take Snap"' in top_bar
    assert "visible: root._topPhase < 3 && !root.searchExpanded" in top_bar


# ------------------------------------------------------------ client selectors
def test_default_top_bar_has_two_client_selectors():
    config = AppConfig()
    assert config.top_bar_clients == ["Plain Text", "Gemini CLI"]


def test_legacy_four_selector_default_is_trimmed():
    config = AppConfig(top_bar_clients=["Plain Text", "Gemini CLI", "Antigravity", "Codex"])
    assert config.top_bar_clients == ["Plain Text", "Gemini CLI"]


def test_user_edited_selector_list_is_preserved_up_to_four():
    edited = ["Plain Text", "Antigravity", "OpenCode"]
    assert AppConfig(top_bar_clients=edited).top_bar_clients == edited

    too_many = ["Plain Text", "Gemini CLI", "Antigravity", "Codex", "OpenCode"]
    assert AppConfig(top_bar_clients=too_many).top_bar_clients == too_many[:4]


def test_single_selector_falls_back_to_the_default_pair():
    assert AppConfig(top_bar_clients=["Codex"]).top_bar_clients == ["Plain Text", "Gemini CLI"]


def test_settings_can_add_and_remove_optional_selectors():
    settings = _read("views", "SettingsView.qml")

    assert "function _addTopBarClient()" in settings
    assert "function _removeTopBarClient(index)" in settings
    assert "function _setTopBarClient(index, format)" in settings
    # Add is capped at four, removal is limited to the optional slots.
    assert "if (arr.length >= 4) return" in settings
    assert "if (index < 2 || index >= arr.length) return" in settings
    assert 'objectName: "addTopBarClientBtn"' in settings
    assert "topBarClients.length : 2) < 4" in settings
    assert "visible: topClientRow.index >= 2" in settings


def test_workbench_bar_renders_the_configured_selectors():
    quick_copy = _read("views", "QuickCopyView.qml")
    # The logo row is driven by the configured selectors, not every format.
    assert "model: AppController.clientFormats" in quick_copy
    # ...while the collapsed dropdown still reaches every available format.
    assert "AppController.config_controller.availableClientFormats" in quick_copy
