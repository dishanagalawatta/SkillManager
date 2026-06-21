from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.update_service import UpdateService


@pytest.fixture
def service():
    return UpdateService(
        sources=["/src"], projects=["/project"], update_packages=[{"name": "S1", "url": "url1"}]
    )


@patch("skill_manager.core.update_service.run_skill_package_update")
@patch("skill_manager.core.update_service.discover_project_skills")
@patch("skill_manager.core.update_service.discover_package_skills")
@patch("skill_manager.core.update_service.copy_skill_folders_to_projects")
def test_run_global_update(mock_copy, mock_src_disc, mock_proj, mock_src_upd, service):
    mock_src_upd.return_value = {"name": "S1", "removed_folders": ["old_f"]}
    # First call is for cleanup from projects
    mock_proj.return_value = [{"project_label": "P1", "skills": [{"folder_name": "old_f"}]}]
    # Second part is discovery from sources
    mock_src_disc.return_value = [{"folder_name": "new", "name": "New"}]
    mock_copy.return_value = {"merged": 1, "failed": 0}

    status_cb = MagicMock()
    progress_cb = MagicMock()
    comp_cb = MagicMock()

    service.run_global_update_sync(status_cb, progress_cb, comp_cb)

    assert mock_src_upd.called
    mock_copy.assert_called_once_with(
        [{"folder_name": "new", "name": "New"}],
        ["/project"],
        update_only=True,
    )
    assert comp_cb.called
    progress_cb.assert_called_once()


@patch("skill_manager.core.update_service.discover_package_skills")
@patch("skill_manager.core.update_service.discover_project_skills")
@patch("skill_manager.core.update_service.check_skill_package_versions")
def test_scan_for_updates(mock_check, mock_proj, mock_src, service):
    mock_src.return_value = [{"name": "Skill1", "folder_name": "f1"}]
    mock_proj.return_value = [{"project_label": "P1", "skills": []}]
    mock_check.return_value = {"name": "S1", "latest_version": "2.0"}

    status_cb = MagicMock()
    comp_cb = MagicMock()

    service.scan_for_updates_sync(status_cb, comp_cb)

    assert comp_cb.called
    results, sources = comp_cb.call_args[0]
    assert results[0]["status"] == "missing"
    assert sources[0]["latest_version"] == "2.0"
    assert status_cb.called


def test_compare_source_and_project_skills_mixed_statuses():
    results = UpdateService.compare_source_and_project_skills(
        [
            {"name": "A", "folder_name": "a"},
            {"name": "B", "folder_name": "b"},
        ],
        [
            {"project_label": "P1", "skills": [{"folder_name": "a"}]},
            {"project_label": "P2", "skills": [{"folder_name": "a"}, {"folder_name": "b"}]},
        ],
    )

    by_name = {result["folder_name"]: result for result in results}
    assert by_name["a"]["status"] == "up_to_date"
    assert by_name["b"]["status"] == "missing"
    assert by_name["b"]["projects"][0] == {"name": "P1", "status": "missing"}


@patch("skill_manager.core.update_service.run_skill_package_update")
@patch("skill_manager.core.update_service.discover_project_skills")
@patch("skill_manager.core.update_service.discover_package_skills")
@patch("skill_manager.core.update_service.copy_skill_folders_to_projects")
def test_run_global_update_recovers_source_failure(
    mock_copy, mock_src_disc, mock_proj, mock_src_upd, service
):
    mock_src_upd.side_effect = RuntimeError("boom")
    mock_proj.return_value = []
    mock_src_disc.return_value = []
    mock_copy.return_value = {"merged": 0, "failed": 0}
    status_cb = MagicMock()
    progress_cb = MagicMock()
    comp_cb = MagicMock()

    service.run_global_update_sync(status_cb, progress_cb, comp_cb)

    progress_cb.assert_called_once()
    assert progress_cb.call_args.args[1]["is_updating"] is False
    comp_cb.assert_called_once()


