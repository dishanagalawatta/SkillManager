"""Reliable cross-platform clipboard writes with verification and fallback.

Qt's ``QClipboard`` can silently fail on several platforms: X11 selection
handoff requires the event loop to flush, Wayland compositor/clipboard-manager
races can drop writes, and headless/offscreen sessions accept writes without
ever publishing them. The app previously wrote through ``QClipboard.setText``
directly and reported success regardless — the "Copy button does not work
reliably" failure mode.

This service fixes that by:

1. Writing via native tools (``wl-copy`` on Wayland) first when
   ``prefer_native`` is set, verifying by reading the *system* clipboard
   back (``wl-paste``) — Qt's own read-back can report success while the
   compositor never received the data.
2. Writing via Qt ``QClipboard`` (lazy, ``None``-safe acquisition),
   flushing the event loop and verifying by reading back (one retry).
3. Falling back to an injected fallback or native tools (``wl-copy`` /
   ``pyperclip`` on Linux).
4. Returning a boolean so callers can report accurate status.

The clipboard is *data transfer*, not input injection, so no
``input_guard`` routing applies here.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel distinguishing "not provided" (lazy Qt lookup) from "explicitly
# disabled" (``qt_clipboard=None`` forces the native fallback path).
_LAZY = object()


def normalize_newlines(text: str) -> str:
    """Normalize CRLF/CR to LF so read-back verification survives platform
    newline translation (e.g. X11 clipboard mime conversion)."""
    return str(text).replace("\r\n", "\n").replace("\r", "\n")


def _resolve_native_writer() -> Callable[[str], bool] | None:
    """Return the Linux native clipboard writer, or ``None`` off-Linux."""
    if sys.platform != "linux":
        return None
    try:
        from skill_manager.utils.linux import set_clipboard

        return set_clipboard
    except Exception as exc:  # noqa: BLE001
        logger.debug("linux.set_clipboard unavailable: %s", exc)
        return None


def _resolve_native_reader() -> Callable[[], str | None] | None:
    """Return the Linux native clipboard reader, or ``None`` off-Linux."""
    if sys.platform != "linux":
        return None
    try:
        from skill_manager.utils.linux import get_clipboard

        return get_clipboard
    except Exception as exc:  # noqa: BLE001
        logger.debug("linux.get_clipboard unavailable: %s", exc)
        return None


class ClipboardService:
    """Writes text to the system clipboard with verification and fallback.

    Parameters are injectable for tests; production usage is
    ``ClipboardService()`` or ``ClipboardService(qt_clipboard)``.
    """

    def __init__(
        self,
        qt_clipboard: Any = _LAZY,
        fallback: Callable[[str], bool] | None = None,
        process_events: Callable[[], None] | None = None,
        *,
        native_writer: Callable[[str], bool] | None = None,
        native_reader: Callable[[], str | None] | None = None,
        prefer_native: bool = False,
    ):
        self._qt_clipboard = qt_clipboard
        self._fallback = fallback
        self._process_events = process_events
        self._native_writer = native_writer
        self._native_reader = native_reader
        self._prefer_native = prefer_native

    # ------------------------------------------------------------------
    # Clipboard access
    # ------------------------------------------------------------------

    def _qt(self) -> Any | None:
        """Return the Qt clipboard object, resolving it lazily once."""
        if self._qt_clipboard is _LAZY:
            try:
                from PySide6.QtGui import QGuiApplication

                self._qt_clipboard = QGuiApplication.clipboard()
            except Exception as exc:  # noqa: BLE001
                logger.debug("QGuiApplication.clipboard() unavailable: %s", exc)
                self._qt_clipboard = None
        return self._qt_clipboard

    def _flush(self) -> None:
        """Let the event loop process the clipboard write (X11 handoff)."""
        if self._process_events is not None:
            self._process_events()
            return
        try:
            from PySide6.QtCore import QCoreApplication

            QCoreApplication.processEvents()
        except Exception as exc:  # noqa: BLE001
            logger.debug("processEvents failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def copy_text(self, text: str) -> bool:
        """Copy *text* to the system clipboard.

        Returns ``True`` only when the write is verified against the real
        system clipboard (native read-back) or a fallback succeeded.
        """
        content = str(text)
        if self._prefer_native:
            if self._native_write(content):
                return self._verify_system(content)
            return self._copy_qt(content)
        return self._copy_qt(content)

    def read_text(self) -> str | None:
        """Return the current clipboard content, or ``None`` on failure."""
        qt = self._qt()
        if qt is not None:
            try:
                return qt.text()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Qt clipboard read failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Native write (system-truth verification)
    # ------------------------------------------------------------------

    def _native_write(self, text: str) -> bool:
        """Write via native tools (``wl-copy`` on Wayland).

        Returns ``True`` only when a native tool took the write — the
        strongest signal available that the compositor owns the content.
        """
        writer = self._native_writer or _resolve_native_writer()
        if writer is None:
            return False
        try:
            return bool(writer(text))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Native clipboard write raised: %s", exc)
            return False

    def _verify_system(self, content: str) -> bool:
        """Confirm *content* is readable from the real system clipboard.

        Reads back with the native reader (e.g. ``wl-paste``) rather than
        Qt's cached read-back, which can report success while the compositor
        never received the data (X11/Wayland handoff races).  Retries absorb
        the window between ``wl-copy``'s parent exiting and the forked child
        registering the selection (measured at ~0.17s).
        """
        reader = self._native_reader or _resolve_native_reader()
        if reader is None:
            return False
        for _ in range(10):
            try:
                current = reader()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Native clipboard read-back failed: %s", exc)
                return False
            # wl-paste / xclip appends a trailing newline (terminal convention);
            # strip it from both sides so exact comparison survives.
            if current is not None and normalize_newlines(current).rstrip(
                "\r\n"
            ) == normalize_newlines(content).rstrip("\r\n"):
                return True
            time.sleep(0.05)
        logger.warning(
            "Native clipboard write unverified after retries; reporting failure "
            "without running Qt (Qt's X11 write can replace the working "
            "Wayland selection with an unpublishable one)"
        )
        return False

    # ------------------------------------------------------------------
    # Qt path
    # ------------------------------------------------------------------

    def _copy_qt(self, content: str) -> bool:
        """Write via Qt ``QClipboard`` with read-back verification, then the
        injected/platform fallback."""
        qt = self._qt()
        if qt is not None:
            for attempt in (1, 2):
                try:
                    qt.setText(content)
                    if sys.platform == "linux" and hasattr(qt, "setText"):
                        try:
                            from PySide6.QtGui import QClipboard

                            qt.setText(content, QClipboard.Mode.Selection)
                        except Exception:  # noqa: BLE001
                            pass
                    self._flush()
                    if normalize_newlines(qt.text()).rstrip("\r\n") == normalize_newlines(
                        content
                    ).rstrip("\r\n"):
                        # On Linux when Qt path is taken, also sync via fallback best-effort
                        if sys.platform == "linux":
                            self._fallback_write(content)
                        return True
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Qt clipboard write failed (attempt %d): %s", attempt, exc)
                    break
            logger.warning(
                "Qt clipboard write unverified (%d chars); trying native fallback",
                len(content),
            )
        return self._fallback_write(content)

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_write(self, text: str) -> bool:
        """Write via an injected fallback or the platform native tools."""
        if self._fallback is not None:
            try:
                return bool(self._fallback(text))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Injected clipboard fallback failed: %s", exc)
                return False
        if sys.platform == "linux":
            try:
                from skill_manager.utils.linux import set_clipboard

                return bool(set_clipboard(text))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Linux native clipboard fallback failed: %s", exc)
                return False
        return False
