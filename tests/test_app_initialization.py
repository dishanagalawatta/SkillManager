from pathlib import Path


def test_app_user_model_id_is_stable():
    """
    Ensure the AppUserModelID does not use a dynamic timestamp which breaks
    Windows taskbar icon grouping.
    """
    app_py_path = Path(__file__).parent.parent / "src" / "skill_manager" / "app.py"
    content = app_py_path.read_text(encoding="utf-8")

    assert 'myappid += ".dev"' in content, "Should append .dev for development builds"
    assert "time.time()" not in content, "Should NOT append a dynamic timestamp to AppUserModelID"


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
