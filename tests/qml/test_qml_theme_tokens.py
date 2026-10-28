"""Design-token drift guard.

Every ``Theme.<name>`` reference in QML must resolve to a property (or
function) declared in ``Theme.qml``.  Unresolved tokens fail silently at
runtime — Qt logs a binding TypeError and the control falls back to a default
colour — which is how ``Theme.info``, ``Theme.tertiaryLabel`` and
``Theme.sizeSubtext`` shipped broken.  This test makes that class of bug loud.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_THEME_REFERENCE = re.compile(r"\bTheme\.([A-Za-z_]\w*)")
_DECLARATION = re.compile(
    r"^\s*(?:readonly\s+)?property\s+[\w.]+\s+([A-Za-z_]\w*)|^\s*function\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)


def _strip_comments(text: str) -> str:
    without_block = _BLOCK_COMMENT.sub("", text)
    return _LINE_COMMENT.sub("", without_block)


def _declared_tokens() -> set[str]:
    theme = (QML_DIR / "Theme.qml").read_text(encoding="utf-8")
    tokens: set[str] = set()
    for prop, func in _DECLARATION.findall(theme):
        tokens.add(prop or func)
    return tokens


def _qml_files() -> list[Path]:
    return sorted(p for p in QML_DIR.rglob("*.qml") if p.name != "Theme.qml")


def test_theme_declares_expected_core_tokens():
    """Sanity-check the parser so a broken regex cannot mask a real drift."""
    tokens = _declared_tokens()

    for token in ("darkMode", "glassPill", "radiusCard", "sizeBody", "alpha"):
        assert token in tokens


@pytest.mark.parametrize("qml_file", _qml_files(), ids=lambda p: p.name)
def test_theme_references_resolve(qml_file: Path):
    """A reference to a token Theme does not declare is a latent UI bug."""
    declared = _declared_tokens()
    used = set(_THEME_REFERENCE.findall(_strip_comments(qml_file.read_text(encoding="utf-8"))))
    unknown = sorted(used - declared)

    assert not unknown, (
        f"{qml_file.name} references undeclared Theme token(s): {unknown}. "
        "Add them to Theme.qml or use an existing semantic token."
    )


def test_previously_broken_tokens_are_declared():
    """Regression pin for the three tokens that shipped without declarations."""
    declared = _declared_tokens()

    assert "info" in declared, "Theme.info is used by DiagnosticsPane"
    assert "tertiaryLabel" in declared, "Theme.tertiaryLabel is used by InspectorEmptyState"
    assert "sizeSubtext" in declared, "Theme.sizeSubtext is used by InspectorEmptyState"
