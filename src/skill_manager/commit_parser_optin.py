"""
Custom commit parser for opt-in release tokens.

Scans commit subjects for [patch], [minor], [major], [dev] tokens.
Only commits containing one of these tokens trigger a version bump.

Usage in pyproject.toml:
    [tool.semantic_release]
    commit_parser = "skill_manager.commit_parser_optin:OptInCommitParser"

The [dev] token is handled by CI passing --as-prerelease to semantic-release
when the latest commit contains [dev].
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic.dataclasses import dataclass
from semantic_release.commit_parser._base import CommitParser, ParserOptions
from semantic_release.commit_parser.token import ParsedCommit, ParseError
from semantic_release.enums import LevelBump

if TYPE_CHECKING:
    from git.objects.commit import Commit


@dataclass
class OptInParserOptions(ParserOptions):
    """Options for the opt-in commit parser."""

    major_token: str = "major"
    """Token that triggers a major version bump: [major]"""

    minor_token: str = "minor"
    """Token that triggers a minor version bump: [minor]"""

    patch_token: str = "patch"
    """Token that triggers a patch version bump: [patch]"""

    dev_token: str = "dev"
    """Token that signals a development pre-release: [dev]"""


class OptInCommitParser(CommitParser[ParsedCommit, OptInParserOptions]):
    """
    Commit parser that only bumps versions when [patch]/[minor]/[major]/[dev]
    tokens are found in the commit subject.

    Commits without any of these tokens are ignored (ParseError).
    The [dev] token is equivalent to a patch bump; the pre-release aspect
    is handled by CI passing --as-prerelease to semantic-release.
    """

    parser_options = OptInParserOptions

    def parse(self, commit: Commit) -> ParsedCommit | ParseError:
        subject = commit.message.split("\n", 1)[0].strip()

        # Check for [major] → highest priority
        if f"[{self.options.major_token}]" in subject:
            return ParsedCommit(
                bump=LevelBump.MAJOR,
                type="major",
                scope="",
                descriptions=[commit.message],
                breaking_descriptions=[f"[{self.options.major_token}] token in commit message"],
                commit=commit,
            )

        # Check for [minor]
        if f"[{self.options.minor_token}]" in subject:
            return ParsedCommit(
                bump=LevelBump.MINOR,
                type="minor",
                scope="",
                descriptions=[commit.message],
                breaking_descriptions=[],
                commit=commit,
            )

        # Check for [patch]
        if f"[{self.options.patch_token}]" in subject:
            return ParsedCommit(
                bump=LevelBump.PATCH,
                type="patch",
                scope="",
                descriptions=[commit.message],
                breaking_descriptions=[],
                commit=commit,
            )

        # Check for [dev] → patch bump (pre-release handled by --as-prerelease in CI)
        if f"[{self.options.dev_token}]" in subject:
            return ParsedCommit(
                bump=LevelBump.PATCH,
                type="dev",
                scope="",
                descriptions=[commit.message],
                breaking_descriptions=[],
                commit=commit,
            )

        # No opt-in token found → no release
        return ParseError(commit=commit, error="No opt-in release token found")
