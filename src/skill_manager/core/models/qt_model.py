from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, Qt, Signal, Slot

from skill_manager.core.models.entities import FilterState, Skill
from skill_manager.core.models.filter_engine import FilterEngine
from skill_manager.core.search import SearchEngine


class SkillModel(QAbstractListModel):
    """
    Qt List Model for skills, delegating logic to FilterEngine.
    """

    NameRole = Qt.UserRole + 1
    CategoryRole = Qt.UserRole + 2
    DescriptionRole = Qt.UserRole + 3
    PathRole = Qt.UserRole + 4
    ProjectRole = Qt.UserRole + 5
    IsStarredRole = Qt.UserRole + 6
    IsSelectedRole = Qt.UserRole + 7
    SearchTextRole = Qt.UserRole + 8
    IsArchivedRole = Qt.UserRole + 9
    IsCollectionRole = Qt.UserRole + 10
    SectionRole = Qt.UserRole + 11
    RawContentRole = Qt.UserRole + 12
    BodyContentRole = Qt.UserRole + 13
    RiskRole = Qt.UserRole + 14
    SourceRole = Qt.UserRole + 15
    DateRole = Qt.UserRole + 16
    IsCollapsedRole = Qt.UserRole + 17
    IsCommandRole = Qt.UserRole + 18
    ClientRole = Qt.UserRole + 19
    MainCategoryNameRole = Qt.UserRole + 20
    IsFirstInSubcategoryRole = Qt.UserRole + 21
    IsMainCollapsedRole = Qt.UserRole + 22
    IsSubCollapsedRole = Qt.UserRole + 23
    SubCategoryNameRole = Qt.UserRole + 24
    IsPackageRole = Qt.UserRole + 25

    filterChanged = Signal()
    showArchivedChanged = Signal()
    categoryFilterChanged = Signal()
    collectionFilterChanged = Signal()
    projectFilterChanged = Signal()
    selectedCountChanged = Signal()
    collapsedCategoriesChanged = Signal()
    showCommandsChanged = Signal()
    showStarredChanged = Signal()
    isPackageOnlyChanged = Signal()
    clientFilterChanged = Signal()
    filterByClientChanged = Signal()
    userSelectionChanged = Signal()

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self._all_skills: list[Skill] = []
        self._all_filtered_skills: list[Skill] = []
        self._filtered_skills: list[Skill] = []
        self._config = config
        self._search_engine = None
        self._selected_ids: set[str] = set()
        self._engine = FilterEngine()
        self._state = FilterState()

        if self._config:
            self._state.collapsed_categories = set(self._config.get("collapsed_categories", []))
            self._state.show_archived = self._config.get("show_archived", False)
            self._state.category_filter = self._config.get("category_filter", "")
            self._state.collection_filter = self._config.get("collection_filter", False)
            self._state.project_filter = self._config.get("project_filter", "")
            self._state.client_filter = self._config.get("client_format", "")
            self._state.show_commands = self._config.get("show_commands", True)
            self._state.show_starred = self._config.get("show_starred", True)
            self._state.is_package_only = self._config.get(
                "is_package_only", self._config.get("is_source_only", None)
            )

    def rowCount(self, _parent=QModelIndex()):
        return len(self._filtered_skills)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
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
            return skill._section_name or self._engine.get_section(skill)
        if role == self.MainCategoryNameRole:
            return skill._main_category_name or self._engine.get_main_category(skill)
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
            return skill._is_first_in_subcategory
        if role == self.IsMainCollapsedRole:
            return self._is_main_collapsed(skill)
        if role == self.IsSubCollapsedRole:
            return self._is_sub_collapsed(skill)
        if role == self.SubCategoryNameRole:
            return skill._sub_category_name or self._engine.get_sub_category(skill)
        if role == self.IsPackageRole:
            return skill.is_package

        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.NameRole: b"name",
            self.CategoryRole: b"category",
            self.DescriptionRole: b"description",
            self.PathRole: b"path",
            self.ProjectRole: b"project",
            self.IsStarredRole: b"isStarred",
            self.IsSelectedRole: b"isSelected",
            self.SearchTextRole: b"searchText",
            self.IsArchivedRole: b"isArchived",
            self.IsCollectionRole: b"isCollection",
            self.SectionRole: b"sectionName",
            self.RawContentRole: b"rawContent",
            self.BodyContentRole: b"bodyContent",
            self.RiskRole: b"risk",
            self.SourceRole: b"source",
            self.MainCategoryNameRole: b"mainCategoryName",
            self.DateRole: b"date",
            self.IsCollapsedRole: b"isCollapsed",
            self.IsCommandRole: b"isCommand",
            self.ClientRole: b"client",
            self.IsFirstInSubcategoryRole: b"isFirstInSubcategory",
            self.IsMainCollapsedRole: b"isMainCollapsed",
            self.IsSubCollapsedRole: b"isSubCollapsed",
            self.SubCategoryNameRole: b"subCategoryName",
            self.IsPackageRole: b"isPackage",
        }

    # Properties
    @Property(str, notify=filterChanged)
    def filterText(self):
        return self._state.filter_text

    @filterText.setter
    def filterText(self, value):
        if self._state.filter_text != value:
            self._state.filter_text = value
            self._apply_filter()
            self.filterChanged.emit()

    @Property(bool, notify=showArchivedChanged)
    def showArchived(self):
        return self._state.show_archived

    @showArchived.setter
    def showArchived(self, value):
        if self._state.show_archived != value:
            self._state.show_archived = value
            self._apply_filter()
            self._save_filters()
            self.showArchivedChanged.emit()

    @Property(str, notify=categoryFilterChanged)
    def categoryFilter(self):
        return self._state.category_filter

    @categoryFilter.setter
    def categoryFilter(self, value):
        if self._state.category_filter != value:
            self._state.category_filter = value
            self._apply_filter()
            self._save_filters()
            self.categoryFilterChanged.emit()

    @Property(bool, notify=collectionFilterChanged)
    def collectionFilter(self):
        return self._state.collection_filter

    @collectionFilter.setter
    def collectionFilter(self, value):
        if self._state.collection_filter != value:
            self._state.collection_filter = value
            self._apply_filter()
            self._save_filters()
            self.collectionFilterChanged.emit()

    @Property(str, notify=projectFilterChanged)
    def projectFilter(self):
        return self._state.project_filter

    @projectFilter.setter
    def projectFilter(self, value):
        if self._state.project_filter != value:
            self._state.project_filter = value
            self._apply_filter()
            self._save_filters()
            self.projectFilterChanged.emit()

    @Property(str, notify=clientFilterChanged)
    def clientFilter(self):
        return self._state.client_filter

    @clientFilter.setter
    def clientFilter(self, value):
        if self._state.client_filter != value:
            self._state.client_filter = value
            if self._state.filter_by_client:
                self._apply_filter()
            self._save_filters()
            self.clientFilterChanged.emit()

    @Property(bool, notify=filterByClientChanged)
    def filterByClient(self):
        return self._state.filter_by_client

    @filterByClient.setter
    def filterByClient(self, value):
        if self._state.filter_by_client != value:
            self._state.filter_by_client = value
            self._apply_filter()
            self.filterByClientChanged.emit()

    @Property(bool, notify=showCommandsChanged)
    def showCommands(self):
        return self._state.show_commands

    @showCommands.setter
    def showCommands(self, value):
        if self._state.show_commands != value:
            self._state.show_commands = value
            self._apply_filter()
            self._save_filters()
            self.showCommandsChanged.emit()

    @Property(bool, notify=showStarredChanged)
    def showStarred(self):
        return self._state.show_starred

    @showStarred.setter
    def showStarred(self, value):
        if self._state.show_starred != value:
            self._state.show_starred = value
            self._apply_filter()
            self._save_filters()
            self.showStarredChanged.emit()

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):
        if self._state.is_package_only is None:
            return Qt.PartiallyChecked
        return Qt.Checked if self._state.is_package_only else Qt.Unchecked

    @isPackageOnly.setter
    def isPackageOnly(self, value):
        new_val = None
        if value == Qt.Checked or value is True:
            new_val = True
        elif value == Qt.Unchecked or value is False:
            new_val = False
        if self._state.is_package_only != new_val:
            self._state.is_package_only = new_val
            self._apply_filter()
            self._save_filters()
            self.isPackageOnlyChanged.emit()

    @Property(int, notify=selectedCountChanged)
    def selectedCount(self):
        return sum(1 for s in self._all_filtered_skills if s.local_path in self._selected_ids)

    # Slots & Methods
    @Slot(int)
    def toggleSelection(self, row):
        if 0 <= row < len(self._filtered_skills):
            skill = self._filtered_skills[row]
            path = skill.local_path
            if not path or self._is_main_collapsed(skill) or self._is_sub_collapsed(skill):
                return
            if path in self._selected_ids:
                self._selected_ids.remove(path)
            else:
                self._selected_ids.add(path)
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsSelectedRole])
            self.selectedCountChanged.emit()
            self.userSelectionChanged.emit()

    @Slot()
    def clearSelection(self):
        self._selected_ids.clear()
        self._emit_selection_data_changed()
        self.selectedCountChanged.emit()
        self.userSelectionChanged.emit()

    @Slot()
    def selectAll(self):
        for skill in self._filtered_skills:
            if self._is_main_collapsed(skill) or self._is_sub_collapsed(skill):
                continue
            if skill.local_path:
                self._selected_ids.add(skill.local_path)
        self._emit_selection_data_changed()
        self.selectedCountChanged.emit()

    @Slot(result=list)
    def getSelectedPaths(self):
        return list(self._selected_ids)

    @Slot(list)
    def selectByPaths(self, paths):
        for path in paths:
            if path:
                self._selected_ids.add(path)
        self._emit_selection_data_changed()
        self.selectedCountChanged.emit()
        self.userSelectionChanged.emit()

    def removeSkillsByPath(self, paths: list):
        path_set = set(paths)
        self._all_skills = [s for s in self._all_skills if s.local_path not in path_set]
        self._selected_ids -= path_set

        if self._search_engine:
            self._search_engine.remove_from_index(list(path_set))

        self._apply_filter()
        self.selectedCountChanged.emit()

    def _apply_filter(self, reset=False):
        """Gateway to trigger filtering, offloading to async if needed."""

        import PySide6.QtAsyncio as QtAsyncio

        # Cancel any pending filter task to prevent race conditions
        if hasattr(self, "_filter_task") and self._filter_task and not self._filter_task.done():
            self._filter_task.cancel()

        self._filter_task = QtAsyncio.run(self._apply_filter_async(reset))

    async def _apply_filter_async(self, reset=False):
        """Asynchronous implementation of filtering and sorting."""
        import asyncio

        if reset:
            self.beginResetModel()
        else:
            self.layoutAboutToBeChanged.emit()

        try:
            loop = asyncio.get_running_loop()

            # Execute the heavy filtering/searching in a background thread
            skills = await loop.run_in_executor(None, self._execute_filter_logic)

            self._all_filtered_skills = self._engine.prepare_rows(skills)
            self._filtered_skills = self._engine.build_visible_rows(
                self._all_filtered_skills, self._state.collapsed_categories
            )
        except asyncio.CancelledError:
            # Task was cancelled by a newer filter request, just exit
            return
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in async filter: {e}")
        finally:
            if reset:
                self.endResetModel()
            else:
                self.layoutChanged.emit()
            self.selectedCountChanged.emit()

    def _execute_filter_logic(self) -> list[Skill]:
        """Internal synchronous logic for filtering and searching."""
        if self._state.filter_text and self._search_engine:
            valid_paths = {
                s.local_path for s in self._engine.filter_skills(self._all_skills, self._state)
            }
            results = self._search_engine.query(self._state.filter_text, valid_paths=valid_paths)
            skills = []
            for result in results:
                s = result[0]
                if isinstance(s, dict):
                    skills.append(Skill.from_dict(s))
                else:
                    skills.append(s)
            return skills
        skills = self._engine.filter_skills(self._all_skills, self._state)
        skills.sort(key=self._engine.sort_key)
        return skills

    def _is_main_collapsed(self, skill: Skill):
        return (
            skill._main_category_name or self._engine.get_main_category(skill)
        ) in self._state.collapsed_categories

    def _is_sub_collapsed(self, skill: Skill):
        return (
            skill._section_name or self._engine.get_section(skill)
        ) in self._state.collapsed_categories

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
        self._all_skills = [Skill.from_dict(s) for s in skills]
        self._search_engine = SearchEngine(skills)  # Keep raw dicts for SearchEngine for now
        self._apply_filter(reset=was_empty)

    @Slot(list)
    def addOrUpdateSkills(self, new_skills: list[dict[str, Any]]):
        was_empty = len(self._all_skills) == 0
        skills_dict = {s.local_path: s for s in self._all_skills}
        for s_dict in new_skills:
            skill = Skill.from_dict(s_dict)
            skills_dict[skill.local_path] = skill
        self._all_skills = list(skills_dict.values())

        # Use incremental update if engine exists, else full init
        if self._search_engine:
            self._search_engine.update_index(new_skills)
        else:
            self._search_engine = SearchEngine(new_skills)

        self._apply_filter(reset=was_empty)

    @Slot(int, bool)
    def setSelected(self, row, selected):
        if 0 <= row < len(self._filtered_skills):
            path = self._filtered_skills[row].local_path
            if not path:
                return
            if selected:
                self._selected_ids.add(path)
            else:
                self._selected_ids.discard(path)
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsSelectedRole])
            self.selectedCountChanged.emit()

    @Property(list, notify=collapsedCategoriesChanged)
    def collapsedCategories(self):
        return list(self._state.collapsed_categories)

    @Property(bool, notify=collapsedCategoriesChanged)
    def isAllExpanded(self):
        return len(self._state.collapsed_categories) == 0

    @Slot()
    def toggleAll(self):
        self.collapseAll() if self.isAllExpanded else self.expandAll()

    @Slot(str)
    def toggleCategory(self, name):
        if name in self._state.collapsed_categories:
            self._state.collapsed_categories.remove(name)
        else:
            self._state.collapsed_categories.add(name)
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    @Slot()
    def expandAll(self):
        self._state.collapsed_categories.clear()
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    @Slot()
    def collapseAll(self):
        sections = {
            (s._main_category_name or self._engine.get_main_category(s))
            for s in self._all_filtered_skills
        }
        self._state.collapsed_categories.update(sections)
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    def _rebuild_visible_rows(self):
        self.layoutAboutToBeChanged.emit()
        self._filtered_skills = self._engine.build_visible_rows(
            self._all_filtered_skills, self._state.collapsed_categories
        )
        self.layoutChanged.emit()
        self.selectedCountChanged.emit()

    @Slot(str, result=bool)
    def isCategoryCollapsed(self, name):
        return name in self._state.collapsed_categories

    def _save_collapsed(self):
        if self._config:
            self._config.set("collapsed_categories", list(self._state.collapsed_categories))

    def _save_filters(self):
        if not self._config:
            return
        c = self._config
        s = self._state
        c.set("show_archived", s.show_archived)
        c.set("category_filter", s.category_filter)
        c.set("collection_filter", s.collection_filter)
        c.set("project_filter", s.project_filter)
        c.set("client_format", s.client_filter)
        c.set("show_commands", s.show_commands)
        c.set("show_starred", s.show_starred)
        c.set("is_package_only", s.is_package_only)
        c.set("is_source_only", s.is_package_only)
