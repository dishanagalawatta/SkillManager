import inspect
from pathlib import Path

from skill_manager.bootstrap import _set_app_user_model_id


def test_app_user_model_id_is_stable():
    """
    Ensure the AppUserModelID does not use a dynamic timestamp which breaks
    Windows taskbar icon grouping.
    """
    source = inspect.getsource(_set_app_user_model_id)

    assert 'myappid += ".dev"' in source, "Should append .dev for development builds"
    assert "time.time()" not in source, "Should NOT append a dynamic timestamp to AppUserModelID"
    assert "SetCurrentProcessExplicitAppUserModelID" in source, (
        "Must set the AppUserModelID via the shell32 API"
    )


def test_main_qml_visibility_deferred():
    """
    Ensure Main.qml is initially visible: false so that the window icon
    can be set before the window is shown to the OS window manager.
    """
    main_qml_path = (
        Path(__file__).parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "Main.qml"
    )
    content = main_qml_path.read_text(encoding="utf-8")

    assert "visible: false" in content, "Main.qml should defer visibility to avoid icon glitches"
    assert "visible: true" not in content, "Main.qml must not be visible by default"


def test_no_loky_intercept_in_entrypoint():
    """
    Ensure no broken PyInstaller/loky intercept code exists in __main__.py, app.py,
    or bootstrap.py.
    ADR-0021: loky's frozen-mode fork is broken on Windows (OSError: WinError 6).
    The fix uses joblib_prefer() to select threads in frozen builds, so the
    broken intercept code was removed from both entrypoints.
    """
    src_dir = Path(__file__).parent.parent / "src" / "skill_manager"

    main_content = (src_dir / "__main__.py").read_text(encoding="utf-8")
    assert "loky_main" not in main_content, "__main__.py must not contain loky intercept"
    assert (
        "--multiprocessing-fork" not in main_content
        or "multiprocessing-fork" in main_content
        and "joblib_main" not in main_content
    ), "__main__.py must not intercept --multiprocessing-fork for loky"

    for name in ("app.py", "bootstrap.py"):
        content = (src_dir / name).read_text(encoding="utf-8")
        assert "loky_main" not in content, f"{name} must not contain loky intercept"
        assert "joblib.externals.loky" not in content, f"{name} must not import loky"


def test_boot_normalization_self_healing(tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    from skill_manager.app import AppController

    monkeypatch.delenv("SKILL_MANAGER_SKIP_INITIAL_LOAD", raising=False)

    real_dir = tmp_path / "valid_project"
    real_dir.mkdir()
    skills_dir = real_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    malformed_path = f"/some/cwd{real_dir.as_posix()}/.agents/skills"

    controller = MagicMock(spec=AppController)
    controller._projects = [malformed_path]
    controller._config = MagicMock()

    AppController._normalize_project_paths_on_startup(controller)

    assert controller._projects[0] == str(skills_dir.resolve())
    controller._config.set.assert_called_with("projects", controller._projects)


def test_desktop_wmclass_and_app_id_sync():
    """
    Ensure the desktop file StartupWMClass matches the applicationName in bootstrap.py
    and Main.qml title for correct taskbar/dock icon grouping on Linux and Windows.
    """
    repo_root = Path(__file__).parent.parent
    desktop_file = repo_root / "packaging" / "linux" / "skill-manager.desktop"
    desktop_content = desktop_file.read_text(encoding="utf-8")

    assert "StartupWMClass=SkillManager" in desktop_content
    assert "Icon=skill-manager" in desktop_content
    assert "Exec=skill-manager %U" in desktop_content

    bootstrap_file = repo_root / "src" / "skill_manager" / "bootstrap.py"
    bootstrap_content = bootstrap_file.read_text(encoding="utf-8")
    assert 'app.setDesktopFileName("skill-manager")' in bootstrap_content
    assert 'app.setApplicationName("SkillManager")' in bootstrap_content

    main_qml = repo_root / "src" / "skill_manager" / "SkillManagerComponents" / "Main.qml"
    main_qml_content = main_qml.read_text(encoding="utf-8")
    assert 'title: "SkillManager"' in main_qml_content
