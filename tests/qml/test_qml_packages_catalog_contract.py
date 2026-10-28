"""QML contract for the Packages view and the curated catalog."""

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return QML_DIR.joinpath(*parts).read_text(encoding="utf-8")


def test_sidebar_labels_the_view_hub():
    """The nav item reads "Hub" while the view key stays "Updates"."""
    sidebar = _read("Sidebar.qml")
    assert 'labelText: "Hub"' in sidebar
    assert 'root.currentView === "Updates"' in sidebar
    assert 'root.navigationChanged("Updates")' in sidebar

    top_bar = _read("TopBar.qml")
    assert 'labelText: "Hub"' in top_bar
    assert 'root.currentView === "Updates"' in top_bar


def test_packages_view_has_the_three_tabs():
    updates = _read("views", "UpdatesView.qml")
    for tab in ("Installed", "Discover", "Project Sync"):
        assert f'label: "{tab}"' in updates
    assert "StackLayout {" in updates
    assert "id: uv_pages" in updates


def test_hub_bar_shows_the_status_summary_and_page_actions():
    """One bar carries the page switcher and the active page's actions."""
    updates = _read("views", "UpdatesView.qml")
    assert 'objectName: "uv_bar"' in updates
    assert " installed" in updates
    assert " outdated" in updates
    assert " unchecked" in updates
    assert 'objectName: "addCustomPackageBtn"' in updates
    assert "AppController.update_controller.scanForUpdates()" in updates
    assert 'hasPendingUpdates ? "Sync All" : "Up to Date"' in updates
    # The bar's right-hand side swaps with the selected tab.
    assert "visible: uv_pages.currentIndex === 0" in updates
    assert 'objectName: "uv_catalogSearch"' in updates
    assert "visible: uv_pages.currentIndex === 1" in updates
    assert 'objectName: "uv_addProjectBtn"' in updates
    assert "visible: uv_pages.currentIndex === 2" in updates


def test_discover_page_renders_the_catalog():
    updates = _read("views", "UpdatesView.qml")
    assert 'objectName: "uv_catalogList"' in updates
    assert "catalogPackages" in updates
    assert "AppController.update_controller.installCatalogPackageDefault(" in updates
    assert "uv_packageEditDialog.openWithTemplate(" in updates
    assert "Installed ✓" in updates
    assert "Configure…" in updates


def test_package_dialog_supports_a_catalog_template():
    """The dialog can be pre-filled from a catalog entry."""
    dialog = _read("dialogs", "PackageEditDialog.qml")
    assert "function openWithTemplate(templateData)" in dialog
    assert "root.editIndex = -1" in dialog
    assert "templateData.display_name" in dialog
    assert "templateData.repository_url" in dialog
    assert "templateData.default_args" in dialog


def test_settings_startup_view_shows_hub_but_stores_updates():
    """The label changed; the persisted view key did not."""
    settings = _read("views", "SettingsView.qml")
    assert '"Last Selected", "Library", "Workbench", "Hub", "Settings"' in settings
    assert 'if (label === "Hub") label = "Updates"' in settings

    # The controller still resolves the "Updates" view key.
    ui_controller = (QML_DIR.parent / "controllers" / "ui_controller.py").read_text(
        encoding="utf-8"
    )
    assert '"updates": "Updates"' in ui_controller
    assert '"packages": "Updates"' in ui_controller
