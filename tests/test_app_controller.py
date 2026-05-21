import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from skill_manager.app import AppController
from skill_manager.utils.task_runner import SynchronousTaskRunner


@pytest.fixture
def controller(qapp, mock_config, temp_dir):
    config_data = {
        "sources": [str(temp_dir / "lib")],
        "projects": [str(temp_dir / "proj")],
        "client_format": "Antigravity",
        "ui_state": {"current_view": "Library"},
    }

    # In the real code, load() sets self.data. We'll mock that behavior.
    def mock_load_side_effect(self):
        self.data = config_data
        return self.data

    # Use only ONE patch
    with patch(
        "skill_manager.core.config.ConfigManager.load",
        autospec=True,
        side_effect=mock_load_side_effect,
    ):
        (temp_dir / "lib").mkdir(exist_ok=True)
        (temp_dir / "proj").mkdir(exist_ok=True)

        c = AppController(skip_initial_load=True)
        c.task_runner = SynchronousTaskRunner()
        # Explicitly set values that might have been missed due to timing of __init__
        c._sources = config_data["sources"]
        c._projects = config_data["projects"]
        c._client_format = config_data["client_format"]
        return c


def test_controller_initialization(controller):
    assert controller.clientFormat == "Antigravity"
    assert len(controller.sources) == 1
    assert controller.currentView == "Library"


def test_controller_set_current_view(controller):
    controller.currentView = "QuickCopy"
    assert controller.currentView == "QuickCopy"
    # isPackageOnly returns CheckState (Unchecked=0, Checked=2, Partially=1)
    assert controller.skillModel.isPackageOnly == Qt.Unchecked


def test_controller_add_remove_source(controller):
    controller.addSource("/new/source")
    expected = os.path.abspath("/new/source")
    assert expected in controller.sources
    controller.removeSource(expected)
    assert expected not in controller.sources


def test_controller_status_message(controller):
    controller._set_status("Test status")
    assert controller.statusMessage == "Test status"


def test_controller_load_initial_data_logic(controller):
    # Test _finalize_loading directly to avoid threads
    skills = [{"name": "Skill A", "category": "Dev", "is_package": True}]
    controller._finalize_loading(
        all_skills=skills, _projects_state=[], cats=["Dev"], proj_labels=[], status="Success"
    )

    assert controller.skillModel.rowCount() == 1
    assert "Dev" in controller.categories
    assert controller.isLoading is False


def test_controller_copy_single_skill(controller):
    skill_data = {"name": "S1", "local_path": "/p1", "is_package": True}
    controller.skillModel.setSkills([skill_data])

    with patch.object(controller, "_clipboard"):
        controller.copySkillToClipboard("/p1")
        # copySkillToClipboard calls copySkillReference which sets "Copied reference: ..."
        assert controller.statusMessage.startswith("Copied reference:")


@patch("skill_manager.app.DiscoveryService")
@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("PySide6.QtCore.QTimer.singleShot")
def test_controller_sync_project(
    mock_timer, mock_copy, mock_discovery_svc, controller
):
    # Mock Timer to run callback immediately
    mock_timer.side_effect = lambda ms, receiver, method: (
        method() if callable(method) else method.call()
    )

    mock_copy.return_value = {"merged": 1, "failed": 0}

    # Ensure projects list is not empty
    controller._projects = ["/some/project"]
    controller.syncProject(controller.projects[0])

    mock_copy.assert_called_once()
    assert "Update complete for" in controller.statusMessage


def test_controller_setters(controller):
    controller.setClientFormat("Codex")
    assert controller.clientFormat == "Codex"
    assert controller.logoSource.endswith("codex.svg")

    controller.setViewFilter("category", "Dev")
    assert controller.skillModel.categoryFilter == "Dev"

    controller.currentView = "QuickCopy"
    controller.setViewFilter("project", "Proj")
    assert controller.skillModel.projectFilter == "Proj"

    controller.setViewFilter("collection", "true")
    assert controller.skillModel.collectionFilter is True

    # Test more properties and signals
    signals_mock = MagicMock()
    controller.windowWidthChanged.connect(signals_mock.width)
    controller.windowHeightChanged.connect(signals_mock.height)
    controller.darkModeChanged.connect(signals_mock.dark)
    controller.currentViewChanged.connect(signals_mock.view)

    controller.windowWidth = 1200
    assert controller.windowWidth == 1200
    signals_mock.width.assert_called()

    controller.windowHeight = 800
    assert controller.windowHeight == 800
    signals_mock.height.assert_called()

    controller.darkMode = True
    assert controller.darkMode is True
    signals_mock.dark.assert_called()

    controller.currentView = "Library"
    assert controller.currentView == "Library"
    signals_mock.view.assert_called()

    controller.startupView = "Updates"
    assert controller.startupView == "Updates"

    controller.rememberFilters = True
    assert controller.rememberFilters is True

    controller.defaultProjectFilter = "all"
    assert controller.defaultProjectFilter == "all"

    controller.reducedMotion = True
    assert controller.reducedMotion is True

    controller.compactListRows = True
    assert controller.compactListRows is True

    controller.windowX = 100
    assert controller.windowX == 100
    controller.windowY = 200
    assert controller.windowY == 200


