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
    ownership = {UpdateService._ownership_project_key("/project"): {"old": "pkg_1"}}
    with (
        patch(
            "skill_manager.core.update_service.load_project_skill_ownership", return_value=ownership
        ),
        patch("skill_manager.core.update_service.save_project_skill_ownership") as save_ownership,
        patch("skill_manager.core.update_service.delete_project_skill_folders") as delete,
    ):
        service._cleanup_removed_project_skills(
            [{"folder_name": "old", "package_id": "pkg_1"}], status_cb
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
            [{"folder_name": "old", "package_id": "pkg_1"}], status_cb
        )

    delete.assert_not_called()


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
        UpdateService._record_project_skill_ownership(source_skills, copy_result)

    saved = save_ownership.call_args.args[0]
    assert saved[UpdateService._ownership_project_key("/project/.agents/skills")]["alpha"] == (
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
