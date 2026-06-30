"""Tests for checkMissingSkills, getCollectionsDiagnostic, and getProjectResolutionTable."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from skill_manager.controllers.config_controller import ConfigController


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._sources = []
    app._projects = []
    app._project_aliases = {}
    app._syncing_projects = []
    app._custom_collections = {}
    app._config = MagicMock()
    return app


@pytest.fixture
def config_controller(mock_app):
    return ConfigController(mock_app)


# --- checkMissingSkills ---


def test_check_missing_skills_returns_empty_for_missing_collection(config_controller):
    result = json.loads(config_controller.checkMissingSkills("nonexistent"))
    assert result == {}


def test_check_missing_skills_returns_empty_for_empty_projects(config_controller):
    config_controller.app._custom_collections = {"MyColl": {"paths": ["/a"], "projects": []}}
    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    assert result == {}


def test_check_missing_skills_returns_empty_for_empty_paths(config_controller):
    config_controller.app._custom_collections = {"MyColl": {"paths": [], "projects": ["Proj"]}}
    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    assert result == {}


def test_check_missing_skills_skips_non_string_paths(config_controller, tmp_path):
    skills_dir = tmp_path / "proj" / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "existing-skill").mkdir()

    config_controller.app._custom_collections = {
        "MyColl": {
            "paths": [None, 123, "/proj/.agents/skills/existing-skill"],
            "projects": ["Proj"],
        }
    }
    config_controller.app._projects = [str(tmp_path / "proj")]
    config_controller.app._project_aliases = {}

    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    # None and 123 are skipped; existing-skill exists so not missing
    assert result == {}


def test_check_missing_skills_skips_non_string_project_labels(config_controller):
    config_controller.app._custom_collections = {
        "MyColl": {"paths": ["/a"], "projects": [None, 123]}
    }
    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    assert result == {}


def test_check_missing_skills_returns_missing_for_unresolved_project(config_controller):
    config_controller.app._custom_collections = {
        "MyColl": {
            "paths": ["/skill/path"],
            "projects": ["UnresolvedProj"],
        }
    }
    config_controller.app._projects = []
    config_controller.app._project_aliases = {}

    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    assert result == {}


def test_check_missing_skills_detects_missing_skill(tmp_path, config_controller):
    skills_dir = tmp_path / "proj" / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    project_path = str(tmp_path / "proj")
    config_controller.app._custom_collections = {
        "MyColl": {
            "paths": [project_path + "/.agents/skills/missing-skill"],
            "projects": ["Proj"],
        }
    }
    config_controller.app._projects = [project_path]
    config_controller.app._project_aliases = {project_path: "Proj"}

    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    assert "Proj" in result
    assert project_path + "/.agents/skills/missing-skill" in result["Proj"]


def test_check_missing_skills_no_false_positive(tmp_path, config_controller):
    skills_dir = tmp_path / "proj" / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "my-skill").mkdir()

    config_controller.app._custom_collections = {
        "MyColl": {
            "paths": ["/proj/.agents/skills/my-skill"],
            "projects": ["Proj"],
        }
    }
    config_controller.app._projects = [str(tmp_path / "proj")]
    config_controller.app._project_aliases = {}

    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    assert result == {}


def test_check_missing_skills_legacy_entry_returns_empty(config_controller):
    config_controller.app._custom_collections = {"OldColl": ["/a", "/b"]}
    result = json.loads(config_controller.checkMissingSkills("OldColl"))
    assert result == {}


def test_check_missing_skills_entry_with_none_paths_returns_empty(config_controller):
    config_controller.app._custom_collections = {"BadColl": {"paths": None, "projects": ["P"]}}
    result = json.loads(config_controller.checkMissingSkills("BadColl"))
    assert result == {}


def test_check_missing_skills_empty_skill_folder_name(tmp_path, config_controller):
    """A skill_path ending in / should produce empty skill_folder and not match any dir."""
    skills_dir = tmp_path / "proj" / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    config_controller.app._custom_collections = {
        "MyColl": {
            "paths": ["/proj/.agents/skills/"],
            "projects": ["Proj"],
        }
    }
    config_controller.app._projects = [str(tmp_path / "proj")]
    config_controller.app._project_aliases = {}

    result = json.loads(config_controller.checkMissingSkills("MyColl"))
    # Empty skill_folder means the check is skipped (skill_folder is "")
    assert result == {}


# --- getCollectionsDiagnostic ---


def test_get_collections_diagnostic_empty(config_controller):
    config_controller.app._custom_collections = {}
    result = json.loads(config_controller.getCollectionsDiagnostic())
    assert result == {}


def test_get_collections_diagnostic_normalizes_types(config_controller):
    config_controller.app._custom_collections = {
        "Coll1": {
            "paths": ["/a", "/b"],
            "projects": ["ProjA"],
        }
    }
    result = json.loads(config_controller.getCollectionsDiagnostic())
    assert result["Coll1"]["paths"] == ["/a", "/b"]
    assert result["Coll1"]["paths_type"] == "list"


def test_get_collections_diagnostic_handles_legacy_list(config_controller):
    config_controller.app._custom_collections = {"Old": ["/x", "/y"]}
    result = json.loads(config_controller.getCollectionsDiagnostic())
    assert result["Old"]["paths"] == ["/x", "/y"]
    assert result["Old"]["paths_type"] == "list (legacy)"


def test_get_collections_diagnostic_handles_none_values(config_controller):
    config_controller.app._custom_collections = {
        "Bad": {"paths": [None, "/valid"], "projects": [None]}
    }
    result = json.loads(config_controller.getCollectionsDiagnostic())
    assert result["Bad"]["paths"] == ["/valid"]
    assert result["Bad"]["projects"] == []


def test_get_collections_diagnostic_handles_unexpected_type(config_controller):
    config_controller.app._custom_collections = {"Weird": "not a dict or list"}
    result = json.loads(config_controller.getCollectionsDiagnostic())
    assert "error" in result["Weird"]


# --- getProjectResolutionTable ---


def test_get_project_resolution_table_empty(config_controller):
    result = json.loads(config_controller.getProjectResolutionTable())
    assert result["registered_projects"] == []
    assert result["collection_project_labels"] == []


def test_get_project_resolution_table_includes_registered_projects(config_controller):
    config_controller.app._projects = ["/path/to/proj"]
    config_controller.app._project_aliases = {"/path/to/proj": "MyProj"}
    config_controller.app._custom_collections = {}

    result = json.loads(config_controller.getProjectResolutionTable())
    assert len(result["registered_projects"]) == 1
    proj = result["registered_projects"][0]
    assert proj["label"] == "MyProj"
    assert proj["resolvable"] is True
    assert "resolved_skills_dir" in proj
    assert "skills_dir_exists" in proj


# --- Diagnostic Slots ---


def test_get_diagnostic_log_path(config_controller):
    path = config_controller.getDiagnosticLogPath()
    assert isinstance(path, str)
    assert "diagnostic.log" in path


def test_get_recent_diagnostic_events(config_controller):
    result = config_controller.getRecentDiagnosticEvents(10)
    events = json.loads(result)
    assert isinstance(events, list)


def test_get_recent_diagnostic_events_returns_json_array(config_controller):
    result = config_controller.getRecentDiagnosticEvents(5)
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    # Each event should have the standard schema
    for event in parsed:
        assert "ts" in event
        assert "level" in event
        assert "category" in event
        assert "msg" in event


def test_clear_diagnostic_logs(config_controller):
    # Should not raise
    config_controller.clearDiagnosticLogs()
    # Check status was set
    assert "Diagnostic logs cleared" in config_controller.app._set_status.call_args_list[-1][0][0]


def test_export_diagnostic_bundle(config_controller, tmp_path):
    result = config_controller.exportDiagnosticBundle(str(tmp_path))
    # May or may not succeed depending on logger state, but should return str
    assert isinstance(result, str)


# --- Regression: double-normalization bug (Phase 3) ---


def test_check_missing_skills_works_with_normalized_skills_path(config_controller, tmp_path):
    """When project_path is already a .agents/skills dir (normalized by addProject),
    checkMissingSkills must NOT double-normalize."""
    project_dir = tmp_path / "myproject"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "brainstorming").mkdir()
    (skills_dir / "brainstorming" / "SKILL.md").write_text("x")

    config_controller.app._custom_collections = {
        "TestSkills": {
            "paths": [str(skills_dir / "brainstorming")],
            "projects": ["MyProj"],
        }
    }
    config_controller.app._projects = [str(skills_dir)]
    config_controller.app._project_aliases = {str(skills_dir): "MyProj"}

    result = json.loads(config_controller.checkMissingSkills("TestSkills"))
    assert result == {}, f"Expected empty dict, got {result}"


def test_check_missing_skills_works_with_agents_skills_path(config_controller, tmp_path):
    """When project_path is <root>/.agents/skills, get_skills_dir should return it as-is."""
    project_dir = tmp_path / "proj"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "foo").mkdir()
    (skills_dir / "foo" / "SKILL.md").write_text("x")

    config_controller.app._custom_collections = {
        "TestSkills": {
            "paths": [str(skills_dir / "foo")],
            "projects": ["P"],
        }
    }
    config_controller.app._projects = [str(skills_dir)]
    config_controller.app._project_aliases = {str(skills_dir): "P"}

    result = json.loads(config_controller.checkMissingSkills("TestSkills"))
    assert result == {}


def test_check_missing_skills_works_with_project_root_path(config_controller, tmp_path):
    """When project_path is the project root, get_skills_dir should find .agents/skills."""
    project_dir = tmp_path / "myroot"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "cavecrew").mkdir()
    (skills_dir / "cavecrew" / "SKILL.md").write_text("x")

    config_controller.app._custom_collections = {
        "TestSkills": {
            "paths": [str(skills_dir / "cavecrew")],
            "projects": ["R"],
        }
    }
    config_controller.app._projects = [str(project_dir)]
    config_controller.app._project_aliases = {str(project_dir): "R"}

    result = json.loads(config_controller.checkMissingSkills("TestSkills"))
    assert result == {}


def test_check_missing_skills_detects_missing_in_normalized_project(config_controller, tmp_path):
    """Even with normalized path, truly missing skills should still be detected."""
    project_dir = tmp_path / "missing"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "existing").mkdir()
    (skills_dir / "existing" / "SKILL.md").write_text("x")

    config_controller.app._custom_collections = {
        "TestSkills": {
            "paths": [
                str(skills_dir / "existing"),
                str(skills_dir / "nonexistent"),
            ],
            "projects": ["M"],
        }
    }
    config_controller.app._projects = [str(skills_dir)]
    config_controller.app._project_aliases = {str(skills_dir): "M"}

    result = json.loads(config_controller.checkMissingSkills("TestSkills"))
    assert "M" in result
    assert len(result["M"]) == 1
    assert "nonexistent" in result["M"][0]


def test_check_missing_skills_logs_resolution_trace_at_info(config_controller, tmp_path):
    """checkMissingSkills emits missing_skills_check INFO log per project."""
    project_dir = tmp_path / "logtest"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "a").mkdir()
    (skills_dir / "a" / "SKILL.md").write_text("x")

    config_controller.app._custom_collections = {
        "LogSkills": {
            "paths": [str(skills_dir / "a")],
            "projects": ["L"],
        }
    }
    config_controller.app._projects = [str(skills_dir)]
    config_controller.app._project_aliases = {str(skills_dir): "L"}

    from skill_manager.core.diagnostics import get_diagnostic_logger

    logger = get_diagnostic_logger()
    logger.initialize()
    logger.set_enabled(True)
    before = logger.get_recent_events(50)

    config_controller.checkMissingSkills("LogSkills")

    after = logger.get_recent_events(50)
    new_events = [e for e in after if e not in before]
    info_checks = [e for e in new_events if e.get("category") == "missing_skills_check"]
    assert len(info_checks) >= 1, f"Expected missing_skills_check INFO log, got {len(info_checks)}"


def test_check_missing_skills_logs_per_skill_at_debug(config_controller, tmp_path):
    """checkMissingSkills emits missing_skills_per_skill DEBUG log per skill."""
    from skill_manager.core.diagnostics import get_diagnostic_logger

    logger = get_diagnostic_logger()
    logger.initialize(log_level="DEBUG")
    logger.set_enabled(True)

    project_dir = tmp_path / "debugtest"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "x").mkdir()
    (skills_dir / "x" / "SKILL.md").write_text("x")

    config_controller.app._custom_collections = {
        "DebugSkills": {
            "paths": [str(skills_dir / "x")],
            "projects": ["D"],
        }
    }
    config_controller.app._projects = [str(skills_dir)]
    config_controller.app._project_aliases = {str(skills_dir): "D"}

    before = logger.get_recent_events(50)

    config_controller.checkMissingSkills("DebugSkills")

    after = logger.get_recent_events(50)
    new_events = [e for e in after if e not in before]
    debug_skills = [e for e in new_events if e.get("category") == "missing_skills_per_skill"]
    assert len(debug_skills) == 1, (
        f"Expected 1 missing_skills_per_skill DEBUG log, got {len(debug_skills)}"
    )


def test_get_project_resolution_table_includes_resolved_skills_dir(config_controller, tmp_path):
    """getProjectResolutionTable includes resolved_skills_dir and skills_dir_exists."""
    project_dir = tmp_path / "tabletest"
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    config_controller.app._custom_collections = {"projects": ["T"]}
    config_controller.app._projects = [str(skills_dir)]
    config_controller.app._project_aliases = {str(skills_dir): "T"}

    result = json.loads(config_controller.getProjectResolutionTable())
    assert len(result["registered_projects"]) == 1
    proj = result["registered_projects"][0]
    assert "resolved_skills_dir" in proj
    assert proj["resolved_skills_dir"] == str(skills_dir)
    assert "skills_dir_exists" in proj
    assert proj["skills_dir_exists"] is True


# --- Command path handling ---


def test_save_collection_keeps_command_paths(config_controller):
    """saveCustomCollection must keep .agents/commands/ paths (commands are first-class items)."""
    config_controller.app._custom_collections = {}
    skill_path = "/proj/.agents/skills/my-skill"
    cmd_path = "/proj/.agents/commands/Test.md"
    config_controller.saveCustomCollection("Coll", [skill_path, cmd_path], [])
    stored = config_controller.app._custom_collections["Coll"]
    assert cmd_path in stored["paths"]
    assert skill_path in stored["paths"]


def test_save_collection_keeps_backslash_command_paths(config_controller):
    """Windows backslash command paths must be preserved."""
    config_controller.app._custom_collections = {}
    skill_path = "C:\\proj\\.agents\\skills\\Skill"
    cmd_path = "C:\\proj\\.agents\\commands\\Cmd.Antigravity.md"
    config_controller.saveCustomCollection("C", [skill_path, cmd_path], [])
    stored = config_controller.app._custom_collections["C"]
    assert stored["paths"] == [skill_path, cmd_path]


def test_save_collection_mixed_paths_keeps_all(config_controller):
    """Mix of skills + commands: all items are kept."""
    config_controller.app._custom_collections = {}
    paths = [
        "/proj/.agents/skills/A",
        "/proj/.agents/commands/X.md",
        "/proj/.agents/skills/B",
        "/proj/.agents/commands/Y.md",
        "/proj/.agents/skills/C",
    ]
    config_controller.saveCustomCollection("M", paths, [])
    stored = config_controller.app._custom_collections["M"]
    assert len(stored["paths"]) == 5
    assert stored["paths"] == paths


def test_save_collection_all_commands_kept(config_controller):
    """Command-only collection should save with all entries."""
    config_controller.app._custom_collections = {}
    paths = ["/proj/.agents/commands/X.md", "/proj/.agents/commands/Y.md"]
    config_controller.saveCustomCollection("AllCmd", paths, [])
    stored = config_controller.app._custom_collections["AllCmd"]
    assert stored["paths"] == paths


def test_check_missing_skills_reports_missing_command(config_controller, tmp_path):
    """Command absent from target project's .agents/commands/ is reported missing."""
    from skill_manager.core.quick_copy import project_label

    project_root = tmp_path / "ProjA"
    project_root.mkdir()
    config_controller.app._projects = [str(project_root)]
    canonical_label = project_label(str(project_root))

    config_controller.app._custom_collections = {
        "Coll": {
            "paths": ["/other/.agents/commands/MyCmd.md"],
            "projects": [canonical_label],
        }
    }
    result = json.loads(config_controller.checkMissingSkills("Coll"))
    assert canonical_label in result
    assert any("MyCmd.md" in p for p in result[canonical_label])


