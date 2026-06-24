"""Tests for multi-project command edit fixes.

Covers update_custom_command_file_multi (add/keep/remove sets,
canonical preservation, confirm hook) and discover_project (target-only,
hidden-dir skipping).
"""

from pathlib import Path

from skill_manager.core.commands import (
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
