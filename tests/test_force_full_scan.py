"""Tests for force_full_scan parameter in discovery pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def _parse_skill(path: str) -> dict:
    return {"name": "test", "description": ""}


def _parse_skill_pkg(path: str) -> dict:
    return {"name": "pkg", "description": ""}


def _parse_skill_by_parent(path: str) -> dict:
    return {"name": Path(path).parent.name, "description": ""}


def _cat_test(name: str, text: str, meta: dict) -> dict:
    return {"main_category": "Test", "sub_category": ""}


def _cat_pkg(name: str, text: str, meta: dict) -> dict:
    return {"main_category": "Pkg", "sub_category": ""}


class TestForceFullScan:
    """Tests that force_full_scan bypasses diskcache fingerprint checks."""

    def test_discover_projects_incremental_force_skips_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=True, diskcache fingerprint is not checked."""
        from skill_manager.core.discovery import DiscoveryService

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[], projects=[str(tmp_path)])
        mock_disk_cache = MagicMock()

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            service.discover_projects_incremental(
                mock_disk_cache, _parse_skill, _cat_test, force_full_scan=True
            )
            mock_disk_cache.get.assert_not_called()

    def test_discover_projects_incremental_no_force_checks_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=False, diskcache fingerprint IS checked."""
        from skill_manager.core.discovery import DiscoveryService

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[], projects=[str(tmp_path)])

        cached_project_data = {
            "project_path": str(tmp_path),
            "project_root": str(tmp_path),
            "project_label": "test",
            "skills": [{"name": "cached", "local_path": str(skill_dir)}],
        }
        mock_disk_cache = MagicMock()

        def mock_get(key):
            key_str = str(key)
            if "proj_skills:" in key_str:
                return cached_project_data
            if "dir_fp:" in key_str:
                return "cached-fp"
            return None

        mock_disk_cache.get.side_effect = mock_get

        with patch(
            "skill_manager.core.discovery.compute_dir_fingerprint", return_value="cached-fp"
        ):
            result = service.discover_projects_incremental(
                mock_disk_cache, _parse_skill, _cat_test, force_full_scan=False
            )
            assert mock_disk_cache.get.called
            assert result[0]["skills"][0]["name"] == "cached"

    def test_discover_packages_incremental_force_skips_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=True, package diskcache fingerprint is not checked."""
        from skill_manager.core.discovery import DiscoveryService

        skill_dir = tmp_path / "pkg-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Pkg Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])
        mock_disk_cache = MagicMock()

        with patch(
            "skill_manager.core.discovery.compute_dir_fingerprint", return_value="cached-fp"
        ):
            service.discover_packages_incremental(
                mock_disk_cache, _parse_skill_pkg, _cat_pkg, force_full_scan=True
            )
            mock_disk_cache.get.assert_not_called()

    def test_discover_packages_incremental_no_force_checks_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=False, package diskcache fingerprint IS checked."""
        from skill_manager.core.discovery import DiscoveryService

        skill_dir = tmp_path / "pkg-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Pkg Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])

        cached_skills = [{"name": "cached-pkg", "local_path": str(skill_dir)}]
        mock_disk_cache = MagicMock()

        def mock_get(key):
            key_str = str(key)
            if "pkg_skills:" in key_str:
                return cached_skills
            if "dir_fp:" in key_str:
                return "cached-fp"
            return None

        mock_disk_cache.get.side_effect = mock_get

        with patch(
            "skill_manager.core.discovery.compute_dir_fingerprint", return_value="cached-fp"
        ):
            result = service.discover_packages_incremental(
                mock_disk_cache, _parse_skill_pkg, _cat_pkg, force_full_scan=False
            )
            assert mock_disk_cache.get.called
            assert result[0]["name"] == "cached-pkg"

    def test_refresh_skills_passes_force_to_load(self) -> None:
        """AppController.refreshSkills forwards force_full_scan to loadInitialData."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app.discovery = MagicMock()

        AppController.refreshSkills(app, "test", True)

        app.discovery.cancel_inflight.assert_called_once()
        app.discovery.loadInitialData.assert_called_once_with(force_full_scan=True, silent=True)
