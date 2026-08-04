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


@pytest.fixture(autouse=True)
def reset_shutdown_flag():
    """Ensure sys.is_shutting_down is reset to False before each test."""
    if hasattr(sys, "is_shutting_down"):
        delattr(sys, "is_shutting_down")
    yield
    if hasattr(sys, "is_shutting_down"):
        delattr(sys, "is_shutting_down")


@pytest.fixture(scope="session", autouse=True)
def ci_sigint_dump(request):
    """CI-only diagnostic: capture all thread stacks when SIGINT/SIGBREAK fires.

    Windows CI dies with a KeyboardInterrupt at a fixed point in the suite,
    delivered in the main thread but injected from outside the visible stack.
    This handler dumps every thread's current frame at delivery time — which
    identifies the injecting thread — then re-raises so pytest behaviour is
    unchanged. It also hooks every in-process SIGINT delivery point
    (``os.kill``, ``_thread.interrupt_main``, ``signal.raise_signal``,
    ``signal.signal``) to log the caller's stack, and records the running
    test item plus elapsed time so the trigger can be correlated with suite
    progress. Active only on Windows when ``SKILL_MANAGER_CI_DIAG=1`` is set
    by the CI workflow; remove together with the workflow variable once the
    root cause is fixed.
    """
    if os.name != "nt" or os.environ.get("SKILL_MANAGER_CI_DIAG") != "1":
        yield
        return

    import _thread
    import signal
    import threading
    import time
    import traceback

    dump_path = Path(os.environ.get("SKILL_MANAGER_CI_DIAG_FILE", "sigint_dump.log"))
    session_start = time.monotonic()
    current_item = {"nodeid": None}
    previous = {}
    # First phantom SIGINT on GHA Windows is external (console-wide Ctrl+C);
    # keep the handler installed for the whole process lifetime so late
    # deliveries during finalization are also swallowed and logged.
    _state = {"count": 0}
    _interrupt_signals = [signal.SIGINT]
    if hasattr(signal, "SIGBREAK"):
        _interrupt_signals.append(signal.SIGBREAK)

    def _emit(message: str) -> None:
        # pytest's capture machinery redirects sys.stderr/fd 2 during test
        # execution, so write to the real stderr to reach the CI log.
        for stream in (sys.__stderr__, sys.__stdout__):
            with contextlib.suppress(Exception):
                stream.write(message)
                stream.flush()
        with contextlib.suppress(Exception):
            os.write(2, message.encode())
        with contextlib.suppress(Exception), dump_path.open("a", encoding="utf-8") as f:
            f.write(message)

    def _log_sender(action: str) -> None:
        frames = [f"  {e.filename}:{e.lineno} in {e.name}" for e in traceback.extract_stack()[-8:]]
        _emit(
            f"\n=== CI_SIGINT_SENDER {action} at {time.strftime('%H:%M:%S')} ===\n"
            + "\n".join(frames)
            + "\n"
        )

    def _dump(signum, frame):
        lines = [
            f"\n=== CI_SIGINT_DIAG signum={signum} at {time.strftime('%H:%M:%S')} "
            f"elapsed={time.monotonic() - session_start:.3f}s ===",
            f"current item: {current_item['nodeid']}",
            "main frame: "
            + (
                f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}"
                if frame
                else "None"
            ),
            f"active threads: {threading.active_count()}",
        ]
        for thread_id, fr in sys._current_frames().items():
            thread = next((t for t in threading.enumerate() if t.ident == thread_id), None)
            name = thread.name if thread else f"tid-{thread_id}"
            daemon = thread.daemon if thread else "?"
            lines.append(f"\n--- Thread {name} (daemon={daemon}) ---")
            for entry in traceback.extract_stack(fr)[-6:]:
                lines.append(f"  {entry.filename}:{entry.lineno} in {entry.name}")
        _emit("\n".join(lines) + "\n")
        if signum == signal.SIGINT:
            # Every SIGINT is external (console-wide Ctrl+C on GHA Windows);
            # swallow all of them, including any late delivery during
            # interpreter finalization after the session ends.
            _state["count"] += 1
            _emit(f"=== CI_SIGINT_SWALLOWED #{_state['count']}: SIGINT ignored, continuing ===\n")
            return
        raise KeyboardInterrupt

    import os as _os

    _real_os_kill = _os.kill

    def _hooked_os_kill(pid, sig, *args, **kwargs):
        if sig in _interrupt_signals and pid in (0, _os.getpid(), -1):
            _log_sender(f"os.kill(pid={pid}, sig={sig})")
        return _real_os_kill(pid, sig, *args, **kwargs)

    _real_interrupt_main = _thread.interrupt_main

    def _hooked_interrupt_main():
        _log_sender("_thread.interrupt_main()")
        return _real_interrupt_main()

    _real_raise_signal = signal.raise_signal

    def _hooked_raise_signal(signum):
        if signum in _interrupt_signals:
            _log_sender(f"signal.raise_signal({signum})")
        return _real_raise_signal(signum)

    _real_signal = signal.signal

    def _hooked_signal(signum, handler):
        if signum in _interrupt_signals and handler not in (signal.SIG_DFL, signal.SIG_IGN, _dump):
            _log_sender(f"signal.signal({signum}, {getattr(handler, '__name__', handler)!r})")
        return _real_signal(signum, handler)

    class _ItemTracker:
        @pytest.hookimpl(tryfirst=True)
        def pytest_runtest_protocol(self, item, nextitem):
            current_item["nodeid"] = item.nodeid

    tracker = _ItemTracker()
    request.config.pluginmanager.register(tracker)

    _os.kill = _hooked_os_kill
    _thread.interrupt_main = _hooked_interrupt_main
    signal.raise_signal = _hooked_raise_signal
    signal.signal = _hooked_signal

    import atexit as _atexit

    def _atexit_probe() -> None:
        # Fires only if interpreter finalization completes normally; if the
        # process is terminated externally (e.g. TerminateProcess) this never
        # runs, which distinguishes a silent kill from a Python-side exit 1.
        _emit(
            f"\n=== CI_DIAG ATEXIT at {time.strftime('%H:%M:%S')} "
            f"elapsed={time.monotonic() - session_start:.3f}s ===\n"
        )

    _atexit.register(_atexit_probe)

    for sig in _interrupt_signals:
        with contextlib.suppress(Exception):
            previous[sig] = signal.signal(sig, _dump)
    try:
        yield
    finally:
        # Deliberately do NOT restore the SIGINT handler: the phantom Ctrl+C
        # also fires after the session ends (during interpreter finalization),
        # where an unhandled KeyboardInterrupt would flip a green run to exit 1.
        request.config.pluginmanager.unregister(tracker)


def _ci_diag_active() -> bool:
    return os.name == "nt" and os.environ.get("SKILL_MANAGER_CI_DIAG") == "1"


def pytest_sessionfinish(session, exitstatus):  # pragma: no cover - CI-only probe
    if not _ci_diag_active():
        return
    _ci_diag_emit(f"\n=== CI_DIAG SESSIONFINISH exitstatus={exitstatus} ===\n")


def pytest_unconfigure(config):  # pragma: no cover - CI-only probe
    if not _ci_diag_active():
        return
    _ci_diag_emit("\n=== CI_DIAG UNCONFIGURE ===\n")


def _ci_diag_emit(message: str) -> None:
    import time

    stamp = time.strftime("%H:%M:%S")
    for stream in (sys.__stderr__, sys.__stdout__):
        with contextlib.suppress(Exception):
            stream.write(f"{stamp} {message}")
            stream.flush()
    with contextlib.suppress(Exception):
        os.write(2, f"{stamp} {message}".encode())
