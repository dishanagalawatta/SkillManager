"""Per-project task list: persistence, isolation, and the clipboard prompt."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from skill_manager.core import tasks as task_store
from skill_manager.core.schemas import ProjectTaskRecord, ProjectTasksState


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """Point the task store at a scratch data dir for every test."""
    import importlib

    import skill_manager.core.config as config_mod

    monkeypatch.setenv("SKILL_MANAGER_DATA_DIR", str(tmp_path / "data"))
    importlib.reload(config_mod)
    import skill_manager.core.tasks as tasks_mod

    importlib.reload(tasks_mod)
    yield tasks_mod
    importlib.reload(config_mod)


def _project(tmp_path: Path, name: str) -> Path:
    proj = tmp_path / name
    proj.mkdir(parents=True)
    return proj


# ── schema ────────────────────────────────────────────────────────────────


def test_task_record_validation():
    """A task needs a title; priority and defaults are sane."""
    record = ProjectTaskRecord(title="Ship the release")
    assert record.title == "Ship the release"
    assert record.completed is False
    assert record.priority == "medium"
    assert record.linked_skills == []
    assert record.id

    with pytest.raises(ValidationError):
        ProjectTaskRecord(title="")

    with pytest.raises(ValidationError):
        ProjectTaskRecord(title="x", priority="urgent")


def test_task_record_strips_title():
    assert ProjectTaskRecord(title="  padded  ").title == "padded"


# ── persistence ──────────────────────────────────────────────────────────


def test_tasks_persist_across_reloads(tmp_path):
    """Tasks written in one session are readable in the next."""
    proj = _project(tmp_path, "projA")

    created = task_store.add_task(str(proj), "Write the release notes")
    assert created is not None
    assert created.title == "Write the release notes"

    reloaded = task_store.get_tasks(str(proj))
    assert len(reloaded) == 1
    assert reloaded[0].id == created.id
    assert reloaded[0].title == "Write the release notes"


def test_tasks_are_isolated_per_project(tmp_path):
    """A task in project A never leaks into project B."""
    proj_a = _project(tmp_path, "projA")
    proj_b = _project(tmp_path, "projB")

    task_store.add_task(str(proj_a), "Only in A")

    assert len(task_store.get_tasks(str(proj_a))) == 1
    assert task_store.get_tasks(str(proj_b)) == []


def test_project_key_ignores_a_trailing_separator(tmp_path):
    """The same project addressed differently maps to the same list."""
    proj = _project(tmp_path, "projA")
    task_store.add_task(str(proj), "One")

    key = task_store.project_task_key(str(proj))
    assert key == task_store.project_task_key(str(proj) + "/")

    # A trailing separator must not create a second list.
    assert len(task_store.get_tasks(str(proj) + "/")) == 1


def test_add_task_rejects_empty_title(tmp_path):
    proj = _project(tmp_path, "projA")
    assert task_store.add_task(str(proj), "   ") is None
    assert task_store.get_tasks(str(proj)) == []


def test_add_task_normalises_unknown_priority(tmp_path):
    proj = _project(tmp_path, "projA")
    record = task_store.add_task(str(proj), "Task", priority="urgent")
    assert record is not None
    assert record.priority == "medium"


def test_update_task_changes_fields(tmp_path):
    proj = _project(tmp_path, "projA")
    record = task_store.add_task(str(proj), "Old title", priority="low")
    assert record is not None

    updated = task_store.update_task(
        str(proj),
        record.id,
        title="New title",
        description="Some notes",
        priority="high",
    )
    assert updated is not None
    assert updated.title == "New title"
    assert updated.description == "Some notes"
    assert updated.priority == "high"


def test_update_task_leaves_untouched_fields_alone(tmp_path):
    proj = _project(tmp_path, "projA")
    record = task_store.add_task(str(proj), "Title", description="Notes")
    assert record is not None

    updated = task_store.update_task(str(proj), record.id, title="New")
    assert updated is not None
    assert updated.description == "Notes"
    assert updated.title == "New"


def test_toggle_task_flips_completion(tmp_path):
    proj = _project(tmp_path, "projA")
    record = task_store.add_task(str(proj), "Toggle me")
    assert record is not None
    assert record.completed is False

    toggled = task_store.toggle_task(str(proj), record.id)
    assert toggled is not None
    assert toggled.completed is True

    toggled = task_store.toggle_task(str(proj), record.id)
    assert toggled is not None
    assert toggled.completed is False


def test_delete_task(tmp_path):
    proj = _project(tmp_path, "projA")
    record = task_store.add_task(str(proj), "Delete me")
    assert record is not None

    assert task_store.delete_task(str(proj), record.id) is True
    assert task_store.get_tasks(str(proj)) == []
    assert task_store.delete_task(str(proj), record.id) is False


def test_clear_completed_tasks(tmp_path):
    proj = _project(tmp_path, "projA")
    done = task_store.add_task(str(proj), "Done one")
    task_store.add_task(str(proj), "Open one")
    assert done is not None
    task_store.toggle_task(str(proj), done.id)

    removed = task_store.clear_completed_tasks(str(proj))
    assert removed == 1
    remaining = task_store.get_tasks(str(proj))
    assert [r.title for r in remaining] == ["Open one"]


def test_reorder_tasks(tmp_path):
    proj = _project(tmp_path, "projA")
    first = task_store.add_task(str(proj), "First")
    second = task_store.add_task(str(proj), "Second")
    third = task_store.add_task(str(proj), "Third")
    assert first and second and third

    assert task_store.reorder_tasks(str(proj), [third.id, first.id, second.id]) is True
    ordered = [r.title for r in task_store.get_tasks(str(proj))]
    assert ordered == ["Third", "First", "Second"]


def test_counts_for_project(tmp_path):
    proj = _project(tmp_path, "projA")
    done = task_store.add_task(str(proj), "Done")
    task_store.add_task(str(proj), "Open")
    assert done is not None
    task_store.toggle_task(str(proj), done.id)

    active, completed = task_store.counts_for_project(str(proj))
    assert (active, completed) == (1, 1)


def test_corrupt_task_file_falls_back_to_empty(tmp_path):
    """A corrupt task file must not crash the app."""
    import skill_manager.core.config as config_mod

    path = config_mod.resolve_data_file("project_tasks.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    state = task_store.load_state()
    assert state.projects == {}


def test_state_schema_roundtrip():
    record = ProjectTaskRecord(title="One")
    state = ProjectTasksState(projects={"/p": [record]})
    dumped = state.model_dump()
    restored = ProjectTasksState.model_validate(dumped)
    assert restored.projects["/p"][0].title == "One"


# ── controller ────────────────────────────────────────────────────────────


@pytest.fixture
def task_controller(tmp_path, monkeypatch):
    """A TaskController backed by a lightweight mock app."""
    from skill_manager.controllers.task_controller import TaskController

    app = MagicMock()
    proj = _project(tmp_path, "projA")
    app._projects = [str(proj)]
    app._project_aliases = {}
    app._current_project_label = proj.name
    app._client_format = "Codex"
    app.config_controller.getProjectPath.return_value = str(proj)
    app._library_model._all_skills = []
    app._quick_copy_model._all_skills = []
    app.clipboard_service.copy_text.return_value = True
    controller = TaskController(app)
    controller._project_dir = proj
    return controller, app, proj


def test_controller_add_and_list(task_controller):
    controller, _app, proj = task_controller

    assert controller.addProjectTask(str(proj), "Write docs", "high", "notes") is True

    tasks = controller.currentProjectTasks
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Write docs"
    assert tasks[0]["priority"] == "high"
    assert controller.activeTaskCount == 1
    assert controller.completedTaskCount == 0


def test_controller_toggle_and_delete(task_controller):
    controller, _app, proj = task_controller
    controller.addProjectTask(str(proj), "Toggle me", "medium", "")

    task_id = controller.currentProjectTasks[0]["id"]
    assert controller.toggleProjectTask(str(proj), task_id) is True
    assert controller.completedTaskCount == 1
    assert controller.activeTaskCount == 0

    assert controller.deleteProjectTask(str(proj), task_id) is True
    assert controller.currentProjectTasks == []


def test_controller_clear_completed(task_controller):
    controller, _app, proj = task_controller
    controller.addProjectTask(str(proj), "Done", "medium", "")
    task_id = controller.currentProjectTasks[0]["id"]
    controller.toggleProjectTask(str(proj), task_id)

    assert controller.clearCompletedProjectTasks(str(proj)) == 1
    assert controller.currentProjectTasks == []


def test_controller_uses_the_active_project_for_an_empty_path(task_controller):
    """An empty project path means "the active project"."""
    controller, _app, proj = task_controller
    assert controller.addProjectTask("", "Active project task", "medium", "") is True
    assert len(task_store.get_tasks(str(proj))) == 1


def test_controller_copy_task_as_prompt(task_controller):
    """The prompt contains the title, the notes, and the skill reference."""
    controller, app, proj = task_controller
    controller.addProjectTask(str(proj), "Ship it", "medium", "with the checklist")

    task_id = controller.currentProjectTasks[0]["id"]
    assert controller.copyTaskAsPrompt(str(proj), task_id) is True

    app.clipboard_service.copy_text.assert_called_once()
    text = app.clipboard_service.copy_text.call_args[0][0]
    assert "Ship it" in text
    assert "with the checklist" in text


def test_controller_copy_task_formats_linked_skill_for_client(task_controller):
    """A linked skill is rendered in the active client's syntax."""
    from skill_manager.core.models.entities import Skill

    controller, app, proj = task_controller
    helper = Skill(
        name="Helper Skill",
        folder_name="helper-skill",
        local_path="/library/helper-skill",
    )
    app._library_model._all_skills = [helper]

    controller.addProjectTask(str(proj), "Use the helper", "medium", "")
    task_id = controller.currentProjectTasks[0]["id"]

    record = task_store.get_tasks(str(proj))[0]
    record.linked_skills = ["helper-skill"]
    task_store.save_state(task_store.load_state())

    assert controller.copyTaskAsPrompt(str(proj), task_id) is True
    text = app.clipboard_service.copy_text.call_args[0][0]
    assert "helper" in text.lower()


