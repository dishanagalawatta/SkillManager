import contextlib
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock

# Pre-inject a mock pynput module so the real C extension never loads.
# Pynput's Windows keyboard hook thread can cause access violations
# when the process exits while the thread is still iterating the
# message queue.  By intercepting the import at the module level,
# we guarantee no real keyboard hook is ever created during testing.
if "pynput" not in sys.modules:
    _mock_pynput = MagicMock()
    _mock_pynput.keyboard = MagicMock()
    _mock_pynput.keyboard.HotKey = MagicMock()
    _mock_pynput.keyboard.Listener = MagicMock()
    sys.modules["pynput"] = _mock_pynput
    sys.modules["pynput.keyboard"] = _mock_pynput.keyboard

# Force QML style before ANY Qt imports to prevent initialization errors
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
# Use offscreen platform for headless environments by default in tests
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Import QtQuick/QtWidgets to ensure types are registered
import PySide6.QtQuick  # noqa: F401
import PySide6.QtWidgets  # noqa: F401
import pytest
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

# Automatically add 'src' to PYTHONPATH for all tests
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from skill_manager.utils.task_runner import SynchronousTaskRunner  # noqa: E402

# Global test configuration
os.environ["SKILL_MANAGER_TESTING"] = "1"
os.environ["POSTHOG_PROJECT_TOKEN"] = ""
os.environ["POSTHOG_HOST"] = ""
os.environ["SKILL_MANAGER_SKIP_INITIAL_LOAD"] = "1"

os.environ.setdefault(
    "SKILL_MANAGER_DATA_DIR",
    str(Path(tempfile.gettempdir()) / f"skillmanager-pytest-{uuid.uuid4().hex}" / "data"),
)

# Monkeypatch os.unlink to workaround Python 3.14 + Pytest issue with Windows junctions
_original_os_unlink = os.unlink


def _safe_os_unlink(path, *args, **kwargs):
    try:
        _original_os_unlink(path, *args, **kwargs)
    except PermissionError as e:
        if "pytest-current" in str(path):
            with contextlib.suppress(Exception):
                os.rmdir(path)
            return
        raise e


os.unlink = _safe_os_unlink


@pytest.fixture(scope="session")
def qapp_cls():
    """Tells pytest-qt to use QApplication instead of QGuiApplication."""
    return QApplication


@pytest.fixture(scope="session", autouse=True)
def setup_qml_style(qapp):
    """Ensures QQuickStyle is set on the qapp instance."""
    QQuickStyle.setStyle("Basic")
    yield


@pytest.fixture(scope="session", autouse=True)
def block_real_pynput(request):
    """Prevent any test from starting a real pynput keyboard listener.

    Pynput's Windows listener thread can crash with an access violation
    when the process exits before the thread finishes iterating the
    message queue.  By forcing ``_ensure_pynput`` to return ``False``
    for the entire session, we guarantee no real keyboard hook is
    ever created during testing.

    Tests decorated with ``@pytest.mark.allow_pynput`` skip this
    block so their own mock keyboard module is used instead.
    """
    from skill_manager.core.global_hotkey import GlobalHotkeyManager

    original = GlobalHotkeyManager._ensure_pynput
    GlobalHotkeyManager._ensure_pynput = staticmethod(lambda: False)
    yield
    GlobalHotkeyManager._ensure_pynput = original


@pytest.fixture
def temp_dir():
    """Provides a temporary directory that is automatically cleaned up."""
    path = Path(tempfile.gettempdir()) / f"skillmanager-test-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


from skill_manager.core.config import ConfigManager  # noqa: E402


@pytest.fixture(scope="session")
def session_temp_dir():
    """Provides a session-scoped temporary directory."""
    path = Path(tempfile.gettempdir()) / f"skillmanager-session-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def session_mock_config(session_temp_dir):
    """Provides a session-scoped mock config."""
    data_dir = session_temp_dir / "data"
    data_dir.mkdir()
    os.environ["SKILL_MANAGER_DATA_DIR"] = str(data_dir)
    config = ConfigManager()
    yield config
    # Do NOT pop SKILL_MANAGER_DATA_DIR — the session-level env var
    # must persist so that every subsequent test uses the test-specific
    # data dir instead of falling back to the real app-data directory.


@pytest.fixture
def mock_config(temp_dir):
    """Provides a function-scoped mock config."""
    data_dir = temp_dir / "data"
    data_dir.mkdir(exist_ok=True)
    previous = os.environ.get("SKILL_MANAGER_DATA_DIR")
    os.environ["SKILL_MANAGER_DATA_DIR"] = str(data_dir)
    config = ConfigManager()
    yield config
    # Restore the previous value instead of popping — prevents leakage
    # to tests that don't use this fixture.
    if previous is not None:
        os.environ["SKILL_MANAGER_DATA_DIR"] = previous
    else:
        os.environ.pop("SKILL_MANAGER_DATA_DIR", None)