def test_controller_toggle_package_only(controller):
    controller.isPackageOnly = True
    # isPackageOnly returns CheckState int
    assert controller.isPackageOnly


def test_controller_logo_and_category_delegate(controller):
    assert controller.logoSource.endswith("antigravity.svg")
    assert controller.getLogoSource("Gemini CLI").endswith("gemini-cli.svg")
    assert controller.getCategoryEmoji("testing") == "🧪"


def test_controller_update_projects_counts_and_ignores_bad_paths(controller, temp_dir):
    project = temp_dir / "proj"
    skills_project = project / ".agents" / "skills"
    skills_project.mkdir(parents=True)
    (skills_project / "skill-a").mkdir()
    (project / "file.txt").write_text("x")
    controller._projects = [str(project), str(temp_dir / "missing")]
    controller._syncing_projects = [str(project)]

    results = controller.updateProjects

    assert results[0]["skill_count"] == 1
    assert results[0]["is_updating"] is True
    assert results[1]["skill_count"] == 0


def test_controller_window_and_theme_setters_emit(controller):
    controller.windowWidthChanged = MagicMock()
    controller.windowHeightChanged = MagicMock()
    controller.windowXChanged = MagicMock()
    controller.windowYChanged = MagicMock()
    controller.darkModeChanged = MagicMock()
    controller.ui.trigger_save = MagicMock()

    controller.windowWidth = 900
    assert controller.ui._window_width != 900

    controller.windowWidth = 1500
    controller.windowHeight = 800
    controller.windowX = 22
    controller.windowY = 33
    controller.darkMode = not controller.ui._dark_mode

    assert controller.ui._window_width == 1500
    assert controller.ui._window_height == 800
    assert controller.ui._window_x == 22
    assert controller.ui._window_y == 33
    assert controller.ui.trigger_save.call_count >= 5


def test_controller_selection_and_clipboard_paths(controller):
    controller.selectedSkillChanged = MagicMock()
    controller.skillModel.setSkills([{"name": "S1", "local_path": "/p1", "is_package": True}])

    controller.selectSkill(0)
    assert controller.selectedSkill["name"] == "S1"
    controller.selectSkill(-1)
    assert controller.selectedSkill == {}

    controller._clipboard = MagicMock()
    controller.copyTextToClipboard("hello")
    controller._clipboard.setText.assert_called_with("hello")
    assert controller.statusMessage == "Copied to clipboard"


def test_controller_small_branch_slots(controller):
    controller._clipboard = MagicMock()
    controller.copySkillReference({"name": "S1", "folder_name": "s1"}, "topic")
    assert controller._clipboard.setText.call_args.args[0].endswith("(topic)")

    controller.ops = MagicMock()
    controller.skillModel.setSkills([{"name": "S1", "local_path": "/p1", "is_package": True}])
    controller.deleteSkill("")
    controller.deleteSkill("/p1")
    controller.ops.delete_skills.assert_called_once()

    controller.skillModel.clearSelection()
    controller.deleteSelectedSkills()
    assert controller.statusMessage == "No skills selected for deletion"

    controller.load_initial_data = MagicMock()
    controller.refreshSkills()
    assert controller.statusMessage == "Refreshing library..."
    controller.load_initial_data.assert_called_once()

    controller.saveCustomCollection("", ["/p1"])
    assert "" not in controller.customCollections

    controller.syncProject("/not-a-project")
    assert "/not-a-project" not in controller.syncingProjects