def test_controller_open_task_count_for_project(task_controller):
    controller, _app, proj = task_controller
    controller.addProjectTask(str(proj), "One", "medium", "")
    assert controller.openTaskCountForProject(str(proj)) == 1
    assert controller.openTaskCountForProject("") == 0


def test_controller_emits_tasks_changed(task_controller):
    controller, _app, proj = task_controller
    emissions = []
    controller.tasksChanged.connect(lambda: emissions.append(True))

    controller.addProjectTask(str(proj), "One", "medium", "")
    assert len(emissions) == 1


def test_controller_without_an_active_project_rejects_tasks(task_controller):
    """Without an active project there is nothing to attach a task to."""
    controller, _app, proj = task_controller
    app = controller.app
    app._current_project_label = ""
    app.config_controller.getProjectPath.return_value = ""

    assert controller.addProjectTask("", "No project", "medium", "") is False
    assert task_store.get_tasks(str(proj)) == []


# ── attachments ───────────────────────────────────────────────────────────


def _fake_image(directory: Path, name: str = "shot.png") -> Path:
    path = directory / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    return path


def test_store_attachment_copies_into_the_app_data_store(tmp_path):
    proj = _project(tmp_path, "projA")
    source = _fake_image(tmp_path)

    stored = task_store.store_attachment(str(proj), str(source))

    assert stored, "an image must be stored"
    assert Path(stored).is_file()
    assert Path(stored).read_bytes() == source.read_bytes()
    assert task_store.attachments_root() in Path(stored).parents
    assert source.exists(), "the original file must not be moved"
    # The project tree is never touched.
    assert list(proj.iterdir()) == []