def test_check_missing_skills_skips_present_command(config_controller, tmp_path):
    """Command already present in target project is not reported missing."""
    project_root = tmp_path / "ProjA"
    commands_dir = project_root / ".agents" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "MyCmd.md").write_text("---\nname: MyCmd\n---\nbody", encoding="utf-8")

    config_controller.app._projects = [str(project_root)]

    config_controller.app._custom_collections = {
        "Coll": {
            "paths": ["/any/.agents/commands/MyCmd.md"],
            "projects": ["ProjA"],
        }
    }
    result = json.loads(config_controller.checkMissingSkills("Coll"))
    assert result == {}


def test_check_missing_skills_mixed_skills_and_commands(config_controller, tmp_path):
    """Both skills and commands are evaluated correctly in one call."""
    from skill_manager.core.quick_copy import project_label

    project_root = tmp_path / "ProjA"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "my-skill").mkdir()
    (skills_dir / "my-skill" / "SKILL.md").touch()

    commands_dir = project_root / ".agents" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "CmdA.md").write_text("---\nname: CmdA\n---\nbody", encoding="utf-8")

    config_controller.app._projects = [str(project_root)]
    canonical_label = project_label(str(project_root))

    config_controller.app._custom_collections = {
        "Coll": {
            "paths": [
                str(skills_dir / "my-skill"),
                str(project_root / ".agents" / "commands" / "CmdA.md"),
                "/other/.agents/commands/CmdB.md",
                "/other/.agents/skills/missing-skill",
            ],
            "projects": [canonical_label],
        }
    }
    result = json.loads(config_controller.checkMissingSkills("Coll"))
    assert canonical_label in result
    missing_names = [Path(p).name for p in result[canonical_label]]
    assert "CmdB.md" in missing_names
    assert "missing-skill" in missing_names
    assert "CmdA.md" not in missing_names
    assert "my-skill" not in missing_names
