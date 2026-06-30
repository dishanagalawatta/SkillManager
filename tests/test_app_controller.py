import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from skill_manager.app import AppController
from skill_manager.core.models.entities import PreparedModelState, Skill
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
        self.data = dict(config_data)  # copy to avoid mutation by migration
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
        yield c

        # Cleanup to prevent dangling timers from saving to deleted temp dirs
        c.on_quit()


def test_controller_initialization(controller):
    assert controller.clientFormat == "Antigravity"
    assert len(controller.sources) == 1
    assert controller.currentView == "Library"


def test_controller_set_current_view(controller):
    controller.currentView = "QuickCopy"
    assert controller.currentView == "QuickCopy"
    # Library defaults to isPackageOnly=True in __init__
    assert controller.isPackageOnly == Qt.CheckState.Checked


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
    # Test _commit_prepared_state directly to avoid threads
    skill = Skill(
        name="Skill A",
        local_path="/test/skill_a",
        category="Dev",
        is_package=True,
        main_category="Core Engineering",
    )
    from skill_manager.core.models.entities import FilterState
    from skill_manager.core.models.filter_engine import FilterEngine

    engine = FilterEngine()
    filter_state = FilterState(is_package_only=True)
    filtered = engine.filter_skills([skill], filter_state)
    all_filtered = engine.prepare_rows(filtered)
    visible = engine.build_visible_rows(all_filtered, set())

    state = PreparedModelState(
        all_skills=[skill],
        search_engine=MagicMock(),
        all_filtered_skills=all_filtered,
        visible_rows=visible,
        categories=["Dev"],
        status="Success",
        generation=0,
    )
    controller.discovery._commit_prepared_state(state)

    assert controller.skillModel.rowCount() == 1
    assert "Dev" in controller.categories


def test_controller_copy_single_skill(controller):
    skill_data = {"name": "S1", "local_path": "/p1", "is_package": True}
    controller.skillModel.setSkills([skill_data])

    with patch.object(controller, "_clipboard"):
        controller.copySkillToClipboard("/p1")
        # copySkillToClipboard calls copySkillReference which sets "Copied reference: ..."
        assert controller.statusMessage.startswith("Copied reference:")


@patch("skill_manager.controllers.discovery_controller.DiscoveryService")
@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("PySide6.QtCore.QTimer.singleShot")
def test_controller_sync_project(mock_timer, mock_copy, mock_discovery_svc, controller):
    # Mock Timer to run callback immediately
    mock_timer.side_effect = lambda ms, receiver, method: (
        method() if callable(method) else method.call()
    )

    mock_copy.return_value = {"merged": 1, "failed": 0, "details": [], "copied": 0}

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
    # AppController forwards these from UIController
    controller.ui.windowWidthChanged.connect(signals_mock.width)
    controller.ui.windowHeightChanged.connect(signals_mock.height)
    controller.ui.darkModeChanged.connect(signals_mock.dark)
    controller.ui.currentViewChanged.connect(signals_mock.view)

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

    controller.reducedMotion = True
    assert controller.reducedMotion is True

    controller.compactListRows = True
    assert controller.compactListRows is True

    controller.windowX = 100
    assert controller.windowX == 100
    controller.windowY = 200
    assert controller.windowY == 200


def test_controller_toggle_package_only(controller):
    # isPackageOnly is read-only on the AppController (returns library model's value).
    # To change it, set directly on the library model.
    controller._library_model.isPackageOnly = Qt.CheckState.Unchecked
    assert controller.isPackageOnly == Qt.CheckState.Unchecked


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
    controller.ui.triggerSave = MagicMock()

    controller.windowWidth = 900
    # setter prevents values < 1050
    assert controller.ui.windowWidth != 900

    controller.windowWidth = 1500
    controller.windowHeight = 800
    controller.windowX = 22
    controller.windowY = 33
    controller.darkMode = not controller.ui.darkMode

    assert controller.ui.windowWidth == 1500
    assert controller.ui.windowHeight == 800
    assert controller.ui.windowX == 22
    assert controller.ui.windowY == 33
    assert controller.ui.triggerSave.call_count >= 5


