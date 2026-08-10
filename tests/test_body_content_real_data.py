"""Test body_content flows through the real discovery pipeline with actual skill files.

Run: uv run pytest tests/test_body_content_real_data.py -x -v -s
"""

import os
from pathlib import Path

import pytest

from skill_manager.core.models.entities import PreparedModelState, Skill
from skill_manager.core.parsing.skill import parse_skill_md


def _find_skill_files(base_dir, max_files=3):
    """Find real SKILL.md files with non-trivial body content."""
    results = []
    for root, _dirs, files in os.walk(base_dir):
        if "SKILL.md" in files:
            fp = Path(root) / "SKILL.md"
            text = fp.read_text(encoding="utf-8-sig", errors="replace")
            # Only keep files with meaningful content after frontmatter
            if len(text) > 500:
                results.append(fp)
                if len(results) >= max_files:
                    break
    return results


def test_real_skill_parse_preserves_body_content():
    """Parse real skill files and verify body_content is present."""
    skill_dir = Path(os.path.expanduser("~/.agent/skills"))
    if not skill_dir.is_dir():
        pytest.skip("No skill directory found")

    skill_files = _find_skill_files(skill_dir)
    assert len(skill_files) > 0, "No real skill files found"

    for sf in skill_files[:2]:
        result = parse_skill_md(str(sf))
        assert result, f"parse_skill_md returned empty for {sf}"
        bc = result.get("body_content", "")
        print(f"\n[DIAG] File: {sf.name}")
        print(f"[DIAG]   raw_content len={len(result.get('raw_content', ''))}")
        print(f"[DIAG]   body_content len={len(bc)}")
        print(f"[DIAG]   body_content[:100]={bc[:100]!r}")
        assert len(bc) > 0, f"body_content is empty after parse_skill_md for {sf}"


def test_model_get_skill_at_with_real_data(app_controller, qapp):
    """Load real skill data into the model and verify get_skill_at returns body_content."""
    skill_dir = Path(os.path.expanduser("~/.agent/skills"))
    if not skill_dir.is_dir():
        pytest.skip("No skill directory found")

    skill_files = _find_skill_files(skill_dir)
    if not skill_files:
        pytest.skip("No suitable skill files found")

    sf = skill_files[0]
    result = parse_skill_md(str(sf))
    assert result, f"parse_skill_md failed for {sf}"

    # Build a Skill object from the parsed data — must add local_path
    # (SkillRecord requires it but raw parse_skill_md doesn't have it)
    result["local_path"] = str(sf)
    skill = Skill.from_dict(result)
    assert len(skill.body_content) > 0, f"Skill.body_content is empty for {sf.name}"
    print(f"\n[DIAG] Skill '{skill.name}' body_content len={len(skill.body_content)}")

    # Create PreparedModelState and commit to model
    state = PreparedModelState(
        all_skills=[skill],
        search_engine=None,
        all_filtered_skills=[skill],
        visible_rows=[skill],
        categories=["General"],
        status="test",
        generation=1,
    )
    app_controller._library_model.replacePreparedState(state)
    qapp.processEvents()
    for _ in range(5):
        qapp.processEvents()

    # Use app_controller's selectSkill to select the skill
    app_controller.selectSkill(0)
    qapp.processEvents()

    # Check selectedSkill body_content
    sel = app_controller.selectedSkill
    bc = sel.body_content if sel else ""
    print(f"[DIAG] After selectSkill(0): body_content len={len(bc)}")
    print(f"[DIAG] body_content[:100]={bc[:100]!r}")

    assert len(bc) > 0, (
        f"body_content is EMPTY in selectedSkill after selectSkill(0) for real skill '{skill.name}'"
    )


def test_set_selected_skill_preserves_real_body_content(app_controller):
    """Direct set_selected_skill with real parsed data preserves body_content."""
    skill_dir = Path(os.path.expanduser("~/.agent/skills"))
    if not skill_dir.is_dir():
        pytest.skip("No skill directory found")

    skill_files = _find_skill_files(skill_dir)
    if not skill_files:
        pytest.skip("No suitable skill files found")

    sf = skill_files[0]
    result = parse_skill_md(str(sf))
    assert result

    skill_dict = {
        "name": result.get("name", "Test"),
        "local_path": str(sf),
        "body_content": result.get("body_content", ""),
        "is_command": False,
        "is_snap": False,
    }

    app_controller.set_selected_skill(skill_dict)
    sel = app_controller.selectedSkill
    bc = sel.body_content if sel else ""

    print(f"\n[DIAG] Real skill file: {sf.name}")
    print(f"[DIAG] body_content len in QMap: {len(bc)}")
    print(f"[DIAG] body_content[:100]={bc[:100]!r}")

    assert len(bc) > 0, "body_content is EMPTY in QMap after set_selected_skill with real data"
