import logging
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)

# PySide6 6.11.0's type stub nests ``Checked`` / ``Unchecked`` /
# ``PartiallyChecked`` under ``Qt.CheckState`` rather than exposing them
# as flat ``Qt.Checked`` etc. The runtime does expose the flat aliases
# (PySide6 has compatibility constants) but the type-checker doesn't
# model that — so the runtime works while pyright rejects the flat
# access. Use the typed nested form so both the runtime and the
# static checker agree.
from skill_manager.core.models.entities import FilterState, Skill
from skill_manager.core.models.filter_engine import FilterEngine
from skill_manager.core.search import SearchEngine

logger = logging.getLogger(__name__)


class SkillModel(QAbstractListModel):
    """
    Qt List Model for skills, delegating logic to FilterEngine.
    """

    NameRole = Qt.ItemDataRole.UserRole + 1
    CategoryRole = Qt.ItemDataRole.UserRole + 2
    DescriptionRole = Qt.ItemDataRole.UserRole + 3
    PathRole = Qt.ItemDataRole.UserRole + 4
    ProjectRole = Qt.ItemDataRole.UserRole + 5
    IsStarredRole = Qt.ItemDataRole.UserRole + 6
    IsSelectedRole = Qt.ItemDataRole.UserRole + 7
    SearchTextRole = Qt.ItemDataRole.UserRole + 8
    IsArchivedRole = Qt.ItemDataRole.UserRole + 9
    IsCollectionRole = Qt.ItemDataRole.UserRole + 10
    SectionRole = Qt.ItemDataRole.UserRole + 11
    RawContentRole = Qt.ItemDataRole.UserRole + 12
    BodyContentRole = Qt.ItemDataRole.UserRole + 13
    RiskRole = Qt.ItemDataRole.UserRole + 14
    SourceRole = Qt.ItemDataRole.UserRole + 15
    DateRole = Qt.ItemDataRole.UserRole + 16
    IsCollapsedRole = Qt.ItemDataRole.UserRole + 17
    IsCommandRole = Qt.ItemDataRole.UserRole + 18
    ClientRole = Qt.ItemDataRole.UserRole + 19
    MainCategoryNameRole = Qt.ItemDataRole.UserRole + 20
    IsFirstInSubcategoryRole = Qt.ItemDataRole.UserRole + 21
    IsMainCollapsedRole = Qt.ItemDataRole.UserRole + 22
    IsSubCollapsedRole = Qt.ItemDataRole.UserRole + 23
    SubCategoryNameRole = Qt.ItemDataRole.UserRole + 24
    IsPackageRole = Qt.ItemDataRole.UserRole + 25
    IsScreenshotRole = Qt.ItemDataRole.UserRole + 26

    _ALL_ROLES = [
        NameRole,
        CategoryRole,
        DescriptionRole,
        PathRole,
        ProjectRole,
        IsStarredRole,
        IsSelectedRole,
        SearchTextRole,
        IsArchivedRole,
        IsCollectionRole,
        SectionRole,
        RawContentRole,
        BodyContentRole,
        RiskRole,
        SourceRole,
        DateRole,
        IsCollapsedRole,
        IsCommandRole,
        ClientRole,
        MainCategoryNameRole,
        IsFirstInSubcategoryRole,
        IsMainCollapsedRole,
        IsSubCollapsedRole,
        SubCategoryNameRole,
        IsPackageRole,
        IsScreenshotRole,
    ]

    filterChanged = Signal()
    showArchivedChanged = Signal()
    categoryFilterChanged = Signal()
    collectionFilterChanged = Signal()
    projectFilterChanged = Signal()
    selectionStateChanged = Signal()
    collapsedCategoriesChanged = Signal()
    showCommandsChanged = Signal()
    showStarredChanged = Signal()
    isPackageOnlyChanged = Signal()
    clientFilterChanged = Signal()
    filterByClientChanged = Signal()
    totalSelectableCountChanged = Signal()

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self._all_skills: list[Skill] = []
        self._all_filtered_skills: list[Skill] = []
        self._filtered_skills: list[Skill] = []
        self._config = config
        self._search_engine = None
        self._selected_ids: dict[str, None] = {}
        self._engine = FilterEngine()
        self.state = FilterState()
        self._suppress_layout = False
        self._batch_apply_needed = False
        self._selections_by_project: dict[str, list[str]] = {}
        self._project_selections_save_timer = None
        self._collapse_save_timer = None
        self._cached_selected_count = 0
        self._cached_visible_selectable = 0
        self._cached_visible_selected = 0
        self._cached_total_selectable = 0

        if self._config:
            self.state.collapsed_categories = set(self._config.get("collapsed_categories", []))
            self.state.show_archived = self._config.get("show_archived", False)
            self.state.category_filter = self._config.get("category_filter", "")
            self.state.collection_filter = self._config.get("collection_filter", False)
            self.state.project_filter = self._config.get("project_filter", "")
            self.state.client_filter = self._config.get("client_format", "")
            self.state.show_commands = self._config.get("show_commands", True)
            self.state.show_starred = self._config.get("show_starred", True)
            self.state.is_package_only = self._config.get(
                "is_package_only", self._config.get("is_source_only", None)
            )
            raw = self._config.get("project_selections", {})
            if raw:
                self._selections_by_project = {k: list(v) for k, v in raw.items()}
            initial_project = self.state.project_filter
            if initial_project and initial_project in self._selections_by_project:
                self._selected_ids = dict.fromkeys(self._selections_by_project[initial_project])

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: ARG002
        return len(self._filtered_skills)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or index.row() >= len(self._filtered_skills):
            return None

        skill = self._filtered_skills[index.row()]
        path = skill.local_path

        if role == self.NameRole:
            return skill.name
        if role == self.CategoryRole:
            return skill.category
        if role == self.DescriptionRole:
            return skill.description
        if role == self.PathRole:
            return path
        if role == self.ProjectRole:
            return skill.project_label
        if role == self.IsStarredRole:
            return skill.is_starred
        if role == self.IsSelectedRole:
            return path in self._selected_ids
        if role == self.IsArchivedRole:
            return skill.is_archived
        if role == self.IsCollectionRole:
            return skill.is_bundle
        if role == self.SectionRole:
            return skill.section_name or self._engine.get_section(skill)
        if role == self.MainCategoryNameRole:
            return skill.main_category_name or self._engine.get_main_category(skill)
        if role == self.RawContentRole:
            return skill.raw_content
        if role == self.BodyContentRole:
            return skill.body_content
        if role == self.RiskRole:
            return skill.risk
        if role == self.SourceRole:
            return skill.source
        if role == self.DateRole:
            return skill.date
        if role == self.IsCollapsedRole:
            return self._is_main_collapsed(skill) or self._is_sub_collapsed(skill)
        if role == self.IsCommandRole:
            return skill.is_command
        if role == self.ClientRole:
            return skill.client
        if role == self.IsFirstInSubcategoryRole:
            return skill.is_first_in_subcategory
        if role == self.IsMainCollapsedRole:
            return self._is_main_collapsed(skill)
        if role == self.IsSubCollapsedRole:
            return self._is_sub_collapsed(skill)
        if role == self.SubCategoryNameRole:
            return skill.sub_category_name or self._engine.get_sub_category(skill)
        if role == self.IsPackageRole:
            return skill.is_package
        if role == self.IsScreenshotRole:
            return skill.is_screenshot

        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: QByteArray(b"name"),
            self.CategoryRole: QByteArray(b"category"),
            self.DescriptionRole: QByteArray(b"description"),
            self.PathRole: QByteArray(b"path"),
            self.ProjectRole: QByteArray(b"project"),
            self.IsStarredRole: QByteArray(b"isStarred"),
            self.IsSelectedRole: QByteArray(b"isSelected"),
            self.SearchTextRole: QByteArray(b"searchText"),
            self.IsArchivedRole: QByteArray(b"isArchived"),
            self.IsCollectionRole: QByteArray(b"isCollection"),
            self.SectionRole: QByteArray(b"sectionName"),
            self.RawContentRole: QByteArray(b"rawContent"),
            self.BodyContentRole: QByteArray(b"bodyContent"),
            self.RiskRole: QByteArray(b"risk"),
            self.SourceRole: QByteArray(b"source"),
            self.MainCategoryNameRole: QByteArray(b"mainCategoryName"),
            self.DateRole: QByteArray(b"date"),
            self.IsCollapsedRole: QByteArray(b"isCollapsed"),
            self.IsCommandRole: QByteArray(b"isCommand"),
            self.ClientRole: QByteArray(b"client"),
            self.IsFirstInSubcategoryRole: QByteArray(b"isFirstInSubcategory"),
            self.IsMainCollapsedRole: QByteArray(b"isMainCollapsed"),
            self.IsSubCollapsedRole: QByteArray(b"isSubCollapsed"),
            self.SubCategoryNameRole: QByteArray(b"subCategoryName"),
            self.IsPackageRole: QByteArray(b"isPackage"),
            self.IsScreenshotRole: QByteArray(b"isScreenshot"),
        }

    # Properties
    @Property(str, notify=filterChanged)
    def filterText(self):  # type: ignore[reportRedeclaration]
        return self.state.filter_text

    @filterText.setter
    def filterText(self, value):
        if self.state.filter_text != value:
            self.state.filter_text = value
            self._apply_filter()
            self.filterChanged.emit()

    @Property(bool, notify=showArchivedChanged)
    def showArchived(self):  # type: ignore[reportRedeclaration]
        return self.state.show_archived

    @showArchived.setter
    def showArchived(self, value):
        if self.state.show_archived != value:
            self.state.show_archived = value
            self._apply_filter()
            self._save_filters()
            self.showArchivedChanged.emit()

    @Property(str, notify=categoryFilterChanged)
    def categoryFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.category_filter

    @categoryFilter.setter
    def categoryFilter(self, value):
        if self.state.category_filter != value:
            self.state.category_filter = value
            self._apply_filter()
            self._save_filters()
            self.categoryFilterChanged.emit()

    @Property(bool, notify=collectionFilterChanged)
    def collectionFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.collection_filter

    @collectionFilter.setter
    def collectionFilter(self, value):
        if self.state.collection_filter != value:
            self.state.collection_filter = value
            self._apply_filter()
            self._save_filters()
            self.collectionFilterChanged.emit()

    @Property(str, notify=projectFilterChanged)
    def projectFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.project_filter

    @projectFilter.setter
    def projectFilter(self, value):
        if self.state.project_filter != value:
            old_project = self.state.project_filter
            if old_project:
                self._selections_by_project[old_project] = list(self._selected_ids)
            self.state.project_filter = value
            if value in self._selections_by_project:
                self._selected_ids = dict.fromkeys(self._selections_by_project[value])
            else:
                self._selected_ids.clear()
            self._apply_filter()
            self._save_filters()
            self._save_project_selections()
            self.projectFilterChanged.emit()

    @Property(str, notify=clientFilterChanged)
    def clientFilter(self):  # type: ignore[reportRedeclaration]
        return self.state.client_filter

    @clientFilter.setter
    def clientFilter(self, value):
        if self.state.client_filter != value:
            self.state.client_filter = value

            if self.state.filter_by_client:
                self._apply_filter()
            self._save_filters()
            self.clientFilterChanged.emit()

    @Property(bool, notify=filterByClientChanged)
    def filterByClient(self):  # type: ignore[reportRedeclaration]
        return self.state.filter_by_client

    @filterByClient.setter
    def filterByClient(self, value):
        if self.state.filter_by_client != value:
            self.state.filter_by_client = value
            self._apply_filter()
            self.filterByClientChanged.emit()

    @Property(bool, notify=showCommandsChanged)
    def showCommands(self):  # type: ignore[reportRedeclaration]
        return self.state.show_commands

    @showCommands.setter
    def showCommands(self, value):
        if self.state.show_commands != value:
            self.state.show_commands = value
            self._apply_filter()
            self._save_filters()
            self.showCommandsChanged.emit()

    @Property(bool, notify=showStarredChanged)
    def showStarred(self):  # type: ignore[reportRedeclaration]
        return self.state.show_starred

    @showStarred.setter
    def showStarred(self, value):
        if self.state.show_starred != value:
            self.state.show_starred = value
            self._apply_filter()
            self._save_filters()
            self.showStarredChanged.emit()

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):  # type: ignore[reportRedeclaration]
        if self.state.is_package_only is None:
            return Qt.CheckState.PartiallyChecked
        return Qt.CheckState.Checked if self.state.is_package_only else Qt.CheckState.Unchecked

    @isPackageOnly.setter
    def isPackageOnly(self, value):
        new_val = None
        if value == Qt.CheckState.Checked or value is True:
            new_val = True
        elif value == Qt.CheckState.Unchecked or value is False:
            new_val = False
        if self.state.is_package_only != new_val:
            self.state.is_package_only = new_val
            self._apply_filter()
            self._save_filters()
            self.isPackageOnlyChanged.emit()

    @Property(int, notify=selectionStateChanged)
    def selectedCount(self):
        return self._cached_selected_count

    @Property(int, notify=selectionStateChanged)
    def visibleSelectableCount(self):
        """Returns the number of skills currently visible in the view (not collapsed)."""
        return self._cached_visible_selectable

    @Property(int, notify=selectionStateChanged)
    def visibleSelectedCount(self):
        """Returns the number of selected skills that are currently visible."""
        return self._cached_visible_selected

    @Property(int, notify=totalSelectableCountChanged)
    def totalSelectableCount(self):
        return self._cached_total_selectable

    def _update_selection_counts(self):
        """Recomputes cached selection/visibility counts."""
        self._cached_selected_count = sum(
            1 for s in self._all_filtered_skills if s.local_path in self._selected_ids
        )
        self._cached_visible_selectable = sum(1 for s in self._filtered_skills if s.local_path)
        self._cached_visible_selected = sum(
            1 for s in self._filtered_skills if s.local_path and s.local_path in self._selected_ids
        )
        self._cached_total_selectable = len(self._all_filtered_skills)

    # Slots & Methods
    @Slot(int)
    def toggleSelection(self, row):
        if 0 <= row < len(self._filtered_skills):
            skill = self._filtered_skills[row]
            path = skill.local_path
            if not path or self._is_main_collapsed(skill) or self._is_sub_collapsed(skill):
                return
            if path in self._selected_ids:
                self._selected_ids.pop(path, None)
            else:
                self._selected_ids[path] = None
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsSelectedRole])
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self._save_project_selections()

    @Slot()
    def clearSelection(self):
        self._selected_ids.clear()
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self._save_project_selections()

    @Slot()
    def selectAll(self):
        for skill in self._all_filtered_skills:
            if skill.local_path:
                self._selected_ids[skill.local_path] = None
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self._save_project_selections()

    @Slot(result=list)
    def getSelectedPaths(self):
        return list(self._selected_ids)

    @Slot(result=list)
    def getFilteredSelectedPaths(self):
        """Return selected paths limited to currently filtered (project-scoped) skills."""
        filtered_paths = {s.local_path for s in self._all_filtered_skills if s.local_path}
        return [p for p in self._selected_ids if p in filtered_paths]

    @Slot(list)
    def selectByPaths(self, paths):
        for path in paths:
            if path:
                self._selected_ids[path] = None
        self._emit_selection_data_changed()
        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self._save_project_selections()

    def removeSkillsByPath(self, paths: list):
        path_set = set(paths)
        self._all_skills = [s for s in self._all_skills if s.local_path not in path_set]
        for path in path_set:
            self._selected_ids.pop(path, None)

        if self._search_engine:
            self._search_engine.remove_from_index(list(path_set))

        self._apply_filter()
        self.selectionStateChanged.emit()
        self._save_project_selections()

    def updateSkillProperty(self, path: str, key: str, value: Any) -> bool:
        """Updates a property for a skill identified by its local_path.
        Returns True if at least one skill was updated.
        """
        changed = False
        # Update in the master list
        for skill in self._all_skills:
            lp = skill.local_path if hasattr(skill, "local_path") else skill.get("local_path")
            if lp == path:
                if isinstance(skill, dict):
                    skill[key] = value
                else:
                    setattr(skill, key, value)
                changed = True

        if not changed:
            return False

        if key == "is_starred":
            self._apply_filter_with_diff()
            return True

        # If it's in the currently filtered list, emit dataChanged
        for i, skill in enumerate(self._filtered_skills):
            lp = skill.local_path if hasattr(skill, "local_path") else skill.get("local_path")
            if lp == path:
                idx = self.index(i, 0)
                # Find role by name if possible, or just emit all
                self.dataChanged.emit(idx, idx)
                break

        self.selectionStateChanged.emit()
        return True

    def _apply_filter(self, reset=False):
        """Applies filters and updates the model synchronously.

        When ``_suppress_layout`` is True, the filter+sort pipeline is
        deferred to ``_end_batch()`` so redundant work is eliminated.
        """
        if self._suppress_layout:
            self._batch_apply_needed = True
            return

        if reset:
            self.beginResetModel()
        else:
            self.layoutAboutToBeChanged.emit()

        try:
            skills = self._execute_filter_logic()
            self._all_filtered_skills = self._engine.prepare_rows(skills)
            self._filtered_skills = self._engine.build_visible_rows(
                self._all_filtered_skills, self.state.collapsed_categories
            )
        except Exception as e:
            logger.error("Error applying filter: %s", e)
        finally:
            if reset:
                self.endResetModel()
            else:
                self.layoutChanged.emit()
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self.totalSelectableCountChanged.emit()

    def _apply_filter_with_diff(self):
        """Applies filters but uses list diffing to emit correct Qt signals for sleek animations."""
        old_list = list(self._filtered_skills)
        try:
            skills = self._execute_filter_logic()
            self._all_filtered_skills = self._engine.prepare_rows(skills)
            new_list = self._engine.build_visible_rows(
                self._all_filtered_skills, self.state.collapsed_categories
            )
        except Exception as e:
            logger.error("Error applying filter for diff: %s", e)
            return

        import difflib

        old_keys = [s.local_path if s.local_path else str(id(s)) for s in old_list]
        new_keys = [s.local_path if s.local_path else str(id(s)) for s in new_list]

        matcher = difflib.SequenceMatcher(None, old_keys, new_keys)

        for tag, i1, i2, j1, j2 in reversed(matcher.get_opcodes()):
            if tag == "replace":
                self.beginRemoveRows(QModelIndex(), i1, i2 - 1)
                del self._filtered_skills[i1:i2]
                self.endRemoveRows()
                self.beginInsertRows(QModelIndex(), i1, i1 + (j2 - j1) - 1)
                self._filtered_skills[i1:i1] = new_list[j1:j2]
                self.endInsertRows()
            elif tag == "delete":
                self.beginRemoveRows(QModelIndex(), i1, i2 - 1)
                del self._filtered_skills[i1:i2]
                self.endRemoveRows()
            elif tag == "insert":
                self.beginInsertRows(QModelIndex(), i1, i1 + (j2 - j1) - 1)
                self._filtered_skills[i1:i1] = new_list[j1:j2]
                self.endInsertRows()
            elif tag == "equal":
                for idx in range(i1, i2):
                    self._filtered_skills[idx] = new_list[j1 + (idx - i1)]
                if i2 > i1:
                    self.dataChanged.emit(self.index(i1, 0), self.index(i2 - 1, 0))

        self._update_selection_counts()
        self.selectionStateChanged.emit()
        self.totalSelectableCountChanged.emit()

    def _begin_batch(self):
        """Suppress layout signals and filter work until _end_batch()."""
        self._suppress_layout = True
        self._batch_apply_needed = False

    def _end_batch(self):
        """Re-enable layout signals and emit a single layoutChanged."""
        self._suppress_layout = False
        if self._batch_apply_needed:
            self._batch_apply_needed = False
            self._apply_filter()

    def _execute_filter_logic(self) -> list[Skill]:
        """Internal synchronous logic for filtering and searching."""
        if self.state.filter_text and self._search_engine:
            valid_paths = {
                s.local_path for s in self._engine.filter_skills(self._all_skills, self.state)
            }
            results = self._search_engine.query(self.state.filter_text, valid_paths=valid_paths)
            path_to_skill = {s.local_path: s for s in self._all_skills}
            return [
                path_to_skill.get(r[0].get("local_path", ""), Skill.from_dict(r[0]))
                for r in results
            ]
        skills = self._engine.filter_skills(self._all_skills, self.state)
        skills.sort(key=self._engine.sort_key)
        return skills

    def _is_main_collapsed(self, skill: Skill):
        return (
            skill.main_category_name or self._engine.get_main_category(skill)
        ) in self.state.collapsed_categories

    def _is_sub_collapsed(self, skill: Skill):
        return (
            skill.section_name or self._engine.get_section(skill)
        ) in self.state.collapsed_categories

    def _emit_selection_data_changed(self):
        if not self._filtered_skills:
            return
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(len(self._filtered_skills) - 1, 0),
            [self.IsSelectedRole],
        )

    @Slot(int, result=dict)
    def get_skill_at(self, row):
        if 0 <= row < len(self._filtered_skills):
            # QML expects a dict or object it can access.
            # dataclasses are accessible in QML if registered,
            # but here we might need to return a dict for safety.
            import dataclasses

            return dataclasses.asdict(self._filtered_skills[row])
        return {}

    @Slot(list)
    def setSkills(self, skills: list[dict[str, Any]]):
        was_empty = len(self._all_skills) == 0
        self._all_skills = [Skill.from_dict_fast(s) for s in skills]
        self._search_engine = SearchEngine(skills)
        self._apply_filter(reset=was_empty)

    @Slot(list)
    def addOrUpdateSkills(self, new_skills: list[dict[str, Any]]):
        was_empty = len(self._all_skills) == 0
        updated_paths = {s_dict.get("local_path", "") for s_dict in new_skills}
        skills_dict = {s.local_path: s for s in self._all_skills}
        for s_dict in new_skills:
            skill = Skill.from_dict_fast(s_dict)
            skills_dict[skill.local_path] = skill
        self._all_skills = list(skills_dict.values())

        # Use incremental update if engine exists, else full init
        if self._search_engine:
            self._search_engine.update_index(new_skills)
        else:
            self._search_engine = SearchEngine(new_skills)

        self._apply_filter(reset=was_empty)

        if updated_paths and not was_empty:
            for row, skill in enumerate(self._filtered_skills):
                if skill.local_path in updated_paths:
                    idx = self.index(row, 0)
                    self.dataChanged.emit(idx, idx, self._ALL_ROLES)

    @Slot(int, bool)
    def setSelected(self, row, selected):
        if 0 <= row < len(self._filtered_skills):
            path = self._filtered_skills[row].local_path
            if not path:
                return
            if selected:
                self._selected_ids[path] = None
            else:
                self._selected_ids.pop(path, None)
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsSelectedRole])
            self._update_selection_counts()
            self.selectionStateChanged.emit()
            self._save_project_selections()

    @Property(list, notify=collapsedCategoriesChanged)
    def collapsedCategories(self):
        return list(self.state.collapsed_categories)

    @Property(bool, notify=collapsedCategoriesChanged)
    def isAllExpanded(self):
        return len(self.state.collapsed_categories) == 0

    @Slot()
    def toggleAll(self):
        self.collapseAll() if self.isAllExpanded else self.expandAll()

    @Slot(str)
    def toggleCategory(self, name):
        if name in self.state.collapsed_categories:
            self.state.collapsed_categories.remove(name)
        else:
            self.state.collapsed_categories.add(name)
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    @Slot()
    def expandAll(self):
        self.state.collapsed_categories.clear()
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    @Slot()
    def collapseAll(self):
        sections = {
            (s.main_category_name or self._engine.get_main_category(s))
            for s in self._all_filtered_skills
        }
        self.state.collapsed_categories.update(sections)
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    def _rebuild_visible_rows(self):
        self.layoutAboutToBeChanged.emit()
        self._filtered_skills = self._engine.build_visible_rows(
            self._all_filtered_skills, self.state.collapsed_categories
        )
        self.layoutChanged.emit()
        self._update_selection_counts()
        self.selectionStateChanged.emit()

    @Slot(str, result=bool)
    def isCategoryCollapsed(self, name):
        return name in self.state.collapsed_categories

    def _save_collapsed(self):
        if not self._config:
            return
        if self._collapse_save_timer is None:
            from PySide6.QtCore import QTimer

            self._collapse_save_timer = QTimer()
            self._collapse_save_timer.setSingleShot(True)
            self._collapse_save_timer.timeout.connect(self._do_save_collapsed)
            self._collapse_save_timer.setInterval(500)
        self._collapse_save_timer.start()

    def _do_save_collapsed(self):
        if self._config is not None:
            self._config.set("collapsed_categories", list(self.state.collapsed_categories))

    def _save_project_selections(self):
        if not self._config:
            return
        if self._project_selections_save_timer is None:
            from PySide6.QtCore import QTimer

            self._project_selections_save_timer = QTimer()
            self._project_selections_save_timer.setSingleShot(True)
            self._project_selections_save_timer.timeout.connect(self._do_save_project_selections)
            self._project_selections_save_timer.setInterval(500)
        self._project_selections_save_timer.start()

    def _do_save_project_selections(self):
        if self._config is not None:
            self._config.set("project_selections", self._selections_by_project)

    def _save_filters(self):
        if not self._config:
            return
        self._config.set_many(
            {
                "show_archived": self.state.show_archived,
                "category_filter": self.state.category_filter,
                "collection_filter": self.state.collection_filter,
                "project_filter": self.state.project_filter,
                "client_format": self.state.client_filter,
                "show_commands": self.state.show_commands,
                "show_starred": self.state.show_starred,
                "is_package_only": self.state.is_package_only,
                "is_source_only": self.state.is_package_only,
            }
        )
