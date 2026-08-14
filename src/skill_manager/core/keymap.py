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

# GTK accelerator syntax for the portal GlobalShortcuts backend
# (preferred_trigger): modifiers and named keys use angle-bracketed
# names, e.g. "<Control><Shift>S".
_QT_TO_GTK: dict[str, str] = {
    "ctrl": "<Control>",
    "shift": "<Shift>",
    "alt": "<Alt>",
    "meta": "<Super>",
    "return": "<Return>",
    "escape": "<Escape>",
    "space": "<Space>",
    "tab": "<Tab>",
    "backspace": "<BackSpace>",
    "delete": "<Delete>",
    "insert": "<Insert>",
    "up": "<Up>",
    "down": "<Down>",
    "left": "<Left>",
    "right": "<Right>",
    "home": "<Home>",
    "end": "<End>",
    "pageup": "<Page_Up>",
    "pagedown": "<Page_Down>",
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


def qt_sequence_to_gtk_accelerator(sequence: str) -> str:
    """Convert a Qt-style key sequence string to GTK accelerator format.

    GTK accelerators wrap modifiers in angle brackets and concatenate
    them with the key, e.g. "Ctrl+Shift+S" -> "<Control><Shift>S".
    This is the format the portal GlobalShortcuts backend expects for
    its ``preferred_trigger`` hint (GNOME may still open a dialog and
    let the user assign the trigger manually).

    Examples:
        >>> qt_sequence_to_gtk_accelerator("Ctrl+Shift+S")
        '<Control><Shift>S'
        >>> qt_sequence_to_gtk_accelerator("Meta+Shift+F12")
        '<Super><Shift>F12'
        >>> qt_sequence_to_gtk_accelerator("")
        ''

    Args:
        sequence: Qt-style key sequence (e.g., "Ctrl+Shift+S").
                  Empty string returns empty string.

    Returns:
        GTK accelerator string (e.g., "<Control><Shift>S").
    """
    if not sequence:
        return ""
    parts = [part.strip() for part in sequence.split("+")]
    mods = []
    key = None
    for part in parts:
        gtk_name = _QT_TO_GTK.get(part.lower())
        if gtk_name is None:
            key = part if len(part) != 1 or not part.isalpha() else part.upper()
        elif part.lower() in ("ctrl", "shift", "alt", "meta"):
            mods.append(gtk_name)
        else:
            key = gtk_name
    if key is None:
        return ""
    return "".join(mods) + key