def test_store_attachment_accepts_a_file_url(tmp_path):
    """QML hands us ``file:///…`` URLs from the dialog and drag-and-drop."""
    proj = _project(tmp_path, "projA")
    source = _fake_image(tmp_path)

    stored = task_store.store_attachment(str(proj), source.as_uri())
    assert stored and Path(stored).is_file()


def test_store_attachment_rejects_non_images(tmp_path):
    proj = _project(tmp_path, "projA")
    doc = tmp_path / "notes.txt"
    doc.write_text("hi", encoding="utf-8")

    assert task_store.store_attachment(str(proj), str(doc)) == ""
    assert task_store.store_attachment(str(proj), str(tmp_path / "missing.png")) == ""
    assert task_store.store_attachment("", str(_fake_image(tmp_path))) == ""


def test_store_attachment_bytes_for_a_pasted_screenshot(tmp_path):
    proj = _project(tmp_path, "projA")

    stored = task_store.store_attachment_bytes(str(proj), b"\x89PNG-data", ".png")
    assert stored and Path(stored).suffix == ".png"
    assert Path(stored).read_bytes() == b"\x89PNG-data"
    assert task_store.store_attachment_bytes(str(proj), b"", ".png") == ""


def test_add_task_persists_attachments(tmp_path):
    proj = _project(tmp_path, "projA")
    stored = task_store.store_attachment(str(proj), str(_fake_image(tmp_path)))

    record = task_store.add_task(str(proj), "With a shot", attachments=[stored, ""])
    assert record is not None
    assert record.attachments == [stored]

    reloaded = task_store.get_tasks(str(proj))[0]
    assert reloaded.attachments == [stored]


def test_update_task_drops_removed_attachments_from_disk(tmp_path):
    proj = _project(tmp_path, "projA")
    keep = task_store.store_attachment(str(proj), str(_fake_image(tmp_path, "a.png")))
    drop = task_store.store_attachment(str(proj), str(_fake_image(tmp_path, "b.png")))
    record = task_store.add_task(str(proj), "Two shots", attachments=[keep, drop])
    assert record is not None

    updated = task_store.update_task(str(proj), record.id, attachments=[keep])
    assert updated is not None
    assert updated.attachments == [keep]
    assert Path(keep).exists()
    assert not Path(drop).exists(), "an unlinked attachment must not linger"


