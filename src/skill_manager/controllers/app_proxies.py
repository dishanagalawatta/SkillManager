"""QML proxy slots for AppController (extracted from ``app.py``, Phase 1).

Slots-only extraction: every method here is a pure ``@Slot`` delegating to a
sub-controller. There are no ``@Property``/signal declarations, so a plain
Python mixin is safe under PySide6's meta-object system — ``AppController``
inherits this mixin *before* ``QObject`` and the metaobject discovers the
inherited slots, keeping every QML call site unchanged.

``logger`` is imported from ``bootstrap`` so tests that patch
``skill_manager.app.logger`` keep intercepting logs emitted from these
methods (see the same pattern in ``app.py``).
"""

from typing import cast

from PySide6.QtCore import Slot

from skill_manager.bootstrap import logger
from skill_manager.core.diagnostics import get_diagnostic_logger
from skill_manager.core.models import SkillModel


class AppControllerProxyMixin:
    """QML-facing proxy slots that delegate to the sub-controllers."""

    # --- Proxy Slots (Temporary for QML compatibility) ---

    @Slot()
    def load_initial_data(self):
        self.loadInitialData()

    @Slot(str, result=str)
    def getLogoSource(self, f):
        return self.ui.getLogoSource(f)

    @Slot(str, result=str)
    def getAssetUri(self, p):
        return self.ui.getAssetUri(p)

    @Slot(str, str)
    def setViewFilter(self, k, v):
        self.ui.setViewFilter(k, v)

    @Slot(str, str, str)
    def setViewFilterForView(self, view, k, v):
        self.ui.setViewFilterForView(view, k, v)

    @Slot()
    def clearViewFilters(self):
        self.ui.clearViewFilters()

    @Slot(int)
    def selectSkill(self, i):
        self.ui.selectSkill(i)

    @Slot()
    def clearVisibleSelection(self):
        self.ui.clearVisibleSelection()

    @Slot()
    def selectAllVisibleSkills(self):
        self.ui.selectAllVisibleSkills()

    @Slot()
    def toggleAllVisibleCategories(self):
        self.ui.toggleAllVisibleCategories()

    @Slot(str)
    def launchSkill(self, p):
        self.ui.launchSkill(p)

    @Slot(str)
    def openPath(self, p):
        self.ui.openPath(p)

    @Slot()
    def resetUiState(self):
        self.ui.resetUiState()

    @Slot(str)
    def setClientFormat(self, f):
        self.ui.setClientFormat(f)

    @Slot(str)
    def setStartupView(self, v):
        self.ui.setStartupView(v)

    @Slot(bool)
    def setRememberFilters(self, b):
        self.ui.setRememberFilters(b)

    @Slot(bool)
    def setReducedMotion(self, b):
        self.ui.setReducedMotion(b)

    @Slot(bool)
    def setCompactListRows(self, b):
        self.ui.setCompactListRows(b)

    @Slot(str)
    def addSource(self, u):
        self.config_mgr.addSource(u)

    @Slot(str)
    def removeSource(self, p):
        self.config_mgr.removeSource(p)

    @Slot(int)
    def removeSourceByIndex(self, i):
        self.config_mgr.removeSourceByIndex(i)

    @Slot(str)
    def addProject(self, u):
        self.config_mgr.addProject(u)

    @Slot(str)
    def removeProject(self, p):
        self.config_mgr.removeProject(p)

    @Slot(int, int)
    def reorderProjects(self, from_index, to_index):
        self.config_mgr.reorderProjects(from_index, to_index)

    @Slot(int)
    def removeUpdateProject(self, i):
        self.config_mgr.removeUpdateProject(i)

    @Slot(str, str)
    def setProjectAlias(self, p, a):
        self.config_mgr.setProjectAlias(p, a)

    @Slot(str, str, result=str)
    def verifyGitPackage(self, u, t=None):
        return self.config_mgr.verifyGitPackage(u, t)

    @Slot(str, str)
    def setShortcut(self, a, s):
        self.config_mgr.setShortcut(a, s)

    @Slot()
    def resetShortcuts(self):
        self.config_mgr.resetShortcuts()

    @Slot(str, list, list)
    def saveCustomCollection(self, n, p, proj):
        self.config_mgr.saveCustomCollection(n, p, proj)

    @Slot(str)
    def deleteCustomCollection(self, n):
        self.config_mgr.deleteCustomCollection(n)

    @Slot(str)
    def applyCollectionSelection(self, n):
        self.config_mgr.applyCollectionSelection(n)

    @Slot(str, result=list)
    def getCollectionPaths(self, n):
        return self.config_mgr.getCollectionPaths(n)

    @Slot(str, result=list)
    def getCollectionProjects(self, n):
        return self.config_mgr.getCollectionProjects(n)

    @Slot(str, result=str)
    def checkMissingSkills(self, n):
        return self.config_mgr.checkMissingSkills(n)

    @Slot(str, list)
    def copyMissingSkills(self, n, projects):
        self.config_mgr.copyMissingSkills(n, projects)

    @Slot()
    def toggleCurrentSkillArchive(self):
        self.ops.toggleCurrentSkillArchive()

    @Slot()
    def toggleCurrentSkillStarred(self):
        self.ops.toggleCurrentSkillStarred()

    @Slot(str)
    def copySkillToClipboard(self, p):
        self.ops.copySkillToClipboard(p)

    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self):
        self.ops.copyCurrentSelectionOrFocusedSkill()

    @Slot()
    def copySelectedSkillsToClipboard(self):
        self.ops.copySelectedSkillsToClipboard()

    @Slot(str)
    def copyTextToClipboard(self, c):
        self.ops.copyTextToClipboard(c)

    @Slot(dict, str)
    def copySkillReference(self, s, a=""):
        self.ops.copySkillReference(s, a)

    @Slot(str)
    def copyCollectionToClipboard(self, n):
        self.ops.copyCollectionToClipboard(n)

    @Slot(str)
    def deleteSkill(self, p):
        self.ops.deleteSkill(p)

    @Slot()
    def deleteSelectedSkills(self):
        self.ops.deleteSelectedSkills()

    @Slot(list)
    def deleteSkillsByPaths(self, paths):
        self.ops.deleteSkillsByPaths(paths)

    @Slot()
    def archiveSelectedSkills(self):
        self.ops.archiveSelectedSkills()

    @Slot(str)
    def copySelectedSkillsToProject(self, p):
        self.ops.copySelectedSkillsToProject(p)

    @Slot(str)
    def copySelectedSkillsToProjectTemporarily(self, p):
        self.ops.copySelectedSkillsToProjectTemporarily(p)

    @Slot(str, str, str, str, list, str)
    def updateCustomCommandFull(self, lp, n, b, cat, proj, on_conflict=""):
        self.ops.updateCustomCommandFull(lp, n, b, cat, proj, on_conflict)

    @Slot(str, str)
    def notify_command_updated(self, old_path: str, new_path: str) -> None:
        self.commandUpdateCompleted.emit(old_path, new_path)

    @Slot(str, str, list, str, result=str)
    def createCustomCommand(self, n, b, pl, cat) -> str:
        return str(self.ops.createCustomCommand(n, b, pl, cat))

    @Slot(str, result=str)
    def getCommandEmoji(self, path: str) -> str:
        return self._config.get_command_emoji(path)

    @Slot(str, str)
    def setCommandEmoji(self, path: str, emoji: str) -> None:
        if emoji in ("", "⚡"):
            self._config.clear_command_emoji(path)
        else:
            self._config.set_command_emoji(path, emoji)
        cast(SkillModel, self.skillModel).refresh_emoji_for_path(path)
        logger.info("Command emoji set for %s", path)

    @Slot(str)
    def clearCommandEmoji(self, path: str) -> None:
        self._config.clear_command_emoji(path)
        cast(SkillModel, self.skillModel).refresh_emoji_for_path(path)
        logger.info("Command emoji cleared for %s", path)

    @Slot(result=list)
    def getEmojiRecents(self) -> list[str]:
        return self._config.get_emoji_recents()

    @Slot(str)
    def addEmojiRecent(self, emoji: str) -> None:
        self._config.add_emoji_recent(emoji)

    @Slot(str, result=list)
    def commandProjectsForPath(self, lp):
        return self.ops.commandProjectsForPath(lp)

    @Slot(str, result=list)
    def skillProjectsForPath(self, lp):
        return self.ops.skillProjectsForPath(lp)

    @Slot(str, list)
    def deleteCustomCommand(self, name, project_labels):
        self.ops.deleteCustomCommand(name, project_labels)

    @Slot(str, list)
    def confirmCommandRemovals(self, local_path, confirmed_labels):
        self.ops.confirmCommandRemovals(local_path, confirmed_labels)

    @Slot(str, str, str)
    def confirmCommandSkillsCarry(self, project_path, command_paths_json, confirmed_skills_json):
        self.ops.confirmCommandSkillsCarry(project_path, command_paths_json, confirmed_skills_json)

    @Slot(str, list)
    def deleteSkillFromProjects(self, path, projects):
        self.ops.deleteSkillFromProjects(path, projects)

    @Slot(str)
    def addToArchive(self, p):
        self.ops.addToArchive(p)

    @Slot()
    def updateNow(self):
        self.updates.updateNow()

    @Slot()
    def scanForUpdates(self):
        self.updates.scanForUpdates()

    @Slot()
    def updateAllOutdated(self):
        self.updates.updateAllOutdated()

    @Slot(str, str)
    def updateSkillInProject(self, s, p):
        self.updates.updateSkillInProject(s, p)

    @Slot(int)
    def runPackageUpdate(self, i):
        self.updates.runPackageUpdate(i)

    @Slot(str)
    def syncProject(self, p):
        self.updates.syncProject(p)

    @Slot(str)
    def addUpdatePackage(self, n):
        self.updates.addUpdatePackage(n)

    @Slot(dict, result=str)
    def addSkillPackage(self, d):
        return self.updates.addSkillPackage(d)

    @Slot(int, dict, result=str)
    def updateUpdatePackage(self, i, d):
        return self.updates.updateUpdatePackage(i, d)

    @Slot(int)
    def removeUpdatePackage(self, i):
        self.updates.removeUpdatePackage(i)

    @Slot(int)
    def clearPackageJustFinished(self, i):
        self.updates.clearPackageJustFinished(i)

    @Slot(str, str, str)
    def logDiagnostic(self, level: str, category: str, msg: str):
        """QML-callable diagnostic logger — emits to the structured ring buffer."""
        get_diagnostic_logger().log_event(level, category, msg)

    # --- Slots ---
