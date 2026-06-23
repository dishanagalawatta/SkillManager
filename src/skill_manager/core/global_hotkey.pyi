"""Type stub override for GlobalHotkeyManager.

See ``qt_model.pyi`` and ``app.pyi`` for the rationale: PySide6 6.11.0's
``QObject`` stub doesn't model the test pattern of replacing a method
at class level (``GlobalHotkeyManager._ensure_pynput = staticmethod(...)``)
for session-scoped monkey-patching. Declaring ``_ensure_pynput`` as
a class-level callable lets the conftest's pattern type-check.
"""

from collections.abc import Callable
from typing import Any, ClassVar

from PySide6.QtCore import QObject, SignalInstance

class GlobalHotkeyManager(QObject):
    # Signals
    hotkeyPressed: ClassVar[SignalInstance]

    # Class-level callable — re-declared from the instance method
    # ``_ensure_pynput`` so ``tests/conftest.py`` can do
    # ``GlobalHotkeyManager._ensure_pynput = staticmethod(lambda: False)``
    # at session scope without a ``reportAttributeAccessIssue`` error.
    # The runtime is a regular instance method (it caches
    # ``self._pynput_available``); the test replaces it with a no-op
    # ``staticmethod`` that ignores ``self`` — both call shapes match
    # the ``Callable[..., bool]`` contract.
    _ensure_pynput: ClassVar[Callable[..., bool]]

    # State
    parent: Any
    _hotkeys: dict[int, tuple[str, str]]
    _listener: Any
    _lock: Any
    _stop_lock: Any
    _pynput_available: bool | None

    def __init__(self, parent: Any = ...) -> None: ...
    def __del__(self) -> None: ...
    def _restart_listener(self) -> None: ...
    def _stop_active_listener(self) -> None: ...
    def stop(self) -> None: ...
    def start(self) -> None: ...
    def register(self, hotkey_id: int, sequence: str) -> bool: ...
    def unregister(self, hotkey_id: int) -> None: ...
    def on_quit(self) -> None: ...
    def _on_global_hotkey(self, hotkey_id: int) -> None: ...

def _make_callback(manager: GlobalHotkeyManager, hotkey_id: int) -> Callable[[], None]: ...
