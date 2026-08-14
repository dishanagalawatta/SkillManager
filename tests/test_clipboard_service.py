"""Unit tests for ClipboardService — verified writes + native fallback."""

import sys

import pytest

from skill_manager.utils.clipboard_service import ClipboardService, normalize_newlines


class FakeClipboard:
    """Minimal QClipboard stand-in with failure injection."""

    def __init__(
        self,
        stored: str = "",
        fail_set: bool = False,
        fail_get: bool = False,
        mangle_newlines: bool = False,
    ):
        self._stored = stored
        self.fail_set = fail_set
        self.fail_get = fail_get
        self.mangle_newlines = mangle_newlines
        self.set_calls: list[str] = []

    def setText(self, text: str) -> None:  # noqa: N802 - mirrors QClipboard API
        self.set_calls.append(text)
        if self.fail_set:
            raise RuntimeError("clipboard set failed")
        self._stored = text.replace("\n", "\r\n") if self.mangle_newlines else text

    def text(self) -> str:
        if self.fail_get:
            raise RuntimeError("clipboard get failed")
        return self._stored


@pytest.fixture
def qt_clipboard():
    return FakeClipboard()


@pytest.fixture
def fallback_spy():
    calls = []

    def _fallback(text: str) -> bool:
        calls.append(text)
        return True

    _fallback.calls = calls  # type: ignore[attr-defined]
    return _fallback


def test_normalize_newlines_crlf_and_cr():
    assert normalize_newlines("a\r\nb\rc") == "a\nb\nc"
    assert normalize_newlines("plain") == "plain"


def test_copy_text_success_via_qt(qt_clipboard):
    service = ClipboardService(qt_clipboard=qt_clipboard, fallback=None)
    assert service.copy_text("hello") is True
    assert qt_clipboard.set_calls == ["hello"]
    assert qt_clipboard.text() == "hello"


def test_copy_text_empty_string_succeeds(qt_clipboard):
    service = ClipboardService(qt_clipboard=qt_clipboard)
    assert service.copy_text("") is True


def test_copy_text_coerces_non_str(qt_clipboard):
    service = ClipboardService(qt_clipboard=qt_clipboard)
    assert service.copy_text(12345) is True
    assert qt_clipboard.text() == "12345"


def test_copy_text_newline_mangling_still_verifies():
    # X11-style CRLF mangle on write must not trigger the fallback.
    qt = FakeClipboard(mangle_newlines=True)
    service = ClipboardService(qt_clipboard=qt)
    assert service.copy_text("line1\nline2") is True
    assert qt.set_calls == ["line1\nline2"]


def test_copy_text_qt_set_failure_falls_back(qt_clipboard, fallback_spy):
    qt_clipboard.fail_set = True
    service = ClipboardService(qt_clipboard=qt_clipboard, fallback=fallback_spy)
    assert service.copy_text("payload") is True
    assert fallback_spy.calls == ["payload"]


def test_copy_text_verification_mismatch_retries_then_falls_back(fallback_spy):
    # Clipboard silently stores a mangled value (never matches) -> retry -> fallback.
    class MangleAlways(FakeClipboard):
        def setText(self, text: str) -> None:  # noqa: N802 - mirrors QClipboard API
            self.set_calls.append(text)
            self._stored = "!!!corrupted!!!"

    qt = MangleAlways()
    service = ClipboardService(qt_clipboard=qt, fallback=fallback_spy)
    assert service.copy_text("data") is True
    assert len(qt.set_calls) == 2  # initial attempt + one retry
    assert fallback_spy.calls == ["data"]


def test_copy_text_all_paths_fail_returns_false(qt_clipboard):
    qt_clipboard.fail_set = True
    service = ClipboardService(qt_clipboard=qt_clipboard, fallback=lambda _t: False)
    assert service.copy_text("data") is False


def test_copy_text_explicit_none_qt_uses_fallback_directly(fallback_spy):
    service = ClipboardService(qt_clipboard=None, fallback=fallback_spy)
    assert service.copy_text("data") is True
    assert fallback_spy.calls == ["data"]


def test_copy_text_no_qt_fallback_false_returns_false():
    service = ClipboardService(qt_clipboard=None, fallback=lambda _t: False)
    assert service.copy_text("data") is False


@pytest.mark.skipif(sys.platform == "win32", reason="Linux specific fallback logic")
def test_copy_text_no_qt_linux_native_fallback_delegates():
    # With no injected fallback, Linux path must delegate to utils.linux.set_clipboard.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("skill_manager.utils.linux.set_clipboard", lambda _t: True)
        service = ClipboardService(qt_clipboard=None, fallback=None)
        assert service.copy_text("data") is True