def test_controller_copy_selected_skills_to_clipboard(controller):
    skills = [
        {"name": "S1", "local_path": "/p1", "folder_name": "skill-one", "is_package": True},
        {"name": "S2", "local_path": "/p2", "folder_name": "skill-two", "is_package": True},
    ]
    controller.skillModel.setSkills(skills)
    controller.skillModel.selectByPaths(["/p1", "/missing"])
    controller._clipboard = MagicMock()

    controller.copySelectedSkillsToClipboard()

    copied = controller._clipboard.setText.call_args.args[0]
    assert "/skill:S1" in copied
    assert "/missing" in copied
    assert controller.statusMessage == "Copied 2 skills to clipboard"

    controller.skillModel.clearSelection()
    controller.copySelectedSkillsToClipboard()
    assert controller.statusMessage == "No skills selected"


def test_controller_custom_collections(controller):
    controller.customCollectionsChanged = MagicMock()
    controller.skillModel.clearSelection = MagicMock()
    controller.skillModel.selectByPaths = MagicMock()

    controller.saveCustomCollection("Core", ["/a", "/b"])
    assert controller.customCollections == ["Core"]
    assert controller.getCollectionPaths("Core") == ["/a", "/b"]

    controller.applyCollectionSelection("Core")
    controller.skillModel.clearSelection.assert_called_once()
    controller.skillModel.selectByPaths.assert_called_once_with(["/a", "/b"])

    controller.deleteCustomCollection("Core")
    assert controller.customCollections == []


def test_controller_create_custom_command_delegates(controller, temp_dir):
    project_path = temp_dir / "proj" / ".agents" / "skills"
    project_path.mkdir(parents=True)
    controller._projects = [str(project_path)]
    controller.refreshSkills = MagicMock()

    controller.createCustomCommand("Deploy", "Codex", "body", "proj", "Ops")

    assert (project_path / "commands" / "Deploy.Codex.md").exists()
    assert controller.statusMessage == "Created command: Deploy.Codex.md"
    controller.refreshSkills.assert_called_once()


def test_controller_config_and_update_source_slots(controller):
    controller.config_mgr = MagicMock()
    controller.addSource("src")
    controller.removeSource("src")
    controller.removeSourceByIndex(0)
    controller.addProject("project")
    controller.removeProject("project")
    controller.removeUpdateProject(0)
    controller.setProjectAlias("project", "Project")
    controller.verifyGitPackage("url", "token")
    controller.config_mgr.add_source.assert_called_once_with("src")
    controller.config_mgr.remove_source.assert_any_call("src")
    controller.config_mgr.add_project.assert_called_once_with("project")
    controller.config_mgr.remove_project.assert_any_call("project")
    controller.config_mgr.set_project_alias.assert_called_once_with("project", "Project")
    controller.config_mgr.verify_git_package.assert_called_once_with("url", "token")

    controller.updatePackagesChanged = MagicMock()
    controller._config.set = MagicMock()
    controller.addUpdatePackage("")
    controller.addUpdatePackage("pkg")
    assert controller._update_packages[-1]["package_name"] == "pkg"

    with (
        patch(
            "skill_manager.core.skill_packages.normalize_skill_package_config",
            return_value={"name": "Repo", "source_type": "git"},
        ),
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=lambda source: {**source, "latest_version": "v1"},
        ),
        patch("skill_manager.app.capture_event") as capture,
    ):
        controller.addSkillPackage({})
        controller.addSkillPackage({"repository_url": "https://example.test/repo.git"})
        assert controller._update_packages[-1]["latest_version"] == "v1"
        controller.updateUpdatePackage(len(controller._update_packages) - 1, {"name": "Repo2"})
        assert controller._update_packages[-1]["name"] == "Repo"
        controller.clearPackageJustFinished(len(controller._update_packages) - 1)
        assert controller._update_packages[-1]["just_finished"] is False
        controller.removeUpdatePackage(len(controller._update_packages) - 1)
        assert capture.call_count >= 2