@patch("skill_manager.core.update_service.run_skill_package_update")
@patch("skill_manager.core.update_service.discover_project_skills")
@patch("skill_manager.core.update_service.discover_package_skills")
@patch("skill_manager.core.update_service.copy_skill_folders_to_projects")
def test_run_global_update_partial_failure(
    mock_copy, mock_src_disc, mock_proj, mock_src_upd, service
):
    # Two packages, one fails
    service.update_packages = [
        {"name": "S1", "url": "url1"},
        {"name": "S2", "url": "url2"},
    ]

    def side_effect(source, output_callback=None):
        if source["name"] == "S1":
            raise RuntimeError("fail S1")
        return {"name": "S2", "removed_folders": []}

    mock_src_upd.side_effect = side_effect
    mock_proj.return_value = []
    mock_src_disc.return_value = []
    mock_copy.return_value = {"merged": 0, "failed": 0}

    status_cb = MagicMock()
    progress_cb = MagicMock()
    comp_cb = MagicMock()

    service.run_global_update_sync(status_cb, progress_cb, comp_cb)

    # Progress should be called for BOTH packages
    assert progress_cb.call_count == 2
    # One should have error status in its updates
    # The final completion should still be called
    comp_cb.assert_called_once()


@patch("skill_manager.core.update_service.discover_project_skills")
def test_cleanup_removed_project_skills_deletes_matches(mock_proj, service):
    mock_proj.return_value = [
        {
            "project_label": "P",
            "skills": [
                {"folder_name": "old", "project_path": "/project"},
                {"folder_name": "keep", "project_path": "/project"},
            ],
        }
    ]
    status_cb = MagicMock()
    ownership = {UpdateService.ownership_project_key("/project"): {"old": "pkg_1"}}
    with (
        patch(
            "skill_manager.core.update_service.load_project_skill_ownership", return_value=ownership
        ),
        patch("skill_manager.core.update_service.save_project_skill_ownership") as save_ownership,
        patch("skill_manager.core.update_service.delete_project_skill_folders") as delete,
    ):
        service._cleanup_removed_project_skills(
            [{"folder_name": "old", "package_id": "pkg_1", "removal_verified": True}],
            status_cb,
        )

    delete.assert_called_once_with([{"folder_name": "old", "project_path": "/project"}])
    save_ownership.assert_called_once()
    status_cb.assert_called_once()


@patch("skill_manager.core.update_service.discover_project_skills")
def test_cleanup_removed_project_skills_leaves_unowned_matches(mock_proj, service):
    mock_proj.return_value = [
        {"project_label": "P", "skills": [{"folder_name": "old", "project_path": "/project"}]}
    ]
    status_cb = MagicMock()
    with (
        patch("skill_manager.core.update_service.load_project_skill_ownership", return_value={}),
        patch("skill_manager.core.update_service.delete_project_skill_folders") as delete,
    ):
        service._cleanup_removed_project_skills(
            [{"folder_name": "old", "package_id": "pkg_1", "removal_verified": True}], status_cb
        )

    delete.assert_not_called()


@patch("skill_manager.core.update_service.discover_project_skills")
def test_cleanup_removed_project_skills_requires_verified_removal(mock_proj, service):
    mock_proj.return_value = [
        {"project_label": "P", "skills": [{"folder_name": "old", "project_path": "/project"}]}
    ]
    ownership = {UpdateService.ownership_project_key("/project"): {"old": "pkg_1"}}
    with (
        patch(
            "skill_manager.core.update_service.load_project_skill_ownership", return_value=ownership
        ),
        patch("skill_manager.core.update_service.delete_project_skill_folders") as delete,
    ):
        service._cleanup_removed_project_skills(
            [{"folder_name": "old", "package_id": "pkg_1"}], MagicMock()
        )

    delete.assert_not_called()


