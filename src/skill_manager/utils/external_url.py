"""
Purpose: Open an external URL in the user's browser without inheriting the
packaged runtime's ``LD_LIBRARY_PATH``.

Why this exists
---------------
``QDesktopServices.openUrl`` delegates to ``xdg-open`` on Linux. On GNOME that
script runs ``gio open``. A PyInstaller onedir/AppImage process exports
``LD_LIBRARY_PATH`` pointing at its bundled libraries, so the host ``gio``
binary resolves the wrong ``libgio`` and dies with::

    gio: symbol lookup error: undefined symbol: g_unix_mount_entry_get_options

The launcher process was started successfully, so ``openUrl`` returns ``True``
and no error is surfaced — the "View Release" button silently does nothing.
This module launches the host helper itself with the environment repaired by
:func:`skill_manager.utils.linux.get_clean_env` (see ADR-0024) and reports a
real result instead of trusting the spawn.

The module is Qt-free so it can run on a background task runner.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from urllib.parse import urlparse

from skill_manager.utils.linux import find_system_binary, get_clean_env

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = frozenset({"https", "http"})
_LINUX_OPENERS = ("gio", "xdg-open", "kde-open5", "sensible-browser")
# Total budget for the whole opener chain, not per candidate: this runs on the
# GUI thread when a button is clicked, so a slow/dangling opener must not
# freeze the window.
_OPEN_TIMEOUT_SECONDS = 3.0


def is_safe_external_url(url: str) -> bool:
    """Only allow absolute web URLs with a scheme we can hand to a browser.

    Rejects empty strings, relative paths, ``file:``/``javascript:`` URLs and
    values that begin with ``-`` (argument injection into the opener).
    """
    if not url or url.lstrip().startswith("-"):
        return False
    parsed = urlparse(url)
    return parsed.scheme.lower() in _ALLOWED_SCHEMES and bool(parsed.netloc)


def _open_linux(url: str) -> tuple[bool, str]:
    env = get_clean_env()
    errors: list[str] = []
    deadline = time.monotonic() + _OPEN_TIMEOUT_SECONDS
    for name in _LINUX_OPENERS:
        binary = find_system_binary(name)
        if not binary:
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0.2:
            errors.append(f"{name}: opener chain timed out")
            break
        argv = [binary, "open", url] if name == "gio" else [binary, url]
        try:
            proc = subprocess.run(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=remaining,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            errors.append(f"{name}: timed out after {remaining:.1f}s")
            break
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{name}: {exc}")
            continue
        if proc.returncode == 0:
            logger.info("Opened external URL via %s", name)
            return True, ""
        stderr = ""
        if proc.stderr:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()[-300:]
        errors.append(f"{name} exited {proc.returncode}{': ' + stderr if stderr else ''}")

    if not errors:
        return False, "No URL opener found (install xdg-utils or gio)"
    logger.warning("Could not open external URL: %s", "; ".join(errors))
    return False, "; ".join(errors)


def open_external_url(url: str) -> tuple[bool, str]:
    """Open *url* in the platform browser.

    Returns:
        ``(True, "")`` when a launcher accepted the URL, otherwise
        ``(False, reason)``. Callers that run on a worker thread may fall back
        to ``QDesktopServices`` on the UI thread when this returns ``False``.
    """
    if not is_safe_external_url(url):
        return False, "Refusing to open an unsafe URL"

    if sys.platform.startswith("linux"):
        return _open_linux(url)

    try:
        if sys.platform == "win32":
            os.startfile(url)  # type: ignore[attr-defined]  # noqa: S606 - browser URL
        elif sys.platform == "darwin":
            subprocess.run(
                ["open", "--", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_OPEN_TIMEOUT_SECONDS,
                check=True,
            )
        else:
            return False, f"Unsupported platform: {sys.platform}"
    except Exception as exc:  # noqa: BLE001 - reported to the UI
        logger.warning("Could not open external URL: %s", exc)
        return False, str(exc)
    return True, ""
