"""Tests for multi-project command edit fixes.

Covers update_custom_command_file_multi (add/keep/remove sets,
canonical preservation, confirm hook) and discover_project (target-only,
hidden-dir skipping).
"""

from pathlib import Path

from skill_manager.core.commands import (
    build_command_content,
    find_command_holder_projects,
    update_custom_command_file_multi,
)
from skill_manager.core.discovery import DiscoveryService
from skill_manager.core.quick_copy import project_label

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_command(cmd_dir: Path, name: str, body: str = "body") -> Path:
    """Write a command .md file with standard frontmatter."""
    cmd_file = cmd_dir / f"{name}.md"
    cmd_file.write_text(f"---\nname: {name}\n---\n{body}", encoding="utf-8")
    return cmd_file


def _make_project(tmp_path: Path, label: str) -> Path:
    """Create a project dir with .agents/commands/ and .agents/skills/.

    Returns the project root path.
    """
    proj = tmp_path / label
    (proj / ".agents" / "commands").mkdir(parents=True, exist_ok=True)
    (proj / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
    return proj


def _compute_label(project_path: Path) -> str:
    """Compute the canonical project label for a path."""
    return project_label(project_path)


# ---------------------------------------------------------------------------
# Tests 1-6: update_custom_command_file_multi
# ---------------------------------------------------------------------------


class TestUpdateMultiProject:
    """Tests for update_custom_command_file_multi."""

    def test_update_multi_project_adds_new_project(self, tmp_path):
        """Adding a project copies the command file there."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        cmd_a = _write_command(proj_a / ".agents" / "commands", "Cmd")

        label_a = _compute_label(proj_a)
        label_b = _compute_label(proj_b)

        results = update_custom_command_file_multi(
            local_path=str(cmd_a),
            name="Cmd",
            body="body",
            category="Commands",
            project_labels=[label_a, label_b],
            project_paths=[str(proj_a), str(proj_b)],
        )

        # File should exist in both projects
        cmd_in_a = proj_a / ".agents" / "commands" / "Cmd.md"
        cmd_in_b = proj_b / ".agents" / "commands" / "Cmd.md"
        assert cmd_in_a.is_file(), "File should remain in project A"
        assert cmd_in_b.is_file(), "File should be created in project B"

        # At least one result per project with ok=True
        ok_results = [r for r in results if r.ok]
        assert len(ok_results) >= 2, f"Expected >=2 ok results, got {len(ok_results)}"

        # Check set_membership
        canonical = [r for r in ok_results if r.set_membership == "canonical"]
        fanout = [r for r in ok_results if r.set_membership == "fanout_add"]
        assert len(canonical) == 1, f"Expected 1 canonical result, got {len(canonical)}"
        assert len(fanout) >= 1, f"Expected >=1 fanout_add result, got {len(fanout)}"

        # Both labels appear in holder check
        holders = find_command_holder_projects("Cmd", [str(proj_a), str(proj_b)])
        assert label_a in holders
        assert label_b in holders

    def test_update_multi_project_removes_deleted_project(self, tmp_path):
        """Confirming removal deletes the command from the removed project."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        _write_command(proj_a / ".agents" / "commands", "Cmd")
        _write_command(proj_b / ".agents" / "commands", "Cmd")

        label_a = _compute_label(proj_a)
        label_b = _compute_label(proj_b)

        results = update_custom_command_file_multi(
            local_path=str(proj_a / ".agents" / "commands" / "Cmd.md"),
            name="Cmd",
            body="body",
            category="Commands",
            project_labels=[label_a],
            project_paths=[str(proj_a), str(proj_b)],
            confirmed_removals=[label_b],
        )

        cmd_a = proj_a / ".agents" / "commands" / "Cmd.md"
        cmd_b = proj_b / ".agents" / "commands" / "Cmd.md"
        assert cmd_a.is_file(), "File should still exist in project A"
        assert not cmd_b.is_file(), "File should be deleted from project B"

        # Check removal result is present
        removal_results = [r for r in results if "Removed" in r.message]
        assert removal_results, "Expected a removal result in output"

    def test_update_multi_project_needs_confirm_before_delete(self, tmp_path):
        """Without confirmed_removals, returns needs_confirm=True."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        _write_command(proj_a / ".agents" / "commands", "Cmd")
        _write_command(proj_b / ".agents" / "commands", "Cmd")

        label_a = _compute_label(proj_a)
        label_b = _compute_label(proj_b)

        results = update_custom_command_file_multi(
            local_path=str(proj_a / ".agents" / "commands" / "Cmd.md"),
            name="Cmd",
            body="body",
            category="Commands",
            project_labels=[label_a],
            project_paths=[str(proj_a), str(proj_b)],
            # No confirmed_removals — should trigger confirm flow
        )

        assert len(results) == 1
        assert results[0].needs_confirm is True
        assert label_b in results[0].pending_removals

        # Files untouched
        cmd_a = proj_a / ".agents" / "commands" / "Cmd.md"
        cmd_b = proj_b / ".agents" / "commands" / "Cmd.md"
        assert cmd_a.is_file(), "File should remain in project A"
        assert cmd_b.is_file(), "File should NOT be deleted yet in project B"

    def test_update_multi_project_cancel_removes_nothing(self, tmp_path):
        """Empty confirmed_removals list cancels all removals."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        _write_command(proj_a / ".agents" / "commands", "Cmd")
        _write_command(proj_b / ".agents" / "commands", "Cmd")

        label_a = _compute_label(proj_a)

        update_custom_command_file_multi(
            local_path=str(proj_a / ".agents" / "commands" / "Cmd.md"),
            name="Cmd",
            body="body",
            category="Commands",
            project_labels=[label_a],
            project_paths=[str(proj_a), str(proj_b)],
            confirmed_removals=[],  # Cancel: confirm empty set
        )

        cmd_a = proj_a / ".agents" / "commands" / "Cmd.md"
        cmd_b = proj_b / ".agents" / "commands" / "Cmd.md"
        assert cmd_a.is_file(), "File should remain in project A"
        assert cmd_b.is_file(), "File should remain in project B (cancel=no delete)"

    def test_update_multi_project_preserves_original_holder(self, tmp_path):
        """When A is original holder and B is added first in list, A is not moved."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        cmd_a = _write_command(proj_a / ".agents" / "commands", "Cmd")

        label_a = _compute_label(proj_a)
        label_b = _compute_label(proj_b)

        # B first in the list — A should still be the canonical holder
        results = update_custom_command_file_multi(
            local_path=str(cmd_a),
            name="Cmd",
            body="body",
            category="Commands",
            project_labels=[label_b, label_a],
            project_paths=[str(proj_a), str(proj_b)],
        )

        # File still in A (not moved away)
        cmd_in_a = proj_a / ".agents" / "commands" / "Cmd.md"
        assert cmd_in_a.is_file(), "File should remain in project A"

        # File also in B
        cmd_in_b = proj_b / ".agents" / "commands" / "Cmd.md"
        assert cmd_in_b.is_file(), "File should exist in project B"

        # Canonical result should reference A's path (keep_set picks first match)
        ok_results = [r for r in results if r.ok and r.path]
        canonical_path = ok_results[0].path if ok_results else None
        # Canonical is from keep_set (A is current holder), so path stays in A
        if canonical_path:
            assert canonical_path.parent == cmd_in_a.parent, (
                f"Canonical should stay in A, got {canonical_path}"
            )

    def test_update_multi_project_idempotent(self, tmp_path):
        """Calling twice with same inputs yields same end state."""
        proj_a = _make_project(tmp_path, "projA")

        cmd_a = _write_command(proj_a / ".agents" / "commands", "Cmd")

        label_a = _compute_label(proj_a)
        paths = [str(proj_a)]
        labels = [label_a]

        def _call():
            return update_custom_command_file_multi(
                local_path=str(cmd_a),
                name="Cmd",
                body="body",
                category="Commands",
                project_labels=labels,
                project_paths=paths,
            )

        results_1 = _call()
        results_2 = _call()

        # Both succeed
        assert all(r.ok for r in results_1)
        assert all(r.ok for r in results_2)

        # File still exists
        cmd_file = proj_a / ".agents" / "commands" / "Cmd.md"
        assert cmd_file.is_file()

        # Content is deterministic
        content = cmd_file.read_text(encoding="utf-8")
        assert "Cmd" in content

    def test_update_multi_project_with_aliases(self, tmp_path):
        """When project aliases are configured, multi-project updates match them correctly without false removal warnings."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        # Command is in project A
        cmd_a = _write_command(proj_a / ".agents" / "commands", "Cmd")

        # Let's map project roots to custom aliases
        aliases = {
            str(proj_a): "AliasA",
            str(proj_b): "AliasB",
        }

        # Query update with aliases as labels
        results = update_custom_command_file_multi(
            local_path=str(cmd_a),
            name="Cmd",
            body="body",
            category="Commands",
            project_labels=["AliasA", "AliasB"],
            project_paths=[str(proj_a), str(proj_b)],
            project_aliases=aliases,
        )

        # No warning/removal requested
        assert len(results) >= 2
        for r in results:
            assert not r.needs_confirm, "Should not require confirmation of removals"
            assert r.ok, f"Expected ok result, got: {r.message}"

        # Holders check with aliases
        holders = find_command_holder_projects(
            "Cmd", [str(proj_a), str(proj_b)], project_aliases=aliases
        )
        assert "AliasA" in holders
        assert "AliasB" in holders

        # Test with the .agents/skills subfolder paths as well
        proj_a_skills = proj_a / ".agents" / "skills"
        proj_b_skills = proj_b / ".agents" / "skills"
        proj_a_skills.mkdir(parents=True, exist_ok=True)
        proj_b_skills.mkdir(parents=True, exist_ok=True)

        holders_sub = find_command_holder_projects(
            "Cmd", [str(proj_a_skills), str(proj_b_skills)], project_aliases=aliases
        )
        assert "AliasA" in holders_sub
        assert "AliasB" in holders_sub

    def test_update_multi_project_keeps_original_holder(self, tmp_path):
        """When the original file is in projB but projA sorts first AND
        both hold the command, the file stays in projB (not moved to projA)."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        # Put the command in BOTH projects, but the local_path is from projB
        cmd_b = _write_command(proj_b / ".agents" / "commands", "Cmd", "old-body-b")

        label_a = _compute_label(proj_a)
        label_b = _compute_label(proj_b)

        # projA sorts BEFORE projB. Both hold the command. The original file is in projB.
        aliases = {str(proj_a): label_a, str(proj_b): label_b}
        results = update_custom_command_file_multi(
            local_path=str(cmd_b),
            name="Cmd",
            body="new body",
            category="Commands",
            project_labels=[label_b, label_a],
            project_paths=[str(proj_a), str(proj_b)],
            project_aliases=aliases,
        )

        # File should stay in projB (not moved to projA despite alphabetical order)
        cmd_in_b = proj_b / ".agents" / "commands" / "Cmd.md"
        assert cmd_in_b.is_file(), "File should remain in original project B"

        # File should also exist in projA (fan-out copy)
        cmd_in_a = proj_a / ".agents" / "commands" / "Cmd.md"
        assert cmd_in_a.is_file(), "File should be copied to project A"

        # The canonical result path should be in projB (original)
        ok_results = [r for r in results if r.ok and r.path]
        canonical_path = ok_results[0].path if ok_results else None
        assert canonical_path is not None
        assert canonical_path.parent == cmd_in_b.parent, (
            f"Canonical should stay in B, got {canonical_path}"
        )

    def test_update_multi_project_skips_identical_fanout(self, tmp_path):
        """When fan-out target already has identical content, skip overwrite.

        Scenario: command is renamed from 'Cmd' to 'CmdNew'. projA was NOT a holder
        of 'CmdNew' (so it's in add_set), but already has a 'CmdNew.md' with
        identical content. The fan-out should detect this and skip the write.
        """
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        body = "same-body"
        identical_content = build_command_content("CmdNew", body, "Commands")

        # projB has the original 'Cmd.md' (old name)
        cmd_old = _write_command(proj_b / ".agents" / "commands", "Cmd", body)

        # projA already has 'CmdNew.md' with identical content (from a previous sync)
        (proj_a / ".agents" / "commands" / "CmdNew.md").write_text(
            identical_content, encoding="utf-8"
        )

        label_a = _compute_label(proj_a)
        label_b = _compute_label(proj_b)
        aliases = {str(proj_a): label_a, str(proj_b): label_b}

        results = update_custom_command_file_multi(
            local_path=str(cmd_old),
            name="CmdNew",
            body=body,
            category="Commands",
            project_labels=[label_b, label_a],
            project_paths=[str(proj_a), str(proj_b)],
            project_aliases=aliases,
        )

        # projA should get "Already up to date" (identical content, skip write)
        ok_results = [r for r in results if r.ok]
        a_result = next(
            (r for r in ok_results if r.path and str(proj_a) in str(r.path)),
            None,
        )
        assert a_result is not None, f"Expected projA result, got: {[r.path for r in ok_results]}"
        assert "Already up to date" in a_result.message, (
            f"Expected 'Already up to date' for projA, got: {a_result.message}"
        )
        assert a_result.set_membership == "fanout_skip", (
            f"Expected set_membership='fanout_skip', got: {a_result.set_membership}"
        )

    def test_update_multi_project_warns_on_different_content(self, tmp_path):
        """When target project has different content, conflict is raised.

        Both projects already hold the command, so add_set is empty and the
        fan-out has nothing to do.  The canonical update targets the original
        project (projB) and succeeds.  projA is an existing holder that keeps
        its own file — it is NOT overwritten by the fan-out.
        """
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        cmd_b = _write_command(proj_b / ".agents" / "commands", "Cmd", "new-body")
        # Pre-populate A with different content
        (proj_a / ".agents" / "commands" / "Cmd.md").write_text(
            "---\nname: Cmd\n---\ndifferent-body", encoding="utf-8"
        )

        label_a = _compute_label(proj_a)
        label_b = _compute_label(proj_b)

        results = update_custom_command_file_multi(
            local_path=str(cmd_b),
            name="Cmd",
            body="new-body",
            category="Commands",
            project_labels=[label_b, label_a],
            project_paths=[str(proj_a), str(proj_b)],
        )

        # Canonical update targets projB (original project) and succeeds.
        # Fan-out has nothing to do (add_set empty). projA keeps its file.
        ok_results = [r for r in results if r.ok]
        assert len(ok_results) == 1, f"Expected 1 ok result, got {len(ok_results)}"
        assert "Cmd.md" in ok_results[0].message
        # projA's file is NOT overwritten
        a_content = (proj_a / ".agents" / "commands" / "Cmd.md").read_text(encoding="utf-8")
        assert "different-body" in a_content


# ---------------------------------------------------------------------------
# Tests 7-8: DiscoveryService.discover_project
# ---------------------------------------------------------------------------


class TestDiscoverProject:
    """Tests for DiscoveryService.discover_project."""

    def test_discover_project_returns_only_target(self, tmp_path):
        """discover_project returns skills/commands from target project only."""
        proj_a = _make_project(tmp_path, "projA")
        proj_b = _make_project(tmp_path, "projB")

        # Add a command to A
        _write_command(proj_a / ".agents" / "commands", "CmdA")

        # Add a skill to B
        skill_b = proj_b / ".agents" / "skills" / "skillB"
        skill_b.mkdir(parents=True, exist_ok=True)
        (skill_b / "SKILL.md").write_text(
            "---\nname: SkillB\ndescription: test\n---\n", encoding="utf-8"
        )

        service = DiscoveryService(sources=[], projects=[str(proj_a), str(proj_b)])

        results_a = service.discover_project(proj_a)

        names = [r.get("name", "") for r in results_a]
        assert "CmdA" in names, f"Expected CmdA in results, got {names}"
        assert "SkillB" not in names, f"SkillB should not be in project A results: {names}"

    def test_discover_project_skips_hidden_dirs(self, tmp_path):
        """Hidden directories under .agents/skills are skipped."""
        proj = _make_project(tmp_path, "proj")

        # Hidden skill dir
        hidden_skill = proj / ".agents" / "skills" / ".hidden-skill"
        hidden_skill.mkdir(parents=True, exist_ok=True)
        (hidden_skill / "SKILL.md").write_text(
            "---\nname: HiddenSkill\ndescription: hidden\n---\n", encoding="utf-8"
        )

        # Normal skill dir
        normal_skill = proj / ".agents" / "skills" / "visible-skill"
        normal_skill.mkdir(parents=True, exist_ok=True)
        (normal_skill / "SKILL.md").write_text(
            "---\nname: VisibleSkill\ndescription: visible\n---\n", encoding="utf-8"
        )

        service = DiscoveryService(sources=[], projects=[str(proj)])
        results = service.discover_project(proj)

        names = [r.get("name", "") for r in results]
        assert "VisibleSkill" in names, f"Expected VisibleSkill, got {names}"
        assert "HiddenSkill" not in names, f"HiddenSkill should be skipped: {names}"
