"""QML contract for the unified command workflow.

The Library is the single source of truth for a custom command: the
create/edit dialog edits that one file, and deployment to other projects
goes through the Library's copy flow, which asks before it replaces an
existing project command.
"""

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return (QML_DIR.joinpath(*parts)).read_text(encoding="utf-8")


def test_command_dialog_has_no_project_selector():
    """The create/edit dialog must not ask for target projects any more."""
    dialog = _read("dialogs", "CommandCreateDialog.qml")

    assert "projectMultiSelect" not in dialog
    assert "editProjectLabels" not in dialog
    assert "GlassMultiSelect" not in dialog
    assert "AppController.projectLabels" not in dialog


def test_command_dialog_calls_the_single_project_api():
    """Create and update use the project-less controller signatures."""
    dialog = _read("dialogs", "CommandCreateDialog.qml")

    assert "AppController.createCustomCommand(" in dialog
    assert "AppController.updateCustomCommandFull(" in dialog
    # The old fan-out argument is gone.
    assert "pendingArgs.projectLabels" not in dialog
    assert "root.pendingArgs.projectLabels" not in dialog


def test_command_dialog_no_longer_prompts_for_project_removals():
    """The multi-project removal prompt was removed with the fan-out."""
    dialog = _read("dialogs", "CommandCreateDialog.qml")

    assert "CommandRemovalConfirmDialog" not in dialog
    assert "onCommandPendingRemovals" not in dialog


def test_removed_removal_dialog_is_not_registered():
    """The dead component must not linger in the module registry."""
    qmldir = _read("qmldir")
    assert "CommandRemovalConfirmDialog" not in qmldir
    assert not (QML_DIR / "dialogs" / "CommandRemovalConfirmDialog.qml").exists()


def test_update_confirm_dialog_is_registered_and_offers_the_three_actions():
    """The copy-conflict dialog exposes update / copy-new / cancel."""
    qmldir = _read("qmldir")
    assert "CommandUpdateConfirmDialog 1.0 dialogs/CommandUpdateConfirmDialog.qml" in qmldir

    dialog = _read("dialogs", "CommandUpdateConfirmDialog.qml")
    assert "Update Existing & Copy New" in dialog
    assert "Copy Only New" in dialog
    assert "Cancel" in dialog
    assert "AppController.confirmCommandCopyWithOverwrite(" in dialog
    assert "AppController.cancelCommandCopyWithOverwrite()" in dialog
    # It must be built on the shared design-system surface.
    assert dialog.lstrip().startswith("/**")
    assert "GlassDialog {" in dialog


def test_library_view_opens_the_update_confirm_dialog():
    """The Library wires the detection signal to the new dialog."""
    library = _read("views", "LibraryView.qml")

    assert "CommandUpdateConfirmDialog {" in library
    assert "onCommandCopyExistingDetected(" in library
    assert "lv_commandUpdateConfirmDialog.openForCopy(" in library