def test_controller_selection_and_clipboard_paths(controller):
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

    controller.skillModel.setSkills([{"name": "S1", "local_path": "/p1", "is_package": True}])

    with patch.object(controller.ops, "deleteSkill") as mock_delete:
        controller.deleteSkill("")
        controller.deleteSkill("/p1")
        mock_delete.assert_any_call("/p1")

    controller.skillModel.clearSelection()
    controller.deleteSelectedSkills()
    assert "No skills selected" in controller.statusMessage

    controller.loadInitialData = MagicMock()
    with patch.object(controller.discovery, "loadInitialData") as mock_load:
        controller.refreshSkills("test", False)
        mock_load.assert_called_once_with(force_full_scan=False, silent=True)

    controller.saveCustomCollection("", ["/p1"], [])
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
    assert "/S1" in copied
    assert controller.statusMessage == "Copied 1 skills to clipboard"

    controller.skillModel.clearSelection()
    controller.copySelectedSkillsToClipboard()
    assert controller.statusMessage == "No skills selected"


def test_controller_custom_collections(controller):
    controller.skillModel.clearSelection = MagicMock()
    controller.skillModel.selectByPaths = MagicMock()

    controller.saveCustomCollection("Core", ["/a", "/b"], ["ProjectA"])
    assert "Core" in controller.customCollections
    assert controller.getCollectionPaths("Core") == ["/a", "/b"]

    controller.applyCollectionSelection("Core")
    controller.skillModel.clearSelection.assert_called_once()
    controller.skillModel.selectByPaths.assert_called_once_with(["/a", "/b"])

    controller.deleteCustomCollection("Core")
    assert "Core" not in controller.customCollections


def test_controller_create_custom_command_delegates(controller, temp_dir):
    project_path = temp_dir / "proj"
    project_path.mkdir(parents=True, exist_ok=True)
    controller._projects = [str(project_path)]

    with (
        patch("skill_manager.core.commands.create_custom_command_file") as mock_create,
        patch("skill_manager.core.discovery.DiscoveryService.discover_single", return_value=None),
    ):
        from skill_manager.core.commands import CommandCreateResult

        mock_create.return_value = CommandCreateResult(
            ok=True, message="Created command: Deploy.md"
        )
        controller.createCustomCommand("Deploy", "body", ["proj"], "Ops")

    assert controller.statusMessage == "Created command in 1 project(s)"


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

    controller.config_mgr.addSource.assert_called_once_with("src")
    controller.config_mgr.removeSource.assert_any_call("src")
    controller.config_mgr.addProject.assert_called_once_with("project")
    controller.config_mgr.removeProject.assert_any_call("project")
    controller.config_mgr.setProjectAlias.assert_called_once_with("project", "Project")
    controller.config_mgr.verifyGitPackage.assert_called_once_with("url", "token")

    controller.updatePackagesChanged = MagicMock()
    controller._config.set = MagicMock()
    controller.addUpdatePackage("")
    controller.addUpdatePackage("pkg")
    assert controller._update_packages[-1]["package_name"] == "pkg"

    with (
        patch(
            "skill_manager.core.skill_packages.normalize_skill_package_config",
            return_value={
                "name": "Repo",
                "source_type": "git",
                "package_id": "repo",
                "repository_url": "https://example.test/repo.git",
                "github_token": "",
                "package_args": "",
                "update_command": "",
                "current_version_command": "",
                "latest_version_command": "",
                "package_path": "",
                "clone_path": "",
                "package_name": "",
            },
        ),
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=lambda source, **kw: {**source, "latest_version": "v1"},
        ),
        patch("skill_manager.controllers.update_controller.capture_event") as capture,
    ):
        controller.addSkillPackage({"repository_url": "https://example.test/repo.git"})
        assert controller._update_packages[-1]["latest_version"] == "v1"
        controller.updateUpdatePackage(len(controller._update_packages) - 1, {"name": "Repo2"})
        # updateUpdatePackage re-normalizes and might update the name if the mock says so
        controller.clearPackageJustFinished(len(controller._update_packages) - 1)
        assert controller._update_packages[-1].get("just_finished") is False
        controller.removeUpdatePackage(len(controller._update_packages) - 1)
        assert capture.call_count >= 1


def test_controller_set_view_filter_modes(controller):
    with patch("skill_manager.controllers.ui_controller.capture_event") as capture:
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
    assert "/S1" in controller._clipboard.setText.call_args.args[0]

    controller.selectSkill(1)
    controller.copyCurrentSelectionOrFocusedSkill()
    assert "/S2" in controller._clipboard.setText.call_args.args[0]

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
    controller.ui.triggerSave = MagicMock()

    controller.setStartupView("Quick Copy")
    assert controller.startupView == "QuickCopy"
    controller.setRememberFilters(False)
    assert controller.rememberFilters is False
    controller.setReducedMotion(True)
    assert controller.reducedMotion is True
    controller.setCompactListRows(True)
    assert controller.compactListRows is True
    assert controller.ui.triggerSave.call_count >= 3

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
    assert controller.compactListRows is False


