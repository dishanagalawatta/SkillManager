"""Contract tests: inspector text areas must not clip content.

Verifies that all TextEdit/TextArea elements in the inspector panels
use WrapAnywhere and proper width constraints to prevent text overflow.
"""

from pathlib import Path

QML_DIR: Path = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


# ── SkillInspector ────────────────────────────────────────────────


def test_skill_inspector_description_uses_wrap_anywhere() -> None:
    """descriptionEdit must use TextEdit.Wrap or WrapAtWordBoundaryOrAnywhere."""
    qml = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: descriptionEdit")
    assert idx >= 0, "descriptionEdit not found in SkillInspector.qml"
    chunk = qml[idx : idx + 600]
    assert "wrapMode: TextEdit.Wrap" in chunk or "wrapMode: TextEdit.WrapAnywhere" in chunk, (
        "descriptionEdit must use Wrap or WrapAnywhere, found: "
        + repr(chunk[chunk.find("wrapMode") : chunk.find("wrapMode") + 50])
    )


def test_skill_inspector_description_has_width_debug_logging() -> None:
    """descriptionEdit must have onWidthChanged debug logging."""
    qml = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: descriptionEdit")
    assert idx >= 0, "descriptionEdit not found in SkillInspector.qml"
    chunk = qml[idx : idx + 1200]
    assert "onWidthChanged" in chunk, "descriptionEdit missing onWidthChanged debug logging"


def test_skill_inspector_raw_content_uses_wrap_anywhere() -> None:
    """rawContentArea must use TextEdit.WrapAnywhere to break long unbroken strings."""
    qml = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: rawContentArea")
    assert idx >= 0, "rawContentArea not found in SkillInspector.qml"
    chunk = qml[idx : idx + 1200]
    assert "wrapMode: TextEdit.WrapAnywhere" in chunk, (
        "rawContentArea must use WrapAnywhere, found: "
        + repr(chunk[chunk.find("wrapMode") : chunk.find("wrapMode") + 50])
    )


def test_skill_inspector_raw_content_uses_available_width() -> None:
    """rawContentArea must use rawContentScroll.availableWidth for width bound."""
    qml = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: rawContentArea")
    assert idx >= 0, "rawContentArea not found in SkillInspector.qml"
    chunk = qml[idx : idx + 500]
    assert "width: rawContentScroll.availableWidth" in chunk, (
        "rawContentArea width must use rawContentScroll.availableWidth, "
        "not parent.width - leftPadding - rightPadding"
    )


def test_skill_inspector_raw_content_no_old_width_binding() -> None:
    """rawContentArea must NOT use the old parent.width - padding pattern."""
    qml = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: rawContentArea")
    assert idx >= 0, "rawContentArea not found in SkillInspector.qml"
    chunk = qml[idx : idx + 400]
    # The old pattern was: width: rawContentScroll.width - rawContentScroll.leftPadding - rawContentScroll.rightPadding
    assert "parent.width - parent.leftPadding" not in chunk, (
        "rawContentArea must not use parent.width - padding pattern"
    )
    assert "rawContentScroll.width - rawContentScroll" not in chunk, (
        "rawContentArea must not use rawContentScroll.width - padding pattern"
    )


# ── CommandInspector ─────────────────────────────────────────────


def test_command_inspector_body_uses_wrap_anywhere() -> None:
    """bodyArea must use TextEdit.WrapAnywhere to break long unbroken strings."""
    qml = (QML_DIR / "CommandInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: bodyArea")
    assert idx >= 0, "bodyArea not found in CommandInspector.qml"
    chunk = qml[idx : idx + 1600]
    assert "wrapMode: TextEdit.WrapAnywhere" in chunk, (
        "bodyArea must use WrapAnywhere, found: "
        + repr(chunk[chunk.find("wrapMode") : chunk.find("wrapMode") + 50])
    )


def test_command_inspector_body_uses_available_width() -> None:
    """bodyArea must use bodyScroll.availableWidth for width bound."""
    qml = (QML_DIR / "CommandInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: bodyArea")
    assert idx >= 0, "bodyArea not found in CommandInspector.qml"
    chunk = qml[idx : idx + 400]
    assert "width: bodyScroll.availableWidth" in chunk, (
        "bodyArea width must use bodyScroll.availableWidth, "
        "not parent.width - leftPadding - rightPadding"
    )


def test_command_inspector_body_has_scrollview_id() -> None:
    """CommandInspector must have a bodyScroll id for availableWidth reference."""
    qml = (QML_DIR / "CommandInspector.qml").read_text(encoding="utf-8")
    assert "id: bodyScroll" in qml, (
        "CommandInspector must declare id: bodyScroll on the SmoothScrollView"
    )


def test_command_inspector_body_no_old_width_binding() -> None:
    """bodyArea must NOT use the old parent.width - padding pattern."""
    qml = (QML_DIR / "CommandInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: bodyArea")
    assert idx >= 0, "bodyArea not found in CommandInspector.qml"
    chunk = qml[idx : idx + 400]
    assert "parent.width - parent.leftPadding" not in chunk, (
        "bodyArea must not use parent.width - padding pattern"
    )


# ── General ──────────────────────────────────────────────────────


def test_no_text_wrap_usage_in_inspectors() -> None:
    """Inspectors must use valid wrap modes for text areas."""
    for fname in ("SkillInspector.qml", "CommandInspector.qml"):
        qml = (QML_DIR / fname).read_text(encoding="utf-8")
        for line in qml.splitlines():
            stripped = line.strip()
            if "wrapMode:" in stripped:
                assert (
                    "TextEdit.Wrap" in stripped
                    or "TextEdit.WrapAnywhere" in stripped
                    or "WrapAtWordBoundaryOrAnywhere" in stripped
                ), f"{fname}: unexpected wrapMode at:\n  {line}"


def test_skill_inspector_description_has_preferred_height_binding() -> None:
    """descriptionEdit must use Layout.preferredHeight: contentHeight, not implicitHeight."""
    qml = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    idx = qml.find("id: descriptionEdit")
    assert idx >= 0, "descriptionEdit not found in SkillInspector.qml"
    chunk = qml[idx : idx + 400]
    assert "Layout.preferredHeight: contentHeight" in chunk, (
        "descriptionEdit must set Layout.preferredHeight: contentHeight + topPadding + bottomPadding "
        "to override the stale implicitHeight (which is based on unwrapped implicitWidth)"
    )


def test_no_contentx_usage_in_inspectors() -> None:
    """Neither inspector should reference contentX (does not exist in Qt 6.11+)."""
    for fname in ("SkillInspector.qml", "CommandInspector.qml"):
        qml = (QML_DIR / fname).read_text(encoding="utf-8")
        assert "contentX" not in qml, (
            f"{fname}: contentX is not a valid property in Qt 6.11+ "
            "(TextEdit/TextArea are not Flickable). Remove all references."
        )