@pytest.fixture
def mock_app():
    """Provides a shared mock for AppController with common attributes."""
    app = MagicMock()
    app.task_runner = SynchronousTaskRunner()
    # Core state
    app._selected_skill = {}
    app._archive_paths = []
    app._starred_paths = []
    app._is_loading = False
    app._status_message = ""
    app._sources = []
    app._projects = []
    app._update_sources = []
    app._syncing_projects = []
    app._project_aliases = {}
    app._update_results = []

    # Models
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app.skillModel = MagicMock()

    # Dependencies
    app._config = MagicMock()
    app._clipboard = MagicMock()
    app.clipboard_service = MagicMock()
    app.clipboard_service.copy_text.return_value = True

    # Common methods
    app._set_status = MagicMock()
    app.refreshSkills = MagicMock()
    app.load_initial_data = MagicMock()
    app.getProjectLabel.side_effect = lambda t: t.split("/")[-1] if t else ""

    return app


@pytest.fixture
def skill_factory():
    def _make_skill(**overrides):
        base = {
            "id": "test-id",
            "name": "Test Skill",
            "category": "Dev",
            "local_path": "/path/to/skill",
            "is_selected": False,
            "is_starred": False,
            "is_source": True,
            "project_label": "Master Library",
        }
        base.update(overrides)
        return base

    return _make_skill


@pytest.fixture
def source_factory():
    def _make_source(**overrides):
        base = {
            "name": "Test Source",
            "source_type": "git",
            "repository_url": "https://github.com/test/repo",
            "local_path": "/local/repo",
        }
        base.update(overrides)
        return base

    return _make_source


@pytest.fixture(scope="session")
def app_controller(session_mock_config, session_temp_dir):
    """Provides an AppController initialized for testing (session-scoped)."""
    import skill_manager.app
    from skill_manager.app import AppController

    # We use SynchronousTaskRunner to avoid threading issues in tests
    controller = AppController(skip_initial_load=True, config=session_mock_config)
    controller.task_runner = SynchronousTaskRunner()

    skill_manager.app.current_test_controller = controller  # type: ignore[attr-defined]

    def controller_factory(qml_engine):
        from PySide6.QtQml import QQmlEngine

        ctrl = skill_manager.app.current_test_controller  # type: ignore[attr-defined]
        if ctrl:
            QQmlEngine.setObjectOwnership(ctrl, QQmlEngine.CppOwnership)  # type: ignore[attr-defined]
        return ctrl

    from contextlib import suppress

    with suppress(Exception):
        from PySide6.QtQml import qmlRegisterSingletonType

        # This registration is process-wide. PySide6 6.11.0's stub claims
        # ``qml_name`` must be bytes but the runtime requires str.
        qmlRegisterSingletonType(
            AppController,
            "App",
            1,
            0,
            "AppController",  # type: ignore[arg-type]
            controller_factory,
        )

    yield controller
    controller.on_quit()


@pytest.fixture
def qml_engine(qapp, app_controller, qtbot):
    """Provides a QQmlApplicationEngine with the AppController already registered."""
    from PySide6.QtQml import QQmlApplicationEngine

    import skill_manager
    from skill_manager.core.resources import qml_components_dir

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)

    qml_dir = qml_components_dir(package_file=skill_manager.__file__)
    engine.addImportPath(str(qml_dir.parent))

    qml_file = qml_dir / "Main.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        pytest.fail("Failed to load Main.qml")

    yield engine

    engine.clearComponentCache()
    engine.deleteLater()
    for _ in range(5):
        qapp.processEvents()
        qtbot.wait(20)


@pytest.fixture
def clean_models(app_controller):
    """Reset incubation state on session-scoped models.

    No-op in test mode (SKILL_MANAGER_TESTING) since the model's
    incubating setter already ignores writes. Kept for compatibility
    with tests that explicitly request it.
    """
    yield


#: The filter fields a test can change on a model.  They are restored
#: after every test so one test cannot leak its filter state into the
#: next one.
_FILTER_FIELDS = (
    "is_package_only",
    "filter_by_client",
    "client_filter",
    "filter_text",
    "category_filter",
    "collection_filter",
    "project_filter",
    "show_commands",
    "show_starred",
    "show_archived",
)


