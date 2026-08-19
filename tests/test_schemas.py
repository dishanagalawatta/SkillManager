import pytest
from PySide6.QtWidgets import QApplication

from skill_manager.core.schemas import (
    AppConfig,
    CacheState,
    PackageConfig,
    SkillMetadata,
    SkillRecord,
)


class TestSkillMetadata:
    def test_metadata_coerces_tags_from_string(self):
        meta = SkillMetadata.model_validate({"tags": "tag1, tag2 , tag3"})
        assert meta.tags == ["tag1", "tag2", "tag3"]

    def test_metadata_coerces_tags_from_list(self):
        meta = SkillMetadata.model_validate({"tags": ["a", 1, None, "b"]})
        assert meta.tags == ["a", "1", "b"]

    def test_metadata_handles_none_tags(self):
        meta = SkillMetadata.model_validate({"tags": None})
        assert meta.tags == []

    def test_metadata_coerces_description_from_list(self):
        meta = SkillMetadata.model_validate({"description": ["line 1", "line 2"]})
        assert meta.description == "line 1\nline 2"

    def test_metadata_handles_none_description(self):
        meta = SkillMetadata.model_validate({"description": None})
        assert meta.description == ""

    def test_metadata_ignores_extra_fields(self):
        meta = SkillMetadata.model_validate({"name": "Test", "extra_junk": 123})
        dumped = meta.model_dump()
        assert "extra_junk" not in dumped
        assert dumped["name"] == "Test"


class TestSkillRecord:
    def test_record_coerces_none_to_string(self):
        record = SkillRecord.model_validate(
            {"name": "Valid", "category": None, "local_path": "/test"}
        )
        assert record.name == "Valid"
        assert record.category == ""

    def test_record_coerces_numbers_to_string(self):
        record = SkillRecord.model_validate({"name": 123, "category": 45.6, "local_path": "/test"})
        assert record.name == "123"
        assert record.category == "45.6"

    def test_record_ignores_extra_fields(self):
        record = SkillRecord.model_validate(
            {"name": "Record", "local_path": "/test", "internal_id": "ABC"}
        )
        assert "internal_id" not in record.model_dump()


class TestAppConfig:
    def test_from_legacy_migration(self):
        data = {
            "targets": ["project1"],
            "target_aliases": {"p1": "Project 1"},
            "show_menu_icons": False,
        }
        config = AppConfig.from_legacy(data)
        assert config.projects == ["project1"]
        assert config.project_aliases == {"p1": "Project 1"}
        assert config.show_menu_icons is False  # type: ignore[attr-defined]
        assert "targets" not in config.model_dump()

    def test_from_legacy_prefers_current_keys(self):
        data = {
            "targets": ["old"],
            "projects": ["new"],
            "target_aliases": {"o": "O"},
            "project_aliases": {"n": "N"},
        }
        config = AppConfig.from_legacy(data)
        assert config.projects == ["new"]
        assert config.project_aliases == {"n": "N"}

    def test_shortcuts_and_aliases_coerce_to_dict(self):
        config = AppConfig.model_validate({"shortcuts": None, "project_aliases": "invalid"})
        assert config.shortcuts == {}
        assert config.project_aliases == {}


class TestCacheState:
    def test_cache_state_recursive_validation(self):
        data = {
            "skills": [
                {"name": "Skill 1", "local_path": "/s1", "extra": "strip me"},
                {"name": "Skill 2", "local_path": "/s2", "category": "Tests"},
            ],
            "projects": [{"id": "p1"}],
        }
        cache = CacheState.model_validate(data)
        assert len(cache.skills) == 2
        assert isinstance(cache.skills[0], SkillRecord)
        assert cache.skills[0].name == "Skill 1"
        assert "extra" not in cache.skills[0].model_dump()
        assert cache.projects == [{"id": "p1"}]

    def test_cache_state_defaults(self):
        cache = CacheState.model_validate({})
        assert cache.skills == []
        assert cache.projects == []
        assert cache.status == ""


class TestPackageConfig:
    def test_package_config_defaults(self):
        pkg = PackageConfig.model_validate({"id": "my-pkg"})
        assert pkg.id == "my-pkg"
        assert pkg.enabled is True
        assert pkg.path == ""

    def test_package_config_ignores_extras(self):
        pkg = PackageConfig.model_validate({"id": "pkg", "foo": "bar"})
        assert "foo" not in pkg.model_dump()


# ── E2E schema coercion (merged from test_sdet_e2e_schemas.py) ──


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
    app_controller.refreshSkills("test", False)
    QApplication.instance().processEvents()  # type: ignore[union-attr]


def test_ui_displays_coerced_schema_data(qtbot, qml_engine, app_controller, sdet_setup_data):
    """E2E test: Verify that UI correctly displays data coerced by our refactored schemas."""
    _root = qml_engine.rootObjects()[0]
    qapp = QApplication.instance()

    # Switch to Library view
    app_controller.ui.currentView = "Library"
    assert qapp is not None
    qapp.processEvents()  # type: ignore[union-attr]
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
