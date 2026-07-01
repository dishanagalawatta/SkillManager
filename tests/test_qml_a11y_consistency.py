"""Tests for QML accessibility consistency rules.

Validates that custom QML controls follow the a11y conventions established
by the project's Accessibility audit. Prevents known anti-patterns from
re-appearing as new components are added.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


def _parse_accessible_bindings(text: str) -> list[tuple[str, str]]:
    """Extract (property_name, value) pairs for Accessible.role, .name, .description."""
    results: list[tuple[str, str]] = []
    for m in re.finditer(r"Accessible\.(\w+):\s*(.+)", text):
        results.append((m.group(1), m.group(2).strip()))
    return results


def _find_redundant_descriptions(qml_path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, name_value, description_value) for any
    Accessible.description that is identical to Accessible.name on the same
    element (within a reasonable heuristic window).
    """
    text = qml_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    name_line = None
    name_value = None
    desc_line = None
    desc_value = None
    redundant: list[tuple[int, str, str]] = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if "Accessible.name:" in stripped:
            name_line = i
            # Extract the value after the colon
            name_value = stripped.split("Accessible.name:", 1)[1].strip()
        elif "Accessible.description:" in stripped:
            desc_line = i
            desc_value = stripped.split("Accessible.description:", 1)[1].strip()
            # Check if we saw an Accessible.name within the last 5 lines
            # and if the values are identical
            if (
                name_value is not None
                and name_line is not None
                and desc_line - name_line <= 5
                and name_value == desc_value
            ):
                redundant.append((desc_line, name_value, desc_value))

    return redundant


@pytest.mark.parametrize(
    "qml_file",
    sorted(QML_DIR.glob("*.qml")),
    ids=lambda p: p.stem,
)
def test_accessible_description_not_duplicate_of_name(qml_file: Path):
    """Accessible.description must not be the exact same string as
    Accessible.name on the same element.  When both are identical,
    screen readers announce the same text twice.

    If this test fails, either:
      - Remove the Accessible.description binding (if it adds no new information), or
      - Change the description value to provide genuinely distinct context.
    """
    redundant = _find_redundant_descriptions(qml_file)

    # Known instances that exist in the codebase and have NOT been fixed yet.
    # When an instance is fixed, remove it from this allow-list so the test
    # catches regressions on that specific component.
    # To find the component name, look at the Accessible.name or .description
    # line that is flagged and identify the parent component file.
    known_instances: dict[str, set[int]] = {
        # Format: "qml_stem": {line_numbers that are expected to be redundant}
        # Add entries here when intentionally deferring a fix.
    }

    unaccounted = [
        (line, n, d)
        for line, n, d in redundant
        if qml_file.stem not in known_instances or line not in known_instances[qml_file.stem]
    ]

    assert not unaccounted, (
        f"{qml_file.name} has Accessible.description identical to Accessible.name "
        f"on {len(unaccounted)} element(s):\n"
        + "\n".join(f"  line {line}: {n}" for line, n, _ in unaccounted)
        + "\nThis causes screen readers to announce the same text twice. "
        "Remove the redundant Accessible.description or change it to a distinct value."
    )
