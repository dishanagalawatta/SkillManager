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
        record = SkillRecord.model_validate({"name": "Valid", "category": None, "local_path": "/test"})
        assert record.name == "Valid"
        assert record.category == ""

    def test_record_coerces_numbers_to_string(self):
        record = SkillRecord.model_validate({"name": 123, "category": 45.6, "local_path": "/test"})
        assert record.name == "123"
        assert record.category == "45.6"

    def test_record_ignores_extra_fields(self):
        record = SkillRecord.model_validate({"name": "Record", "local_path": "/test", "internal_id": "ABC"})
        assert "internal_id" not in record.model_dump()


class TestAppConfig:
    def test_from_legacy_migration(self):
        data = {
            "targets": ["project1"],
            "target_aliases": {"p1": "Project 1"},
            "show_menu_icons": False
        }
        config = AppConfig.from_legacy(data)
        assert config.projects == ["project1"]
        assert config.project_aliases == {"p1": "Project 1"}
        assert config.show_menu_icons is False
        assert "targets" not in config.model_dump()

    def test_from_legacy_prefers_current_keys(self):
        data = {
            "targets": ["old"],
            "projects": ["new"],
            "target_aliases": {"o": "O"},
            "project_aliases": {"n": "N"}
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
                {"name": "Skill 2", "local_path": "/s2", "category": "Tests"}
            ],
            "projects": [{"id": "p1"}]
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
