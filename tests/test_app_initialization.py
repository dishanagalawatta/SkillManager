from pathlib import Path


def test_app_user_model_id_is_stable():
    """
    Ensure the AppUserModelID does not use a dynamic timestamp which breaks
    Windows taskbar icon grouping.
    """
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    # Locate the AppUserModelID setting block specifically
    start_idx = content.find("myappid = ")
    end_idx = content.find("SetCurrentProcessExplicitAppUserModelID")
    assert start_idx != -1 and end_idx != -1
    block = content[start_idx:end_idx]

    assert 'myappid += ".dev"' in block, "Should append .dev for development builds"
    assert "time.time()" not in block, "Should NOT append a dynamic timestamp to AppUserModelID"


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
    Ensure no broken PyInstaller/loky intercept code exists in __main__.py or app.py.
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

    app_content = (src_dir / "app.py").read_text(encoding="utf-8")
    assert "loky_main" not in app_content, "app.py must not contain loky intercept"
    assert "joblib.externals.loky" not in app_content, "app.py must not import loky"
