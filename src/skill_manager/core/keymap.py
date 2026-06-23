"""Pure key-sequence conversion utilities.

Maps Qt-style key sequence strings to pynput's expected format.
Pure: no Qt runtime objects, no pynput, no side effects, no I/O.

The input is the format Qt produces from QKeySequence.toString(),
e.g. "Ctrl+Shift+S". The output is pynput's GlobalHotKeys format,
e.g. "<ctrl>+<shift>+s".
"""

from __future__ import annotations

_QT_TO_PYNPUT: dict[str, str] = {
    "ctrl": "<ctrl>",
    "shift": "<shift>",
    "alt": "<alt>",
    "meta": "<cmd>",
    "return": "<enter>",
    "escape": "<esc>",
    "space": "<space>",
    "tab": "<tab>",
    "backspace": "<backspace>",
    "delete": "<delete>",
    "insert": "<insert>",
    "up": "<up>",
    "down": "<down>",
    "left": "<left>",
    "right": "<right>",
    "home": "<home>",
    "end": "<end>",
    "pageup": "<page_up>",
    "pagedown": "<page_down>",
}


def qt_sequence_to_pynput_keys(sequence: str) -> str:
    """Convert a Qt-style key sequence string to pynput format.

    Examples:
        >>> qt_sequence_to_pynput_keys("Ctrl+Shift+S")
        '<ctrl>+<shift>+s'
        >>> qt_sequence_to_pynput_keys("Meta+Shift+S")
        '<cmd>+<shift>+s'
        >>> qt_sequence_to_pynput_keys("F12")
        'f12'
        >>> qt_sequence_to_pynput_keys("")
        ''

    Args:
        sequence: Qt-style key sequence (e.g., "Ctrl+Shift+S").
                  Empty string returns empty string.

    Returns:
        pynput-format key sequence (e.g., "<ctrl>+<shift>+s").
    """
    if not sequence:
        return ""
    return "+".join(
        _QT_TO_PYNPUT.get(part.lower().strip(), part.lower().strip())
        for part in sequence.split("+")
    )
