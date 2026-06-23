"""Tests for the pure keymap conversion module.

These are pure-function tests with no fixtures, no Qt, and no pynput.
They run instantly and have zero side effects.
"""

import pytest

from skill_manager.core.keymap import qt_sequence_to_pynput_keys


class TestStandardModifierMappings:
    """The core Qt-to-pynput mapping table — must match pynput's syntax."""

    @pytest.mark.parametrize(
        "qt_input,expected",
        [
            ("Ctrl", "<ctrl>"),
            ("Shift", "<shift>"),
            ("Alt", "<alt>"),
            ("Meta", "<cmd>"),  # Qt "Meta" → pynput "<cmd>" (Windows key)
        ],
    )
    def test_modifiers(self, qt_input, expected):
        assert qt_sequence_to_pynput_keys(qt_input) == expected

    @pytest.mark.parametrize(
        "qt_input,expected",
        [
            ("Return", "<enter>"),
            ("Escape", "<esc>"),
            ("Space", "<space>"),
            ("Tab", "<tab>"),
            ("Backspace", "<backspace>"),
            ("Delete", "<delete>"),
            ("Insert", "<insert>"),
        ],
    )
    def test_named_keys(self, qt_input, expected):
        assert qt_sequence_to_pynput_keys(qt_input) == expected

    @pytest.mark.parametrize(
        "qt_input,expected",
        [
            ("Up", "<up>"),
            ("Down", "<down>"),
            ("Left", "<left>"),
            ("Right", "<right>"),
            ("Home", "<home>"),
            ("End", "<end>"),
            ("PageUp", "<page_up>"),
            ("PageDown", "<page_down>"),
        ],
    )
    def test_navigation_keys(self, qt_input, expected):
        assert qt_sequence_to_pynput_keys(qt_input) == expected


class TestCombinations:
    """Multi-key sequences — pynput uses '+' as separator."""

    def test_two_modifiers_plus_letter(self):
        assert qt_sequence_to_pynput_keys("Ctrl+Shift+S") == "<ctrl>+<shift>+s"

    def test_three_modifiers_plus_letter(self):
        assert qt_sequence_to_pynput_keys("Ctrl+Alt+Shift+H") == "<ctrl>+<alt>+<shift>+h"

    def test_meta_replacement_in_combination(self):
        # Critical: Meta must become <cmd>, not stay as 'meta'
        assert qt_sequence_to_pynput_keys("Meta+Shift+S") == "<cmd>+<shift>+s"


class TestEdgeCases:
    """Boundary conditions the function must handle gracefully."""

    def test_empty_string_returns_empty(self):
        assert qt_sequence_to_pynput_keys("") == ""

    def test_none_returns_empty(self):
        # None is falsy → hits early return before split()
        assert qt_sequence_to_pynput_keys(None) == ""  # type: ignore[arg-type]

    def test_case_insensitive(self):
        assert qt_sequence_to_pynput_keys("CTRL+SHIFT+S") == "<ctrl>+<shift>+s"
        assert qt_sequence_to_pynput_keys("ctrl+shift+s") == "<ctrl>+<shift>+s"

    def test_whitespace_in_parts_stripped(self):
        assert qt_sequence_to_pynput_keys(" Ctrl + Shift + S ") == "<ctrl>+<shift>+s"

    def test_unknown_key_passes_through_lowercased(self):
        # F12, F1, F2 etc. are not in the mapping — pass through
        assert qt_sequence_to_pynput_keys("F12") == "f12"
        assert qt_sequence_to_pynput_keys("Print") == "print"

    def test_single_letter_passes_through(self):
        assert qt_sequence_to_pynput_keys("A") == "a"
        assert qt_sequence_to_pynput_keys("S") == "s"