@patch("skill_manager.core.update_service.discover_project_skills")
def test_cleanup_removed_project_skills_skips_package_storage_path(mock_proj, service, tmp_path):
    package_path = tmp_path / "repo" / ".agents" / "skills"
    package_path.mkdir(parents=True)
    service.sources = []
    service.update_packages = [
        {
            "name": "Pkg",
            "package_id": "pkg_1",
            "package_path": str(package_path),
            "resolved_package_path": str(package_path),
        }
    ]
    mock_proj.return_value = [
        {
            "project_label": "Repo",
            "skills": [{"folder_name": "old", "project_path": str(package_path)}],
        }
    ]
    ownership = {UpdateService.ownership_project_key(str(package_path)): {"old": "pkg_1"}}

    with (
        patch(
            "skill_manager.core.update_service.load_project_skill_ownership",
            return_value=ownership,
        ),
        patch("skill_manager.core.update_service.delete_project_skill_folders") as delete,
    ):
        service._cleanup_removed_project_skills(
            [{"folder_name": "old", "package_id": "pkg_1", "removal_verified": True}],
            MagicMock(),
        )

    delete.assert_not_called()


@patch("skill_manager.core.update_service.save_package_skill_inventory")
@patch("skill_manager.core.update_service.load_package_skill_inventory")
@patch("skill_manager.core.update_service.run_skill_package_update")
@patch("skill_manager.core.update_service.discover_package_skills")
@patch("skill_manager.core.update_service.delete_project_skill_folders")
def test_run_global_update_suppresses_deletion_when_inventory_scan_is_unsafe(
    mock_delete,
    mock_discover,
    mock_update,
    mock_load_inventory,
    mock_save_inventory,
    service,
    temp_dir,
):
    package_path = temp_dir / "missing-package"
    project_path = temp_dir / "project" / ".agents" / "skills"
    project_skill = project_path / "alpha"
    project_skill.mkdir(parents=True)
    (project_skill / "SKILL.md").write_text("project alpha")
    service.projects = [str(project_path)]
    service.update_packages = [
        {
            "name": "Pkg",
            "package_id": "pkg_1",
            "package_path": str(package_path),
            "resolved_package_path": str(package_path),
        }
    ]
    mock_load_inventory.return_value = {
        "pkg_1": {
            "resolved_package_path": str(package_path),
            "skills": {"alpha": {"fingerprint": "old"}},
        }
    }
    mock_update.return_value = {
        "name": "Pkg",
        "package_id": "pkg_1",
        "package_path": str(package_path),
        "resolved_package_path": str(package_path),
    }
    mock_discover.return_value = []
    status_cb = MagicMock()

    service.run_global_update_sync(status_cb, MagicMock(), MagicMock())

    assert project_skill.is_dir()
    mock_delete.assert_not_called()
    saved_inventory = mock_save_inventory.call_args.args[0]
    assert saved_inventory["pkg_1"]["skills"] == {"alpha": {"fingerprint": "old"}}
    assert any("Skipped project deletion" in call.args[0] for call in status_cb.call_args_list)


