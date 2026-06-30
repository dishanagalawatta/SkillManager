"""Tests for post-scan path verification in discovery."""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch


def _parse_test(path: str) -> dict:
    return {"name": "test", "description": ""}


def _parse_by_parent(path: str) -> dict:
    return {"name": Path(path).parent.name, "description": ""}


def _cat_test(name: str, text: str, meta: dict) -> dict:
    return {"main_category": "Test", "sub_category": ""}


class TestDiscoveryVerifiesPaths:
    """Tests that discovery removes skills with missing local_path."""

    def test_packages_verification_removes_missing(self, tmp_path: Path) -> None:
        """discover_packages_incremental removes skills whose local_path is gone."""
        from skill_manager.core.discovery import DiscoveryService

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])

        mock_disk_cache = MagicMock()
        mock_disk_cache.get.return_value = None

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            result = service.discover_packages_incremental(mock_disk_cache, _parse_test, _cat_test, force_full_scan=True)
            assert len(result) == 1
            assert result[0]["name"] == "test"

        shutil.rmtree(skill_dir)

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp2"):
            result = service.discover_packages_incremental(mock_disk_cache, _parse_test, _cat_test, force_full_scan=True)
            assert len(result) == 0

    def test_projects_verification_removes_missing(self, tmp_path: Path) -> None:
        """discover_projects_incremental removes skills whose local_path is gone."""
        from skill_manager.core.discovery import DiscoveryService

        skill1 = tmp_path / "skill-a"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill A\n", encoding="utf-8")

        skill2 = tmp_path / "skill-b"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill B\n", encoding="utf-8")

        service = DiscoveryService(sources=[], projects=[str(tmp_path)])

        mock_disk_cache = MagicMock()
        mock_disk_cache.get.return_value = None

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            result = service.discover_projects_incremental(mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True)
            assert len(result) == 1
            assert len(result[0]["skills"]) == 2

        shutil.rmtree(skill1)

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp2"):
            result = service.discover_projects_incremental(mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True)
            assert len(result) == 1
            assert len(result[0]["skills"]) == 1
            assert result[0]["skills"][0]["name"] == "skill-b"

    def test_verification_keeps_existing_skills(self, tmp_path: Path) -> None:
        """Verification only removes missing skills, keeps existing ones."""
        from skill_manager.core.discovery import DiscoveryService

        skill1 = tmp_path / "skill-1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill 1\n", encoding="utf-8")

        skill2 = tmp_path / "skill-2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill 2\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])

        mock_disk_cache = MagicMock()
        mock_disk_cache.get.return_value = None

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            result = service.discover_packages_incremental(mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True)
            assert len(result) == 2

        shutil.rmtree(skill1)

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp2"):
            result = service.discover_packages_incremental(mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True)
            assert len(result) == 1
            assert result[0]["name"] == "skill-2"
