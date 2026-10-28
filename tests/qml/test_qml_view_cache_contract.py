"""QML contract for the cached view host (ADR-0048).

Views are created on first visit and then kept alive, so switching is a
visibility flip instead of a full rebuild. The pairing that makes this safe is
``cleanup()`` (detach the models when the view is hidden) + ``activate()``
(re-attach them when it is shown again): a view that cleans up without
activating renders an empty list forever, and a view that never cleans up keeps
its delegate memory while hidden.
"""

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return QML_DIR.joinpath(*parts).read_text(encoding="utf-8")


def test_main_hosts_one_loader_per_view():
    main = _read("Main.qml")

    for loader in ("workbenchView", "libraryView", "hubView", "settingsView"):
        assert f"id: {loader}" in main, f"missing cached loader {loader}"

    # The old destroy-on-switch loader was a single source-bound Loader.
    assert 'source: "views/" + window.currentView.replace(" ", "") + "View.qml"' not in main


def test_host_creates_once_and_then_flips_visibility():
    main = _read("Main.qml")

    assert "function isShowing(view)" in main
    assert "function show(view)" in main
    assert "loader.status === Loader.Null" in main, "views must be created on first visit"
    assert 'loader.source = "views/" + name + "View.qml"' in main
    assert 'typeof loader.item.activate === "function"' in main
    assert "loader.visible = true" in main
    assert "loader.visible = false" in main


def test_host_resets_every_cached_view_on_shutdown():
    main = _read("Main.qml")

    assert "function reset()" in main
    # Shutdown must clean up models before the context goes away.
    assert "loader.item.cleanup()" in main
    assert 'loader.source = ""' in main
    assert "viewLoader.reset()" in main


def test_navigation_uses_view_names_not_sources():
    main = _read("Main.qml")

    assert "if (viewLoader.isShowing(view)) return" in main
    assert "viewLoader.source.toString().indexOf(" not in main


def test_views_that_detach_models_can_reattach_them():
    """cleanup() and activate() must stay in step for every view that has one."""
    view_files = {
        "QuickCopy": "QuickCopyView.qml",
        "Library": "LibraryView.qml",
        "Updates": "UpdatesView.qml",
    }
    for name, filename in view_files.items():
        source = _read("views", filename)
        assert "function cleanup()" in source, f"{name} must clean up when hidden"
        assert "function activate()" in source, f"{name} must re-attach when shown"
        assert "activate()" in source.split("Component.onCompleted:", 1)[1], (
            f"{name} must call activate() once at construction"
        )
        # cacheBuffer is cleared before the model is detached (ADR-0027).
        cleanup_body = source.split("function cleanup()", 1)[1].split("}", 1)[0]
        assert cleanup_body.index("cacheBuffer = 0") < cleanup_body.index("model = null")


def test_every_cached_view_exists_on_disk():
    for filename in (
        "QuickCopyView.qml",
        "LibraryView.qml",
        "UpdatesView.qml",
        "SettingsView.qml",
    ):
        assert (QML_DIR / "views" / filename).exists()