def test_controller_set_view_filter_modes(controller):
    with patch("skill_manager.app.capture_event") as capture:
        controller.currentView = "Library"
        controller.setViewFilter("category", "Testing")
    assert controller.libraryModel.categoryFilter == "Testing"
    assert controller.quickCopyModel.categoryFilter == ""
    capture.assert_called_once()

    controller.currentView = "QuickCopy"
    controller.setViewFilter("category", "Automation")
    assert controller.libraryModel.categoryFilter == "Testing"
    assert controller.quickCopyModel.categoryFilter == "Automation"

    controller.setViewFilter("collection", "true")
    assert controller.quickCopyModel.collectionFilter is True
    assert controller.libraryModel.collectionFilter is False
    controller.setViewFilter("collection", "")
    assert controller.quickCopyModel.collectionFilter is False

    controller.setViewFilter("project", "Proj")
    assert controller.quickCopyModel.projectFilter == "Proj"
    assert controller.libraryModel.projectFilter == ""
    controller.setViewFilter("clear", "")
    assert controller.quickCopyModel.projectFilter == ""
    assert controller.libraryModel.categoryFilter == "Testing"
    assert controller.quickCopyModel.filterText == ""

    controller.setViewFilterForView("Library", "clear", "")
    assert controller.libraryModel.categoryFilter == ""


def test_controller_daily_speed_actions(controller):
    skills = [
        {"name": "S1", "local_path": "/p1", "folder_name": "skill-one", "is_package": True},
        {"name": "S2", "local_path": "/p2", "folder_name": "skill-two", "is_package": True},
    ]
    controller.skillModel.setSkills(skills)
    controller._clipboard = MagicMock()

    controller.copyCurrentSelectionOrFocusedSkill()
    assert "/skill:S1" in controller._clipboard.setText.call_args.args[0]

    controller.selectSkill(1)
    controller.copyCurrentSelectionOrFocusedSkill()
    assert "/skill:S2" in controller._clipboard.setText.call_args.args[0]

    controller.selectAllVisibleSkills()
    assert controller.skillModel.selectedCount == 2
    controller.copyCurrentSelectionOrFocusedSkill()
    assert controller.statusMessage == "Copied 2 skills to clipboard"

    controller.clearVisibleSelection()
    assert controller.skillModel.selectedCount == 0
    assert controller.statusMessage == "Selection cleared"

    controller.toggleAllVisibleCategories()
    assert "categories" in controller.statusMessage


def test_controller_daily_speed_preferences(controller):
    controller.ui.trigger_save = MagicMock()
    controller.startupViewChanged = MagicMock()
    controller.rememberFiltersChanged = MagicMock()
    controller.defaultProjectFilterChanged = MagicMock()
    controller.reducedMotionChanged = MagicMock()
    controller.compactListRowsChanged = MagicMock()

    controller.setStartupView("Quick Copy")
    assert controller.startupView == "QuickCopy"
    controller.setRememberFilters(False)
    assert controller.rememberFilters is False
    controller.setDefaultProjectFilter("all")
    assert controller.defaultProjectFilter == "all"
    controller.setReducedMotion(True)
    assert controller.reducedMotion
    controller.setCompactListRows(True)
    assert controller.compactListRows
    assert controller.ui.trigger_save.call_count >= 4

    controller.libraryModel.filterText = "abc"
    controller.quickCopyModel.categoryFilter = "Testing"
    controller.currentView = "Library"
    controller.clearViewFilters()
    assert controller.libraryModel.filterText == ""
    assert controller.quickCopyModel.categoryFilter == "Testing"

    controller.resetUiState()
    assert controller.currentView == "Library"
    assert controller.startupView == "Library"
    assert controller.rememberFilters is True
    assert controller.defaultProjectFilter == "last"
    assert controller.compactListRows is False


@patch("PySide6.QtCore.QTimer.singleShot")
def test_controller_load_initial_data_success_and_error(
    mock_timer, controller, temp_dir
):
    mock_timer.side_effect = lambda _ms, receiver, method=None: (
        receiver()
        if method is None and callable(receiver)
        else method()
        if callable(method)
        else method.call()
    )

    update_source_path = temp_dir / "update-source"
    update_source_path.mkdir()
    controller._update_packages = [{"package_path": str(update_source_path)}]

    service = MagicMock()
    service.discover_all.side_effect = lambda cache_callback: (
        cache_callback(
            {"skills": [], "projects": [], "categories": ["Cached"], "project_labels": []}
        )
        or {
            "skills": [{"name": "A", "is_package": True}],
            "projects": [],
            "categories": ["Dev"],
            "project_labels": ["P"],
            "status": "Done",
        }
    )
    with patch("skill_manager.app.DiscoveryService", return_value=service):
        controller.load_initial_data()
    assert controller.categories == ["Dev"]
    assert controller.statusMessage == "Done"

    failing_service = MagicMock()
    failing_service.discover_all.side_effect = RuntimeError("boom")
    with patch("skill_manager.app.DiscoveryService", return_value=failing_service):
        controller.load_initial_data()
    assert controller.statusMessage == "Error scanning skills: boom"


