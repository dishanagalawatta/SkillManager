"""Tests for OptInCommitParser."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from skill_manager.commit_parser_optin import OptInCommitParser


@pytest.fixture
def parser():
    return OptInCommitParser()


def _make_commit(subject: str) -> MagicMock:
    commit = MagicMock()
    commit.message = f"{subject}\n\nBody text here."
    return commit


class TestOptInCommitParser:
    def test_major_token(self, parser):
        result = parser.parse(_make_commit("feat: add [major] feature"))
        assert result.type == "major"
        assert result.breaking_descriptions

    def test_minor_token(self, parser):
        result = parser.parse(_make_commit("feat: add [minor] feature"))
        assert result.type == "minor"
        assert result.breaking_descriptions == []

    def test_patch_token(self, parser):
        result = parser.parse(_make_commit("fix: [patch] bug"))
        assert result.type == "patch"
        assert result.breaking_descriptions == []

    def test_dev_token(self, parser):
        result = parser.parse(_make_commit("chore: [dev] WIP"))
        assert result.type == "dev"
        assert result.breaking_descriptions == []

    def test_no_token_returns_error(self, parser):
        result = parser.parse(_make_commit("chore: no token here"))
        assert hasattr(result, "error")
        assert "No opt-in" in result.error

    def test_major_takes_priority_over_minor(self, parser):
        result = parser.parse(_make_commit("feat: [major] and [minor]"))
        assert result.type == "major"

    def test_minor_takes_priority_over_patch(self, parser):
        result = parser.parse(_make_commit("feat: [minor] and [patch]"))
        assert result.type == "minor"
