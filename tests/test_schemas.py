from skill_manager.core.schemas import (
    AppConfig,
    CacheState,
    PackageConfig,
    SkillMetadata,
    SkillRecord,
)


def test_app_config_accepts_legacy_targets_and_aliases():
    config = AppConfig.from_legacy(
        {
            "targets": ["legacy-project"],
            "target_aliases": {"C:/repo/.agents/skills": "Repo"},
            "unknown_field": "preserved",
        }
    )

    dumped = config.model_dump()
    assert dumped["projects"] == ["legacy-project"]
    assert dumped["project_aliases"] == {"C:/repo/.agents/skills": "Repo"}
    assert dumped["unknown_field"] == "preserved"
    assert "targets" not in dumped
    assert "target_aliases" not in dumped


def test_app_config_prefers_current_keys_over_legacy_duplicates():
    config = AppConfig.from_legacy(
        {
            "targets": ["legacy-project"],
            "projects": ["current-project"],
            "target_aliases": {"old": "Old"},
            "project_aliases": {"new": "New"},
        }
    )

    dumped = config.model_dump()
    assert dumped["projects"] == ["current-project"]
    assert dumped["project_aliases"] == {"new": "New"}


def test_cache_state_fills_missing_keys_and_preserves_extras():
    cache = CacheState.model_validate({"skills": [{"name": "One"}], "version": 8})

    dumped = cache.model_dump()
    assert dumped["skills"][0]["name"] == "One"
    assert dumped["projects"] == []
    assert dumped["categories"] == []
    assert dumped["project_labels"] == []
    assert dumped["status"] == ""
    assert dumped["version"] == 8


def test_skill_record_is_tolerant_of_malformed_loadable_values():
    record = SkillRecord.model_validate(
        {
            "name": None,
            "category": 123,
            "description": ["not", "ideal"],
            "local_path": None,
            "is_package": True,
            "extra": "preserved",
        }
    )

    dumped = record.model_dump()
    assert dumped["name"] == ""
    assert dumped["category"] == "123"
    assert dumped["description"] == "['not', 'ideal']"
    assert dumped["local_path"] == ""
    assert dumped["is_package"] is True
    assert dumped["extra"] == "preserved"


def test_metadata_and_package_config_defaults_are_legacy_tolerant():
    metadata = SkillMetadata.model_validate({"tags": None, "risk": "High"})
    package = PackageConfig.model_validate({"id": "pkg", "unexpected": "kept"})

    assert metadata.model_dump()["tags"] == []
    assert metadata.model_dump()["risk"] == "High"
    assert package.model_dump()["enabled"] is True
    assert package.model_dump()["unexpected"] == "kept"