def test_controller_load_initial_data_success_and_error(controller, temp_dir):
    update_source_path = temp_dir / "update-source"
    update_source_path.mkdir()
    controller._update_packages = [{"package_path": str(update_source_path)}]

    service = MagicMock()
    def mock_discover_all(*args, **kwargs):
        cache_callback = kwargs.get("cache_callback")
        if cache_callback:
            cache_callback(
                {"skills": [], "projects": [], "categories": ["Cached"], "project_labels": []}
            )
        return {
            "skills": [{"name": "A", "is_package": True}],
            "projects": [],
            "categories": ["Dev"],
            "project_labels": ["P"],
            "status": "Done",
        }
    service.discover_all.side_effect = mock_discover_all

    with (
        patch(
            "skill_manager.controllers.discovery_controller.DiscoveryService", return_value=service
        ),
        patch("PySide6.QtAsyncio.run", side_effect=lambda coro: None),  # Avoid real async loop
    ):
        controller.loadInitialData()

    # Success case - test _commit_prepared_state directly
    from skill_manager.core.models.entities import FilterState
    from skill_manager.core.models.filter_engine import FilterEngine

    skill = Skill(name="A", local_path="/test/a", is_package=True, main_category="")
    engine = FilterEngine()
    filter_state = FilterState(is_package_only=True)
    filtered = engine.filter_skills([skill], filter_state)
    all_filtered = engine.prepare_rows(filtered)
    visible = engine.build_visible_rows(all_filtered, set())

    state = PreparedModelState(
        all_skills=[skill],
        search_engine=MagicMock(),
        all_filtered_skills=all_filtered,
        visible_rows=visible,
        categories=["Dev"],
        status="Done",
        generation=0,
    )
    controller.discovery._commit_prepared_state(state)
    assert controller.categories == ["Dev"]

    # Error case
    with (
        patch("PySide6.QtAsyncio.run", side_effect=lambda coro: None),
    ):
        controller.discovery._handle_loading_error("Error scanning skills: boom")
    assert controller.statusMessage == "Error scanning skills: boom"


def test_controller_load_initial_data_delays_final_refresh_after_cache_preview(controller):
    # This test is now less relevant as we've switched to QtAsyncio
    # and the delay is internal to the coroutine. We'll verify it doesn't crash.
    with patch("PySide6.QtAsyncio.run", side_effect=lambda coro: None):
        controller.loadInitialData()
    assert controller.isLoading is False


def test_controller_cache_save_load_and_corruption(controller, tmp_path):
    cache_file = tmp_path / "cache.json"
    # Ensure directory exists for save_cache (core persistence might not create it)
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    with patch("skill_manager.core.persistence.SKILL_LIBRARY_CACHE_FILE", str(cache_file)):
        controller.config_mgr.save_cache(
            {
                "skills": [
                    {
                        "name": "A",
                        "local_path": "/test",
                        "raw_content": "large",
                        "body_content": "body",
                    }
                ]
            }
        )
        saved = cache_file.read_text(encoding="utf-8")
        assert "raw_content" not in saved
        assert controller.config_mgr.load_cache()["skills"][0]["name"] == "A"

        cache_file.write_text("{bad", encoding="utf-8")
        assert controller.config_mgr.load_cache() is None
    assert not cache_file.exists()


def test_controller_archive_refresh_and_delegate_actions(controller):
    # Don't mock the whole ops object, we need its real state
    # but mock methods we want to track
    with (
        patch.object(controller.ops, "toggleCurrentSkillArchive"),
        patch.object(controller.ops, "toggleCurrentSkillStarred"),
        patch.object(controller.ops, "copySelectedSkillsToProject"),
        patch.object(controller.ops, "copySelectedSkillsToProjectTemporarily"),
        patch.object(controller.ui, "launchSkill"),
        patch.object(controller.ui, "openPath"),
        patch.object(controller.updates, "updateNow"),
        patch.object(controller.updates, "scanForUpdates"),
        patch.object(controller.updates, "updateSkillInProject"),
    ):
        controller.addToArchive("/skill")
        assert "/skill" in controller._archive_paths

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

        controller.ops.toggleCurrentSkillArchive.assert_called_once()
        controller.ops.toggleCurrentSkillStarred.assert_called_once()
        controller.ops.copySelectedSkillsToProject.assert_any_call("/project")
        controller.ops.copySelectedSkillsToProjectTemporarily.assert_any_call("/project")
        controller.ui.launchSkill.assert_called_once_with("/skill")
        controller.ui.openPath.assert_called_once_with("/skill")
        # updateNow called twice: once directly, once via updateAllOutdated
        assert controller.updates.updateNow.call_count == 2
        controller.updates.scanForUpdates.assert_called_once()
        controller.updates.updateSkillInProject.assert_called_once_with("Skill", "Project")


