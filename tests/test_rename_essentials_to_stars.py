# Purpose: Verification of the renaming from essentials to starred terminology.
# Usage: Run via `pytest tests/test_rename_essentials_to_stars.py`


def test_config_constants_renamed():
    import skill_manager.core.config as config

    # Assert new starred constants exist
    assert hasattr(config, "SKILL_LIBRARY_STARRED_FILENAME")
    assert config.SKILL_LIBRARY_STARRED_FILENAME == "skill_library_starred.json"
    assert hasattr(config, "SKILL_LIBRARY_STARRED_FILE")
    assert "skill_library_starred.json" in str(config.SKILL_LIBRARY_STARRED_FILE)

    # Assert old essentials constants are removed
    assert not hasattr(config, "SKILL_LIBRARY_ESSENTIALS_FILENAME")
    assert not hasattr(config, "SKILL_LIBRARY_ESSENTIALS_FILE")
    assert "skill_library_starred.json" in config.DATA_FILENAMES
    assert "skill_library_essentials.json" not in config.DATA_FILENAMES


def test_persistence_functions_renamed():
    import skill_manager.core.persistence as persistence

    # Assert new starred functions exist
    assert hasattr(persistence, "save_starred")
    assert hasattr(persistence, "load_starred")

    # Assert old essentials functions are removed
    assert not hasattr(persistence, "save_essentials")
    assert not hasattr(persistence, "load_essentials")


def test_discovery_service_starred():
    from skill_manager.core.discovery import DiscoveryService

    # Initialize DiscoveryService with starred_paths instead of essential_paths
    service = DiscoveryService(
        sources=[],
        projects=[],
        archive_paths=["/a1"],
        starred_paths=["/path/to/starred/skill"],
    )

    assert hasattr(service, "starred_paths")
    assert service.starred_paths == ["/path/to/starred/skill"]
    assert not hasattr(service, "essential_paths")

    # Test _transform_skill assigns "is_starred"
    raw_skill = {
        "name": "Super Skill",
        "local_path": "/path/to/starred/skill",
        "metadata": {"risk": "Low", "source": "Internal"},
    }

    transformed = service._transform_skill(raw_skill, is_package=True)
    assert transformed["is_starred"] is True
    assert "is_essential" not in transformed


def test_skill_model_starred():
    from skill_manager.core.models import SkillModel

    # Assert roles, signals, and properties
    assert hasattr(SkillModel, "IsStarredRole")
    assert not hasattr(SkillModel, "IsEssentialRole")
    assert hasattr(SkillModel, "showStarredChanged")
    assert not hasattr(SkillModel, "showEssentialsChanged")

    model = SkillModel()
    assert hasattr(model, "showStarred")
    assert not hasattr(model, "showEssentials")

    roles = model.roleNames()
    assert SkillModel.IsStarredRole in roles
    assert roles[SkillModel.IsStarredRole] == b"isStarred"

    # Test section grouping with starred skill
    starred_skill = {
        "name": "Important Skill",
        "local_path": "/p1",
        "is_starred": True,
        "category": "General",
    }
    model.setSkills([starred_skill])

    # Check data for starred role and section role
    idx = model.index(0, 0)
    assert model.data(idx, SkillModel.IsStarredRole) is True
    assert model.data(idx, SkillModel.SectionRole) == "Special|Starred"
