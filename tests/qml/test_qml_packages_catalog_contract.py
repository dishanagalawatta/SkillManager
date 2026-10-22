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


def test_sidebar_labels_the_view_packages():
    """The nav item reads "Packages" while the view key stays "Updates"."""
    sidebar = _read("Sidebar.qml")
    assert 'labelText: "Packages"' in sidebar
    assert 'root.currentView === "Updates"' in sidebar
    assert 'root.navigationChanged("Updates")' in sidebar

    top_bar = _read("TopBar.qml")
    assert 'labelText: "Packages"' in top_bar
    assert 'root.currentView === "Updates"' in top_bar


def test_packages_view_has_the_three_tabs():
    updates = _read("views", "UpdatesView.qml")
    for tab in ("Installed", "Discover", "Project Sync"):
        assert f'label: "{tab}"' in updates
    assert "StackLayout {" in updates
    assert "id: uv_pages" in updates


def test_packages_view_header_shows_the_status_summary():
    updates = _read("views", "UpdatesView.qml")
    assert 'text: "Packages"' in updates
    assert " installed" in updates
    assert " outdated" in updates
    assert " unchecked" in updates
    assert 'objectName: "addCustomPackageBtn"' in updates
    assert 'labelText: "Check for Updates"' in updates
    assert 'hasPendingUpdates ? "Sync All" : "Up to Date"' in updates


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


def test_settings_startup_view_shows_packages_but_stores_updates():
    """The label changed; the persisted view key did not."""
    settings = _read("views", "SettingsView.qml")
    assert '"Library", "QuickCopy", "Packages", "Settings"' in settings
    assert 'label === "Packages" ? "Updates" : label' in settings

    # The controller still resolves the "Updates" view key.
    ui_controller = (QML_DIR.parent / "controllers" / "ui_controller.py").read_text(
        encoding="utf-8"
    )
    assert '"updates": "Updates"' in ui_controller
    assert '"packages": "Updates"' in ui_controller