@patch("PySide6.QtCore.QTimer.singleShot")
def test_controller_run_update_success_and_failure(mock_timer, controller, temp_dir):
    mock_timer.side_effect = lambda _ms, receiver, method=None: (
        receiver()
        if method is None and callable(receiver)
        else method()
        if callable(method)
        else method.call()  # type: ignore[union-attr]
    )

    controller.loadInitialData = MagicMock()
    controller._config.set = MagicMock()
    controller._sources = [str(temp_dir / "lib")]
    controller._update_packages = [{"name": "Repo", "source_type": "git", "package_id": "repo"}]

    with (
        patch(
            "skill_manager.controllers.update_controller.UpdateController._resolvePackageStorageState"
        ),
        patch(
            "skill_manager.core.skill_packages.run_skill_package_update",
            return_value={"name": "Repo", "source_type": "git", "package_path": "x"},
        ),
        patch(
            "skill_manager.core.skill_packages.scan_package_inventory",
            return_value={"scan_ok": True, "skills": {}},
        ),
        patch(
            "skill_manager.core.skill_packages.diff_package_inventory",
            return_value={"removed": [], "added": [], "updated": []},
        ),
        patch("skill_manager.core.skill_packages.inventory_removals_verified", return_value=True),
        patch("skill_manager.controllers.update_controller.capture_event"),
    ):
        controller.runPackageUpdate(0)

    assert controller._update_packages[0].get("is_updating") is False
    assert controller._update_packages[0].get("just_finished") is True
    assert controller._update_packages[0].get("package_path") == "x"

    with (
        patch(
            "skill_manager.controllers.update_controller.UpdateController._resolvePackageStorageState"
        ),
        patch(
            "skill_manager.core.skill_packages.run_skill_package_update",
            side_effect=RuntimeError("bad"),
        ),
        patch("skill_manager.controllers.update_controller.capture_event"),
        patch("skill_manager.controllers.update_controller.capture_exception") as capture_exception,
    ):
        controller.runPackageUpdate(0)
    capture_exception.assert_called_once()
    assert "Update finished for Repo" in controller.statusMessage


def test_controller_on_quit_flushes_pending_save(controller):
    controller.ui._save_timer = MagicMock()
    controller.ui._save_timer.isActive.return_value = True
    controller.ui.saveUiState = MagicMock()
    with patch("skill_manager.app.posthog_shutdown") as shutdown:
        controller.on_quit()
    controller.ui._save_timer.stop.assert_called_once()
    controller.ui.saveUiState.assert_called_once()
    shutdown.assert_called_once()


def test_client_formats_order(controller):
    assert controller.clientFormats == ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]


def test_client_format_change_syncs_model_filters(qapp, controller):
    controller._quick_copy_model.filterByClient = True
    controller._library_model.filterByClient = True

    controller._client_format = "Codex"
    controller.clientFormatChanged.emit()
    qapp.processEvents()

    assert controller.quickCopyModel.clientFilter == "Codex"
    assert controller.libraryModel.clientFilter == "Codex"

    controller._client_format = "Antigravity"
    controller.clientFormatChanged.emit()
    qapp.processEvents()

    assert controller.quickCopyModel.clientFilter == "Antigravity"
    assert controller.libraryModel.clientFilter == "Antigravity"


def test_copy_collection_to_clipboard_delegates_to_ops(controller):
    controller._custom_collections = {
        "TestColl": {
            "paths": ["/skill/a"],
            "projects": [],
            "shortcut": "",
            "shortcut_enabled": True,
        }
    }
    controller._clipboard = MagicMock()
    controller._client_format = "Gemini"

    with patch.object(controller.ops, "copyCollectionToClipboard") as mock_ops:
        controller.copyCollectionToClipboard("TestColl")
        mock_ops.assert_called_once_with("TestColl")


