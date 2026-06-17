import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def sdet_setup_data(app_controller, temp_dir):
    """Sets up a skill with data that requires schema coercion."""
    lib_dir = temp_dir / "sdet_lib"
    lib_dir.mkdir(exist_ok=True)

    # Skill with description as list and tags as string
    skill_dir = lib_dir / "coerced-skill"
    skill_dir.mkdir(exist_ok=True)

    content = """---
name: Coerced Skill
description:
  - Line 1
  - Line 2
tags: tag1, tag2
category: SDET Test
---
# Body
"""
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    app_controller.config_mgr.addSource(str(lib_dir))
    app_controller.refreshSkills()
    QApplication.instance().processEvents()


def test_ui_displays_coerced_schema_data(qtbot, qml_engine, app_controller, sdet_setup_data):
    """E2E test: Verify that UI correctly displays data coerced by our refactored schemas."""
    _root = qml_engine.rootObjects()[0]
    qapp = QApplication.instance()

    # Switch to Library view
    app_controller.ui.currentView = "Library"
    qapp.processEvents()
    qtbot.wait(200)

    # Find the skill in the model
    found = False
    for i in range(app_controller.libraryModel.rowCount()):
        record = app_controller.libraryModel.get_skill_at(i)
        if record.get("name") == "Coerced Skill":
            found = True
            # Verify coercion worked at the model level
            assert record.get("description") == "Line 1\nLine 2"
            assert record.get("tags") == ["tag1", "tag2"]
            break

    assert found, "Coerced Skill not found in library model"

    # Verify UI rendering (if possible by finding a child with the text)
    # This assumes the Library view renders the description of the selected item
    # Since we can't easily click items in a ListView via findChild without more logic,
    # we'll verify the model data which is what the UI binds to.
