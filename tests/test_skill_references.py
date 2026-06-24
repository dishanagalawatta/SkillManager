"""Tests for skill_references module — skill name extraction and resolution."""

import textwrap

# ---------------------------------------------------------------------------
# extract_skill_names
# ---------------------------------------------------------------------------


class TestExtractSkillNames:
    def test_empty_content(self):
        from skill_manager.core.skill_references import extract_skill_names

        assert extract_skill_names("") == []
        assert extract_skill_names(None) == []  # type: ignore[arg-type]

    def test_single_antigravity(self):
        from skill_manager.core.skill_references import extract_skill_names

        result = extract_skill_names("use /git-pr for PRs")
        assert result == ["git-pr"]

    def test_single_opencode(self):
        from skill_manager.core.skill_references import extract_skill_names

        result = extract_skill_names("use /cavecrew for subagents")
        assert result == ["cavecrew"]

    def test_single_gemini_short(self):
        from skill_manager.core.skill_references import extract_skill_names

        result = extract_skill_names("see @frontend-design")
        assert result == ["frontend-design"]

    def test_single_gemini_long(self):
        from skill_manager.core.skill_references import extract_skill_names

        result = extract_skill_names("see @.agents/skills/frontend-design/SKILL.md")
        assert result == ["frontend-design"]

    def test_single_codex(self):
        from skill_manager.core.skill_references import extract_skill_names

        result = extract_skill_names("load [$git-pr](/path/to/SKILL.md)")
        assert result == ["git-pr"]

    def test_multiple_mixed_formats(self):
        from skill_manager.core.skill_references import extract_skill_names

        content = textwrap.dedent("""\
            Use /git-pr for PR templates.
            Also load @.agents/skills/cavecrew/SKILL.md for subagents.
            And [$brainstorming](/skills/brainstorming/SKILL.md) for planning.
        """)
        result = extract_skill_names(content)
        # Order of appearance: git-pr, cavecrew, brainstorming
        assert result == ["git-pr", "cavecrew", "brainstorming"]

    def test_deduplication(self):
        from skill_manager.core.skill_references import extract_skill_names

        content = "use /git-pr and /git-pr again"
        result = extract_skill_names(content)
        assert result == ["git-pr"]

    def test_case_insensitive_dedup(self):
        from skill_manager.core.skill_references import extract_skill_names

        content = "use /Git-Pr and /git-pr"
        result = extract_skill_names(content)
        # Both match git-pr (case-insensitive key), only first kept
        assert result == ["Git-Pr"]

    def test_no_false_positives(self):
        from skill_manager.core.skill_references import extract_skill_names

        # Regular words should not match
        assert extract_skill_names("hello world") == []
        # Note: /word tokens DO match (this is by design — /name is Antigravity/OpenCode syntax).
        # URLs like https://example.com will produce "example" as a false positive, but
        # the resolution step (resolve_referenced_skills) filters these out since no real
        # skill folder will be named "example". This tradeoff keeps the simple regex fast.
        assert extract_skill_names("just plain text") == []

    def test_plain_text_no_refs(self):
        from skill_manager.core.skill_references import extract_skill_names

        assert extract_skill_names("This is just a plain prompt.") == []


# ---------------------------------------------------------------------------
# resolve_referenced_skills
# ---------------------------------------------------------------------------


def _make_skill(name, folder_name=None, local_path=None, **extra):
    """Factory for minimal skill dicts."""
    return {
        "name": name,
        "folder_name": folder_name or name.lower(),
        "local_path": local_path or f"/skills/{folder_name or name.lower()}",
        "is_command": extra.pop("is_command", False),
        "is_screenshot": extra.pop("is_screenshot", False),
        **extra,
    }


class TestResolveReferencedSkills:
    def test_empty_content(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        skills = [_make_skill("git-pr")]
        assert resolve_referenced_skills("", skills) == []
        assert resolve_referenced_skills("no refs here", skills) == []

    def test_match_by_folder_name(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        skill = _make_skill("Git PR", folder_name="git-pr")
        result = resolve_referenced_skills("use /git-pr", [skill])
        assert len(result) == 1
        assert result[0]["folder_name"] == "git-pr"

    def test_match_by_name(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        # Use a name with no spaces (the /regex only matches [a-zA-Z0-9_-]+)
        skill = _make_skill("Git-PR", folder_name="something-else")
        result = resolve_referenced_skills("use /git-pr", [skill])
        # "git-pr" extracted → lowered "git-pr" → not in folder ("something-else") → check name ("git-pr")
        assert len(result) == 1
        assert result[0]["name"] == "Git-PR"

    def test_excludes_commands(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        cmd = _make_skill("my-cmd", is_command=True)
        result = resolve_referenced_skills("use /my-cmd", [cmd])
        assert result == []

    def test_excludes_screenshots(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        ss = _make_skill("pic", folder_name="pic", is_screenshot=True)
        result = resolve_referenced_skills("use /pic", [ss])
        assert result == []

    def test_dedup_by_local_path(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        # Two entries with same local_path but different names
        s1 = _make_skill("Git PR", folder_name="git-pr", local_path="/x")
        s2 = _make_skill("Git PR Alt", folder_name="Git-PR", local_path="/x")
        result = resolve_referenced_skills("use /git-pr and /Git-PR", [s1, s2])
        assert len(result) == 1

    def test_multiple_references(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        s1 = _make_skill("git-pr", folder_name="git-pr")
        s2 = _make_skill("cavecrew", folder_name="cavecrew")
        result = resolve_referenced_skills("use /git-pr and /cavecrew", [s1, s2])
        assert len(result) == 2
        assert {s["folder_name"] for s in result} == {"git-pr", "cavecrew"}

    def test_no_match_in_skills(self):
        from skill_manager.core.skill_references import resolve_referenced_skills

        skill = _make_skill("other")
        result = resolve_referenced_skills("use /nonexistent", [skill])
        assert result == []


# ---------------------------------------------------------------------------
# find_referenced_skills_in_command
# ---------------------------------------------------------------------------


class TestFindReferencedSkillsInCommand:
    def test_reads_file(self, tmp_path):
        from skill_manager.core.commands import find_referenced_skills_in_command

        cmd_file = tmp_path / "deploy.md"
        cmd_file.write_text(
            textwrap.dedent("""\
                ---
                name: Deploy
                category: DevOps
                type: command
                ---

                Use /git-pr for pull requests.
            """),
            encoding="utf-8-sig",
        )
        skill = _make_skill("git-pr", folder_name="git-pr")
        result = find_referenced_skills_in_command(str(cmd_file), [skill])
        assert len(result) == 1
        assert result[0]["folder_name"] == "git-pr"

    def test_missing_file(self):
        from skill_manager.core.commands import find_referenced_skills_in_command

        assert find_referenced_skills_in_command("/no/such/file.md", []) == []

    def test_no_refs_in_body(self, tmp_path):
        from skill_manager.core.commands import find_referenced_skills_in_command

        cmd_file = tmp_path / "plain.md"
        cmd_file.write_text("No skill references here.", encoding="utf-8-sig")
        assert find_referenced_skills_in_command(str(cmd_file), []) == []

    def test_empty_all_skills(self, tmp_path):
        from skill_manager.core.commands import find_referenced_skills_in_command

        cmd_file = tmp_path / "cmd.md"
        cmd_file.write_text("Use /git-pr.", encoding="utf-8-sig")
        assert find_referenced_skills_in_command(str(cmd_file), []) == []