@patch("skill_manager.core.update_service.save_package_skill_inventory")
@patch("skill_manager.core.update_service.load_project_skill_ownership")
@patch("skill_manager.core.update_service.load_package_skill_inventory")
@patch("skill_manager.core.update_service.run_skill_package_update")
@patch("skill_manager.core.update_service.discover_project_skills")
@patch("skill_manager.core.update_service.discover_package_skills")
@patch("skill_manager.core.update_service.copy_skill_folders_to_projects")
@patch("skill_manager.core.update_service.delete_project_skill_folders")
def test_run_global_update_skips_cleanup_and_sync_for_project_root_conflict(
    mock_delete,
    mock_copy,
    mock_discover_sources,
    mock_discover_projects,
    mock_update,
    mock_load_inventory,
    mock_load_ownership,
    mock_save_inventory,
    tmp_path,
    caplog,
):
    project_root = tmp_path / "repo"
    package_path = project_root / ".agents" / "skills"
    project_skill = package_path / "old"
    project_skill.mkdir(parents=True)
    (project_skill / "SKILL.md").write_text("old")
    service = UpdateService(
        sources=[],
        projects=[str(project_root)],
        update_packages=[
            {
                "name": "skills",
                "package_id": "skills",
                "package_path": str(package_path),
                "resolved_package_path": str(package_path),
            }
        ],
    )
    mock_load_inventory.return_value = {
        "skills": {
            "resolved_package_path": str(package_path),
            "skills": {"old": {"fingerprint": "old"}},
        }
    }
    mock_update.return_value = {
        "name": "skills",
        "package_id": "skills",
        "package_path": str(package_path),
        "resolved_package_path": str(package_path),
    }
    mock_discover_projects.return_value = [
        {
            "project_label": "Repo",
            "skills": [{"folder_name": "old", "project_path": str(package_path)}],
        }
    ]
    mock_load_ownership.return_value = {
        UpdateService.ownership_project_key(str(package_path)): {"old": "skills"}
    }
    mock_discover_sources.return_value = [{"folder_name": "new", "name": "New"}]

    status_cb = MagicMock()
    comp_cb = MagicMock()
    service.run_global_update_sync(status_cb, MagicMock(), comp_cb)

    assert project_skill.is_dir()
    mock_delete.assert_not_called()
    mock_copy.assert_not_called()
    comp_cb.assert_called_once()
    assert "update.path_conflict" in caplog.text
    assert "action=skip_project_cleanup_sync" in caplog.text
    assert "update.project.skipped" in caplog.text
    mock_update.assert_not_called()


@patch("skill_manager.core.update_service.save_package_skill_inventory")
@patch("skill_manager.core.update_service.load_package_skill_inventory")
@patch("skill_manager.core.update_service.run_skill_package_update")
@patch("skill_manager.core.update_service.discover_package_skills")
def test_run_global_update_skips_package_update_for_project_root_conflict(
    mock_discover_sources,
    mock_update,
    mock_load_inventory,
    mock_save_inventory,
    tmp_path,
    caplog,
):
    project_root = tmp_path / "repo"
    package_path = project_root / ".agents" / "skills"
    package_path.mkdir(parents=True)
    service = UpdateService(
        sources=[],
        projects=[str(project_root)],
        update_packages=[
            {
                "name": "skills",
                "package_id": "skills",
                "package_path": str(package_path),
                "resolved_package_path": str(package_path),
            }
        ],
    )
    mock_load_inventory.return_value = {}
    mock_discover_sources.return_value = []

    progress_cb = MagicMock()
    comp_cb = MagicMock()
    service.run_global_update_sync(MagicMock(), progress_cb, comp_cb)

    mock_update.assert_not_called()
    progress_cb.assert_called_once()
    assert progress_cb.call_args.args[1]["is_updating"] is False
    assert "update.package.skipped" in caplog.text


def test_record_project_skill_ownership_for_merged_results():
    source_skills = [{"folder_name": "alpha", "package_id": "pkg_alpha"}]
    copy_result = {
        "details": [
            {
                "skill": "Alpha",
                "project": "/project/.agents/skills",
                "status": "merged",
                "message": "/project/.agents/skills/alpha",
            }
        ]
    }

    with (
        patch("skill_manager.core.update_service.load_project_skill_ownership", return_value={}),
        patch("skill_manager.core.update_service.save_project_skill_ownership") as save_ownership,
    ):
        UpdateService.record_project_skill_ownership(source_skills, copy_result)

    saved = save_ownership.call_args.args[0]
    assert saved[UpdateService.ownership_project_key("/project/.agents/skills")]["alpha"] == (
        "pkg_alpha"
    )


@patch("skill_manager.core.update_service.discover_package_skills")
def test_scan_for_updates_top_level_error_reports_status(mock_src, service):
    mock_src.side_effect = RuntimeError("scan failed")
    status_cb = MagicMock()
    comp_cb = MagicMock()

    service.scan_for_updates_sync(status_cb, comp_cb)

    assert status_cb.call_args_list[-1].args[0] == "Scan failed: scan failed"
    comp_cb.assert_not_called()
