"""QML contract tests for modal dialog positioning and Overlay parenting.

Verifies that all dialog components in SkillManagerComponents/dialogs/ as well as standalone
popup windows (EmojiPicker.qml, FontPickerDialog.qml) are parented to Overlay.overlay,
centered dynamically using anchors.centerIn: Overlay.overlay, and enforce responsive
width and height bounds based on Overlay.overlay.
"""

from pathlib import Path

COMPONENTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)
DIALOGS_DIR = COMPONENTS_DIR / "dialogs"


def test_command_create_dialog_overlay_contract():
    """CommandCreateDialog.qml must parent and center on Overlay.overlay with dynamic sizing."""
    dialog_file = DIALOGS_DIR / "CommandCreateDialog.qml"
    assert dialog_file.exists(), "CommandCreateDialog.qml must exist"

    content = dialog_file.read_text(encoding="utf-8")

    # Must specify parent: Overlay.overlay
    assert "parent: Overlay.overlay" in content, (
        "CommandCreateDialog.qml must specify 'parent: Overlay.overlay' to avoid relative positioning bugs"
    )

    # Must specify anchors.centerIn: Overlay.overlay
    assert "anchors.centerIn: Overlay.overlay" in content, (
        "CommandCreateDialog.qml must specify 'anchors.centerIn: Overlay.overlay' for dynamic window centering"
    )

    # Must not use fixed x/y parent calculations
    assert "x: (parent.width - width)" not in content, (
        "CommandCreateDialog.qml must not use relative 'x: (parent.width - width)' positioning"
    )


def test_standalone_popups_overlay_contract():
    """EmojiPicker.qml and FontPickerDialog.qml must center on Overlay.overlay with dynamic dimensions."""
    for filename in ("EmojiPicker.qml", "FontPickerDialog.qml"):
        popup_file = COMPONENTS_DIR / filename
        assert popup_file.exists(), f"{filename} must exist"

        content = popup_file.read_text(encoding="utf-8")

        assert "parent: Overlay.overlay" in content, (
            f"{filename} must specify 'parent: Overlay.overlay'"
        )
        assert "anchors.centerIn: Overlay.overlay" in content, (
            f"{filename} must specify 'anchors.centerIn: Overlay.overlay'"
        )
        assert "Math.min(" in content, f"{filename} must enforce dynamic bounds using Math.min("


def test_all_dialogs_overlay_parenting_contract():
    """All custom dialog QML files in dialogs/ must specify parent: Overlay.overlay or anchors.centerIn: Overlay.overlay."""
    qml_files = list(DIALOGS_DIR.glob("*.qml"))
    assert len(qml_files) > 0, "Dialogs directory must contain QML files"

    for qml_file in qml_files:
        if qml_file.name == "FolderPickerNative.qml":
            # Native folder dialog does not use Overlay
            continue

        content = qml_file.read_text(encoding="utf-8")

        assert (
            "parent: Overlay.overlay" in content or "anchors.centerIn: Overlay.overlay" in content
        ), (
            f"{qml_file.name} must set 'parent: Overlay.overlay' or 'anchors.centerIn: Overlay.overlay'"
        )

        assert "x: (parent.width - width)" not in content, (
            f"{qml_file.name} must not use fixed 'x: (parent.width - width)' relative to local parent"
        )
