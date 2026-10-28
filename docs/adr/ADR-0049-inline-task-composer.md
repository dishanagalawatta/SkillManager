# ADR-0049: Inline Task Composer with Image Attachments

> Status: **Accepted**
> Date: 2026-10-28
> Owner: @DIKKA

## Context

The per-project task panel added tasks through a one-line `TextField` pill in a
`RowLayout` above the list, with `Enter` submitting and a separate priority
pill next to it. Every task was therefore a title; notes existed in the model
(`ProjectTaskRecord.description`) and in the inline editor, but they could not
be *written* at creation time. There was no way to record a screenshot with a
task, no subtask structure, and the input row was visually detached from the
list it fed.

## Decision

Replace the quick-add pill with **`TaskComposer.qml`**, a multi-line editor
hosted as the footer of the task list box.

- **Title / notes split** — the first non-empty line is the title, every line
  after it is the notes. One line stays the fast path; five lines cost nothing.
- **Subtask bullets** — `Enter` on a line starting with `- `, `* ` or
  `- [ ] ` continues the marker; an empty marker ends the list instead of
  leaving a dangling dash.
- **Keys** — `Ctrl`/`Cmd`+`Enter` adds, `Enter` inserts a newline, `Esc`
  discards the draft. The editor grows to 180 px and then scrolls.
- **Priority** — the existing low → medium → high pill moved inside the
  composer, next to the actions it applies to.
- **Images** — attached through three paths: file dialog, drag-and-drop, and
  `Ctrl+V` of a clipboard image (text paste is untouched: the handler only
  accepts the event when the clipboard actually holds an image).
- **Storage** — `core/tasks.store_attachment()` copies the file into
  `DATA_DIR / "task_attachments"/<sha256(project key)[:16]>/<uuid><suffix>`.
  Images only (`.png .jpg .jpeg .gif .webp .bmp`), 25 MB cap, never written
  into the project tree, and unlink is restricted to paths inside the store.
  Files are pruned when an attachment is removed, or when its task is deleted
  or cleared.
- **Drafts** — the panel keeps one draft per project (`_drafts` map), so
  switching project never writes a half-written task into another project's
  list, and never throws the draft away either.

## Consequences

### Positive

- A task can be captured at the moment it is thought of: title, notes, subtask
  bullets and a screenshot in one surface.
- The composer lives inside the list box, so "where I type" and "where it
  lands" are the same place.
- Attachments are per-task data, not project files: deleting a task leaves no
  orphaned images and never touches the user's repository.

### Negative

- A growing footer reduces the visible list height while drafting. Capped at
  180 px so the list keeps at least a few rows.
- The clipboard-paste shortcut is platform-behaviour-dependent: on a clipboard
  with both text and an image, the image wins.
- Attachment files live outside the project, so `copyTaskAsPrompt` emits the
  absolute paths rather than markdown images; the agent has to read the file.

### Neutral

- `addProjectTask` gained a `QVariantList` attachments argument; existing
  four-argument call sites keep working through the default.
- Priorities still cycle rather than open a menu — unchanged behaviour, moved.

## Alternatives Considered

### Keep the pill and add a "expand" button that opens a dialog

Rejected: the request was to stop separating "type here" from "the task lands
there". A modal adds a step and hides the list while composing.

### Rich text / markdown editor

Rejected for now: the model stores plain text, and the panel is a quick capture
surface. Markdown round-tripping (render, edit, preserve source) is a much
larger change than the problem that was reported.

### Store attachments in the project tree (`.agents/tasks/<id>.png`)

Rejected: project directories are the user's, often version-controlled. The app
would litter them and deleting a task would show up as a git change.

## References

- `src/skill_manager/SkillManagerComponents/TaskComposer.qml`
- `src/skill_manager/core/tasks.py` — `store_attachment`, `attachments_root`
- `tests/qml/test_qml_task_composer_contract.py`
- `docs/ARCHITECTURE.md` — Per-Project Task List
- [ADR-0047](ADR-0047-common-side-panel-shell.md) — the panel shell it sits in