def test_controller_cache_save_load_and_corruption(controller, tmp_path):
    cache_file = tmp_path / "cache.json"
    with patch("skill_manager.core.config.SKILL_LIBRARY_CACHE_FILE", str(cache_file)):
        controller._save_cache(
            {"skills": [{"name": "A", "raw_content": "large", "body_content": "body"}]}
        )
        saved = cache_file.read_text(encoding="utf-8")
        assert "raw_content" not in saved
        assert controller._load_cache()["skills"][0]["name"] == "A"

        cache_file.write_text("{bad", encoding="utf-8")
        assert controller._load_cache() is None
    assert not cache_file.exists()


def test_controller_archive_refresh_and_delegate_actions(controller):
    controller.load_initial_data = MagicMock()
    controller._save_archive = MagicMock()
    controller._save_starred = MagicMock()
    controller.ops = MagicMock()
    controller.ui = MagicMock()
    controller.updates = MagicMock()

    controller.addToArchive("/skill")
    assert "/skill" in controller._archive_paths
    controller.load_initial_data.assert_called_once()

    controller.toggleCurrentSkillArchive()
    controller.toggleCurrentSkillStarred()
    controller.copySelectedSkillsToProject("/project")
    controller.copySelectedSkillsToProjectTemporarily("/project")
    controller.launchSkill("/skill")
    controller.openPath("/skill")
    controller.updateNow()
    controller.scanForUpdates()
    controller.updateAllOutdated()
    controller.updateSkillInProject("Skill", "Project")

    controller.ops.toggle_archive.assert_called_once()
    controller.ops.toggle_starred.assert_called_once()
    controller.ops.copy_selected_to_project.assert_any_call("/project")
    controller.ops.copy_selected_to_project.assert_any_call("/project", is_temporary=True)
    controller.ui.launch_skill.assert_called_once_with("/skill")
    controller.ui.open_path.assert_called_once_with("/skill")
    assert controller.updates.update_now.call_count == 2
    controller.updates.scan_for_updates.assert_called_once()
    controller.updates.update_skill_in_project.assert_called_once_with("Skill", "Project")


@patch("PySide6.QtCore.QTimer.singleShot")
def test_controller_run_update_success_and_failure(mock_timer, controller, temp_dir):
    mock_timer.side_effect = lambda _ms, receiver, method=None: (
        receiver()
        if method is None and callable(receiver)
        else method()
        if callable(method)
        else method.call()
    )

    controller.load_initial_data = MagicMock()
    controller.updatePackagesChanged = MagicMock()
    controller._config.set = MagicMock()
    controller._sources = [str(temp_dir / "lib")]
    controller._update_packages = [{"name": "Repo", "source_type": "git"}]

    with (
        patch(
            "skill_manager.core.skill_packages.run_skill_package_update",
            return_value={"name": "Repo", "source_type": "git", "package_path": "x"},
        ),
        patch("skill_manager.app.capture_event"),
    ):
        controller.runPackageUpdate(0)
    assert controller._update_packages[0]["is_updating"] is False
    assert controller._update_packages[0]["just_finished"] is True
    assert controller._update_packages[0]["package_path"] == "x"

    with (
        patch(
            "skill_manager.core.skill_packages.run_skill_package_update",
            side_effect=RuntimeError("bad"),
        ),
        patch("skill_manager.app.capture_event"),
        patch("skill_manager.app.capture_exception") as capture_exception,
    ):
        controller.runPackageUpdate(0)
    capture_exception.assert_called_once()
    assert controller.statusMessage == "Update finished for Repo"


def test_controller_on_quit_flushes_pending_save(controller):
    controller.ui._save_timer = MagicMock()
    controller.ui._save_timer.isActive.return_value = True
    controller.ui.save_ui_state = MagicMock()
    with patch("skill_manager.app.posthog_shutdown") as shutdown:
        controller.on_quit()
    controller.ui._save_timer.stop.assert_called_once()
    controller.ui.save_ui_state.assert_called_once()
    shutdown.assert_called_once()


def test_client_formats_order(controller):
    assert controller.clientFormats == ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]