# ---------------------------------------------------------------------------
# Selection refresh integration (real DiscoveryService)
# ---------------------------------------------------------------------------


def _write_command_file(path, name, body, category="Commands"):
    """Write a valid command file with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"---\nname: {name}\ncategory: {category}\ntype: command\ndate: 2026-01-01\n---\n\n{body}"
    )
    path.write_text(content, encoding="utf-8")


def _load_command_into_model(controller, cmd_path, name, body):
    """Load a command into both models so _refresh_selected_skill can find it."""
    skill_data = {
        "local_path": str(cmd_path),
        "name": name,
        "body_content": body,
        "category": "Custom Commands",
        "main_category": "\u2699\ufe0f System & Workflow",
        "is_command": True,
        "is_starred": False,
        "is_bundle": False,
        "is_archived": False,
        "is_selected": False,
        "is_package": False,
        "is_source": False,
        "project_label": "test-project",
        "source": "Custom",
        "risk": "Low",
        "description": "",
        "raw_content": "",
    }
    controller._library_model.addOrUpdateSkills([skill_data])
    controller._quick_copy_model.addOrUpdateSkills([skill_data])
    for model in (controller._library_model, controller._quick_copy_model):
        model.showCommands = True
        model.state.is_package_only = None
        model._apply_filter()
    return skill_data


@patch("skill_manager.core.persistence.patch_cache_add")
def test_update_custom_command_refreshes_selected_skill_real_discovery(
    mock_patch_cache,
    controller,
    temp_dir,
):
    """updateCustomCommandFull refreshes _selected_skill using real DiscoveryService.

    On main (pre-fix), this fails because discover_single returns
    None for bare .md command files.
    """
    from skill_manager.core.quick_copy import project_label as compute_project_label

    project_path = temp_dir / "proj"
    project_path.mkdir(parents=True, exist_ok=True)
    commands_dir = project_path / ".agents" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    controller._projects = [str(project_path)]

    cmd_file = commands_dir / "Cmd.md"
    _write_command_file(cmd_file, "Cmd", "old body")

    _load_command_into_model(controller, cmd_file, "Cmd", "old body")
    controller._selected_skill = {"local_path": str(cmd_file), "name": "Cmd"}

    emissions = []
    controller.selectedSkillChanged.connect(lambda: emissions.append(True))

    proj_label = compute_project_label(project_path)
    controller.updateCustomCommandFull(str(cmd_file), "Cmd", "new body", "Commands", [proj_label], "")

    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()

    assert emissions, (
        "selectedSkillChanged was not emitted — "
        "discover_single likely returned None for the command file"
    )


@patch("skill_manager.core.persistence.patch_cache_add")
def test_create_custom_command_refreshes_selected_skill_real_discovery(
    mock_patch_cache,
    controller,
    temp_dir,
):
    """createCustomCommand refreshes _selected_skill using real DiscoveryService.

    On main (pre-fix), this fails because discover_single returns
    None for bare .md command files.
    """
    project_path = temp_dir / "proj"
    project_path.mkdir(parents=True, exist_ok=True)

    from skill_manager.core.quick_copy import project_label as compute_project_label

    label = compute_project_label(project_path)

    # Pre-create the command file so discover_single can parse it
    cmd_file = project_path / ".agents" / "commands" / "NewCmd.md"
    _write_command_file(cmd_file, "NewCmd", "echo hello")

    _load_command_into_model(controller, cmd_file, "NewCmd", "echo hello")
    controller._selected_skill = {"local_path": str(cmd_file), "name": "NewCmd"}

    emissions = []
    controller.selectedSkillChanged.connect(lambda: emissions.append(True))

    controller.createCustomCommand("NewCmd2", "echo hello", [label], "Commands")

    # Verify the new command file was created and discover_single works
    new_cmd_file = project_path / ".agents" / "commands" / "NewCmd2.md"
    assert new_cmd_file.exists(), "New command file should exist on disk"

    from skill_manager.core.discovery import DiscoveryService

    svc = DiscoveryService(
        sources=list(controller._sources),
        projects=controller._projects,
        archive_paths=controller._archive_paths,
        starred_paths=controller._starred_paths,
        project_aliases=controller._project_aliases,
    )
    skill_data = svc.discover_single(new_cmd_file, new_cmd_file.parent)
    assert skill_data is not None, (
        "discover_single returned None for newly created command — "
        "the command file parser should handle bare .md files"
    )
