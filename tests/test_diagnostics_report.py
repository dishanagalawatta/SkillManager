"""Tests for the report-issue backend: prefilled GitHub issues/new URL builder."""

from __future__ import annotations

from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

from skill_manager.controllers.config_controller import ConfigController
from skill_manager.core import diagnostics as diag_mod
from skill_manager.core.diagnostics import app_version, build_report_issue_url
from skill_manager.core.release_check_service import GITHUB_REPO


def _parse(url: str) -> dict:
    parts = urlparse(url)
    assert parts.scheme == "https"
    assert parts.netloc == "github.com"
    assert parts.path == f"/{GITHUB_REPO}/issues/new"
    return parse_qs(parts.query)


def test_url_points_to_repo_issues_new():
    qs = _parse(build_report_issue_url("crash on start", "it broke"))
    assert "title" in qs and "body" in qs


def test_url_contains_version_and_health(monkeypatch):
    monkeypatch.setattr(diag_mod.get_diagnostic_logger(), "get_health_status", lambda: "red")
    monkeypatch.setattr(
        diag_mod.get_diagnostic_logger(),
        "get_diagnostic_counts",
        lambda: {"errors": 2, "warnings": 1, "info": 3, "total": 6},
    )
    qs = _parse(build_report_issue_url("oops", "details"))
    body = qs["body"][0]
    assert app_version() in body
    assert "red" in body
    assert "errors=2" in body
    assert "Log path" in body


def test_url_encodes_special_characters():
    summary = "crash & burn? #1"
    qs = _parse(build_report_issue_url(summary, "a+b & c"))
    assert qs["title"][0] == summary
    assert "a+b & c" in qs["body"][0]


def test_empty_summary_uses_default_title():
    qs = _parse(build_report_issue_url("", ""))
    assert "SkillManager" in qs["title"][0]


def test_slot_delegates_to_builder():
    app = MagicMock()
    controller = ConfigController(app)
    url = controller.getReportIssueUrl("hello", "world")
    qs = _parse(url)
    assert qs["title"][0] == "hello"
    assert "world" in qs["body"][0]


def test_get_report_bundle_path_exports_zip(tmp_path):
    app = MagicMock()
    controller = ConfigController(app)
    path = controller.getReportBundlePath(str(tmp_path))
    assert path.endswith(".zip")