def test_read_text_returns_stored(qt_clipboard):
    qt_clipboard.setText("stored-value")
    service = ClipboardService(qt_clipboard=qt_clipboard)
    assert service.read_text() == "stored-value"


def test_read_text_none_qt_returns_none():
    service = ClipboardService(qt_clipboard=None)
    assert service.read_text() is None


def test_process_events_hook_is_invoked(qt_clipboard):
    flushed = []

    def _flush():
        flushed.append(True)

    service = ClipboardService(qt_clipboard=qt_clipboard, process_events=_flush)
    assert service.copy_text("data") is True
    assert flushed == [True]


def test_fallback_exception_is_swallowed(qt_clipboard):
    def _boom(_text: str) -> bool:
        raise RuntimeError("native tool crashed")

    service = ClipboardService(qt_clipboard=qt_clipboard, fallback=_boom)
    # Qt path succeeds, so fallback never runs — force failure first.
    qt_clipboard.fail_set = True
    assert service.copy_text("data") is False


# ---------------------------------------------------------------------------
# Native-first path (prefer_native=True)
# ---------------------------------------------------------------------------


def test_copy_text_prefer_native_writes_and_verifies_system_clipboard(qt_clipboard):
    written: list[str] = []
    system_clipboard: list[str] = []

    def _writer(text: str) -> bool:
        written.append(text)
        system_clipboard.append(text)
        return True

    def _reader() -> str | None:
        return system_clipboard[-1] if system_clipboard else None

    service = ClipboardService(
        qt_clipboard=qt_clipboard,
        native_writer=_writer,
        native_reader=_reader,
        prefer_native=True,
    )
    assert service.copy_text("hello") is True
    assert written == ["hello"]
    assert qt_clipboard.set_calls == []


def test_copy_text_prefer_native_unverified_skips_qt_and_reports_false(qt_clipboard):
    # Native write landed but the system clipboard never confirms it.
    # Must NOT report success (the old Qt-cache false positive), and must
    # NOT run Qt: Qt's X11 write can replace the working Wayland selection
    # with an unpublishable one, breaking the paste the native write already
    # made possible.
    def _writer(_text: str) -> bool:
        return True

    def _reader() -> str | None:
        return "!!!stale!!!"

    service = ClipboardService(
        qt_clipboard=qt_clipboard,
        fallback=lambda _t: True,
        native_writer=_writer,
        native_reader=_reader,
        prefer_native=True,
    )
    assert service.copy_text("data") is False
    assert qt_clipboard.set_calls == []


def test_copy_text_prefer_native_writer_raises_falls_back_to_qt(qt_clipboard):
    def _boom(_text: str) -> bool:
        raise RuntimeError("wl-copy crashed")

    service = ClipboardService(qt_clipboard=qt_clipboard, native_writer=_boom, prefer_native=True)
    assert service.copy_text("data") is True
    assert qt_clipboard.set_calls == ["data"]


def test_copy_text_prefer_native_writer_unavailable_uses_qt(qt_clipboard):
    def _no_tool(_text: str) -> bool:
        return False  # wl-copy and pyperclip both unavailable

    service = ClipboardService(
        qt_clipboard=qt_clipboard, native_writer=_no_tool, prefer_native=True
    )
    assert service.copy_text("data") is True
    assert qt_clipboard.set_calls == ["data"]


def test_copy_text_prefer_native_unconfirmed_returns_false(qt_clipboard):
    def _writer(_text: str) -> bool:
        return True

    def _reader() -> str | None:
        return None

    qt_clipboard.fail_set = True
    service = ClipboardService(
        qt_clipboard=qt_clipboard,
        fallback=lambda _t: True,
        native_writer=_writer,
        native_reader=_reader,
        prefer_native=True,
    )
    assert service.copy_text("data") is False
    assert qt_clipboard.set_calls == []


def test_copy_text_prefer_native_reader_trailing_newline_still_verifies(qt_clipboard):
    def _writer(text: str) -> bool:
        return True

    def _reader() -> str | None:
        return "data\n"

    service = ClipboardService(
        qt_clipboard=qt_clipboard,
        native_writer=_writer,
        native_reader=_reader,
        prefer_native=True,
    )
    assert service.copy_text("data") is True
    assert qt_clipboard.set_calls == []


def test_copy_text_default_prefer_native_off_skips_native(qt_clipboard):
    # Regression guard: without prefer_native the native writer must never
    # run — tests and headless processes must not touch the real clipboard.
    def _writer(_text: str) -> bool:
        raise AssertionError("native writer must not run without prefer_native")

    service = ClipboardService(qt_clipboard=qt_clipboard, native_writer=_writer)
    assert service.copy_text("data") is True
    assert qt_clipboard.set_calls == ["data"]