@pytest.fixture(autouse=True)
def restore_session_model_filters():
    """Restore the session-scoped models' filter state after each test.

    The AppController (and therefore both SkillModels) lives for the whole
    session, so a test that changes a filter — e.g. the discovery flow
    clearing ``is_package_only`` — used to leak that state into every
    later test in the same worker.  The Quick Copy view would then list
    package skills as well, and the row order would depend on which test
    ran before.

    The controller is only reused when it already exists; this fixture
    never creates one.
    """
    import skill_manager.app

    controller = getattr(skill_manager.app, "current_test_controller", None)
    if controller is None:
        yield
        return

    models = [controller.libraryModel, controller.quickCopyModel]
    saved = [
        {name: getattr(model.state, name, None) for name in _FILTER_FIELDS} for model in models
    ]

    yield

    for model, values in zip(models, saved, strict=True):
        for name, value in values.items():
            # A restore must never fail a test.
            with contextlib.suppress(Exception):
                setattr(model.state, name, value)


@pytest.fixture(autouse=True)
def reset_shutdown_flag():
    """Ensure sys.is_shutting_down is reset to False before each test."""
    if hasattr(sys, "is_shutting_down"):
        delattr(sys, "is_shutting_down")
    yield
    if hasattr(sys, "is_shutting_down"):
        delattr(sys, "is_shutting_down")


@pytest.fixture(scope="session", autouse=True)
def windows_ci_sigint_guard():
    """Swallow the phantom console-wide SIGINT delivered once per GHA Windows run.

    GHA Windows CI delivers one external CTRL+C event per run (the same
    console-wide event the step shell sees; see ``_test-python.yml``). Without
    a handler, Python's default KeyboardInterrupt aborts the suite mid-run at
    a fixed test. The handler swallows every SIGINT for the whole process
    lifetime and is deliberately never restored, so a late delivery during
    interpreter finalization cannot flip a green run to exit 1. Active only on
    Windows when ``SKILL_MANAGER_WIN_SIGINT_GUARD=1`` is set by the CI
    workflow, so local Ctrl+C still interrupts test runs.
    """
    if os.name != "nt" or os.environ.get("SKILL_MANAGER_WIN_SIGINT_GUARD") != "1":
        yield
        return

    import signal

    def _swallow(signum, frame):
        return None

    with contextlib.suppress(Exception):
        signal.signal(signal.SIGINT, _swallow)
    yield


# ---------------------------------------------------------------------------
# Linux Qt teardown guard
# ---------------------------------------------------------------------------
#: Exit status captured in ``pytest_sessionfinish`` for the guard below.
_QT_EXIT_STATUS = {"code": 0}


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Record pytest's real status before Qt's teardown can clobber it."""
    _QT_EXIT_STATUS["code"] = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    """Exit before Qt's own process teardown runs, on Linux only.

    On Linux, once a session has loaded ``Main.qml`` through the
    ``qml_engine`` fixture and run a few update-controller tests, Qt 6.11's
    atexit path destroys the ``QApplication``'s private data twice. Every
    test passes first; the double free only corrupts the *exit status*
    (``134``/``139``), which made ``uv run pytest`` look like a failure:

        ERROR: AddressSanitizer: attempting double-free on 0x…de0
            #0 operator delete(void*, unsigned long)
            #1 libQt6Core.so.6+0x2a6729
            #2 libQt6Core.so.6+0x35aaff
            #3 __run_exit_handlers  stdlib/exit.c:118
        0x…de0 is located 0 bytes inside of 32-byte region
        previously allocated by thread T0 here:
            #2 QBindingStorage::QBindingStorage()
            #3 QObjectPrivate::QObjectPrivate(QtPrivate_6_11_1)
            #4 QCoreApplicationPrivate::QCoreApplicationPrivate(int&, char**)

    That is Qt's own exit path freeing the ``QApplication``'s binding
    storage, not project code: the crash needs only a loaded ``Main.qml``
    plus two ``downloadAndInstallUpdate`` tests, survives deleting the
    engines, the ``QApplication``, or ``QQuickStyle`` first, and does not
    reproduce in the shipped app. CI only runs on Windows, so it never
    surfaced there.

    Running the suite to completion and then leaving via ``os._exit``
    skips Qt's broken teardown while preserving pytest's exit status.
    Coverage and the terminal summary are written in
    ``pytest_sessionfinish``, which runs before this hook. Set
    ``SKILL_MANAGER_QT_EXIT_GUARD=0`` to opt out (e.g. when profiling the
    teardown itself).
    """
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("SKILL_MANAGER_QT_EXIT_GUARD") == "0":
        return
    # xdist workers must return normally from pytest.main() so execnet can
    # deliver the result; a hard exit there stalls the controller.
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return
    # Nothing to guard when Qt was never imported (pure-Python test runs).
    if "PySide6.QtCore" not in sys.modules:
        return

    with contextlib.suppress(Exception):
        from PySide6.QtCore import QCoreApplication

        if QCoreApplication.instance() is None:
            return

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_QT_EXIT_STATUS["code"])