def test_delete_task_removes_its_attachments(tmp_path):
    proj = _project(tmp_path, "projA")
    stored = task_store.store_attachment(str(proj), str(_fake_image(tmp_path)))
    record = task_store.add_task(str(proj), "Temporary", attachments=[stored])
    assert record is not None

    assert task_store.delete_task(str(proj), record.id) is True
    assert not Path(stored).exists()


def test_clear_completed_removes_attachments_of_completed_tasks(tmp_path):
    proj = _project(tmp_path, "projA")
    done_shot = task_store.store_attachment(str(proj), str(_fake_image(tmp_path, "done.png")))
    open_shot = task_store.store_attachment(str(proj), str(_fake_image(tmp_path, "open.png")))
    done = task_store.add_task(str(proj), "Done", attachments=[done_shot])
    task_store.add_task(str(proj), "Open", attachments=[open_shot])
    assert done is not None
    task_store.toggle_task(str(proj), done.id)

    assert task_store.clear_completed_tasks(str(proj)) == 1
    assert not Path(done_shot).exists()
    assert Path(open_shot).exists()


def test_attachments_outside_the_store_are_never_deleted(tmp_path):
    """A task record is user data; it must not be able to delete arbitrary files."""
    proj = _project(tmp_path, "projA")
    outside = _fake_image(tmp_path, "precious.png")

    record = task_store.add_task(str(proj), "Sneaky", attachments=[str(outside)])
    assert record is not None
    assert task_store.delete_task(str(proj), record.id) is True
    assert outside.exists()


def test_controller_attachment_flow(task_controller):
    controller, app, proj = task_controller
    source = _fake_image(Path(app._projects[0]).parent)

    stored = controller.attachTaskImage(str(proj), str(source))
    assert stored, "the controller must store the attachment"

    assert (
        controller.addProjectTask(str(proj), "Ship it", "high", "with a screenshot", [stored])
        is True
    )
    task = controller.currentProjectTasks[0]
    assert task["attachments"] == [stored]

    task_id = task["id"]
    assert controller.copyTaskAsPrompt(str(proj), task_id) is True
    text = app.clipboard_service.copy_text.call_args[0][0]
    assert stored in text


def test_controller_attach_rejects_non_images(task_controller):
    controller, _app, proj = task_controller
    doc = Path(proj).parent / "notes.txt"
    doc.write_text("hi", encoding="utf-8")

    assert controller.attachTaskImage(str(proj), str(doc)) == ""
    # No project selected -> nothing can be stored.
    assert controller.attachTaskImage("", str(doc)) == ""


def test_controller_clipboard_image_is_optional(task_controller):
    """A text-only clipboard must return "" instead of raising."""
    controller, _app, proj = task_controller
    assert controller.attachClipboardImage(str(proj)) == ""


# ── read caching ──────────────────────────────────────────────────────────


def _count_reads(monkeypatch):
    """Record every read of the tasks JSON file."""
    reads: list = []
    original = Path.read_bytes

    def counting(self):
        reads.append(self)
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    return reads


def test_repeated_reads_hit_the_cache(tmp_path, monkeypatch):
    """QML re-reads the task state constantly; the file must be parsed once."""
    proj = _project(tmp_path, "projA")
    task_store.add_task(str(proj), "One")
    reads = _count_reads(monkeypatch)

    for _ in range(25):
        task_store.get_tasks(str(proj))
        task_store.counts_for_project(str(proj))

    assert reads == [], "the state should be served from the cache"


def test_external_writes_invalidate_the_cache(tmp_path):
    """Another process (or the MCP server) writing the file must be seen."""
    import json

    import skill_manager.core.config as config_mod

    proj = _project(tmp_path, "projA")
    task_store.add_task(str(proj), "One")
    key = task_store.project_task_key(str(proj))
    assert task_store.get_tasks(str(proj))[0].title == "One"

    path = config_mod.resolve_data_file("project_tasks.json")
    payload = json.loads(path.read_bytes())
    payload["projects"][key].append({"id": "external", "title": "From elsewhere", "order": 1})
    path.write_bytes(json.dumps(payload).encode("utf-8"))

    titles = [record.title for record in task_store.get_tasks(str(proj))]
    assert titles == ["One", "From elsewhere"]


def test_mutations_return_a_copy_not_the_cache(tmp_path):
    """A failed write must not leave the cache holding unsaved changes."""
    proj = _project(tmp_path, "projA")
    task_store.add_task(str(proj), "One")

    cached = task_store.load_state()
    copy = cached.model_copy(deep=True)
    copy.projects["/unrelated"] = []
    assert "/unrelated" not in task_store.load_state().projects
