"""QML contract test: CustomTitleBar sun/moon toggle must use the Python setter.

The sun/moon button in the title bar must write to
``AppController.ui_controller.darkMode`` (which fires darkModeChanged,
triggers DWM re-apply, and persists) rather than writing directly to the
QML ``Theme.darkMode`` singleton (which only affects QML-side tokens).
"""

from __future__ import annotations

from pathlib import Path

import pytest

QML_FILE = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
    / "CustomTitleBar.qml"
)


class TestTitleBarToggleUsesPythonSetter:
    def test_sun_moon_button_writes_appcontroller(self) -> None:
        """onClicked must reference AppController.ui_controller.darkMode."""
        content = QML_FILE.read_text(encoding="utf-8")
        assert "AppController.ui_controller.darkMode" in content, (
            "CustomTitleBar.qml must use AppController.ui_controller.darkMode "
            "for the theme toggle, not Theme.darkMode"
        )

    def test_sun_moon_button_does_not_bypass_python(self) -> None:
        """onClicked must NOT write directly to Theme.darkMode."""
        lines = QML_FILE.read_text(encoding="utf-8").splitlines()
        # Find lines containing "onClicked" near a Theme.darkMode reference
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("onClicked:") and "Theme.darkMode" in stripped:
                pytest.fail(
                    f"Line {i + 1}: onClicked writes to Theme.darkMode directly "
                    f"(bypasses Python setter): {stripped}"
                )
