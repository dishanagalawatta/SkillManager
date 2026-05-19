from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, Qt, Signal, Slot

from skill_manager.core.search import SearchEngine


class SkillModel(QAbstractListModel):
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
        self._all_skills = []
        self._all_filtered_skills = []
        self._filtered_skills = []
        self._filter_text = ""
        self._show_archived = False
        self._category_filter = ""
        self._collection_filter = False
        self._project_filter = ""
        self._client_filter = ""
        self._filter_by_client = True
        self._show_commands = True
        self._show_starred = True
        self._is_package_only = None  # None = All, True = Packages, False = Projects
        self._config = config
        self._collapsed_categories = set()
        self._search_engine = None
        self._selected_ids = set()  # Store selected local_paths for isolation

        if self._config:
            self._collapsed_categories = set(self._config.get("collapsed_categories", []))
            self._show_archived = self._config.get("show_archived", False)
            self._category_filter = self._config.get("category_filter", "")
            self._collection_filter = self._config.get("collection_filter", False)
            self._project_filter = self._config.get("project_filter", "")
            self._client_filter = self._config.get("client_format", "")
            self._show_commands = self._config.get("show_commands", True)
            self._show_starred = self._config.get("show_starred", True)
            self._is_package_only = self._config.get(
                "is_package_only", self._config.get("is_source_only", None)
            )

    def rowCount(self, _parent=QModelIndex()):
        return len(self._filtered_skills)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._filtered_skills):
            return None

        skill = self._filtered_skills[index.row()]
        path = skill.get("local_path", "")

        if role == self.NameRole:
            return skill.get("name", "")
        if role == self.CategoryRole:
            return skill.get("category", "")
        if role == self.DescriptionRole:
            return skill.get("description", "")
        if role == self.PathRole:
            return path
        if role == self.ProjectRole:
            return skill.get("project_label", "")
        if role == self.IsStarredRole:
            return skill.get("is_starred", False)
        if role == self.IsSelectedRole:
            return path in self._selected_ids
        if role == self.IsArchivedRole:
            return skill.get("is_archived", False)
        if role == self.IsCollectionRole:
            return skill.get("is_bundle", False)
        if role == self.SectionRole:
            return skill.get("_section_name", self._section_for_skill(skill))
        if role == self.MainCategoryNameRole:
            return skill.get("_main_category_name", self._main_category_for_skill(skill))
        if role == self.RawContentRole:
            return skill.get("raw_content", "")
        if role == self.BodyContentRole:
            return skill.get("body_content", "")
        if role == self.RiskRole:
            return skill.get("risk", "Unknown")
        if role == self.SourceRole:
            return skill.get("source", "Unknown")
        if role == self.DateRole:
            return skill.get("date", "Unknown")
        if role == self.IsCollapsedRole:
            return self._is_main_collapsed(skill) or self._is_sub_collapsed(skill)
        if role == self.IsCommandRole:
            return skill.get("is_command", False)
        if role == self.ClientRole:
            return skill.get("client", "")
        if role == self.IsFirstInSubcategoryRole:
            return skill.get("_is_first_in_subcategory", False)
        if role == self.IsMainCollapsedRole:
            return self._is_main_collapsed(skill)
        if role == self.IsSubCollapsedRole:
            return self._is_sub_collapsed(skill)
        if role == self.SubCategoryNameRole:
            return skill.get("_sub_category_name", self._sub_category_for_skill(skill))

        return None

    def roleNames(self):
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
        }

    @Property(str, notify=filterChanged)
    def filterText(self):
        return self._filter_text

    @filterText.setter
    def filterText(self, value):
        if self._filter_text != value:
            self._filter_text = value
            self._apply_filter()
            self.filterChanged.emit()

    @Property(bool, notify=showArchivedChanged)
    def showArchived(self):
        return self._show_archived

    @showArchived.setter
    def showArchived(self, value):
        if self._show_archived != value:
            self._show_archived = value
            self._apply_filter()
            self._save_filters()
            self.showArchivedChanged.emit()

    @Property(str, notify=categoryFilterChanged)
    def categoryFilter(self):
        return self._category_filter

    @categoryFilter.setter
    def categoryFilter(self, value):
        if self._category_filter != value:
            self._category_filter = value
            self._apply_filter()
            self._save_filters()
            self.categoryFilterChanged.emit()

    @Property(bool, notify=collectionFilterChanged)
    def collectionFilter(self):
        return self._collection_filter

    @collectionFilter.setter
    def collectionFilter(self, value):
        if self._collection_filter != value:
            self._collection_filter = value
            self._apply_filter()
            self._save_filters()
            self.collectionFilterChanged.emit()

    @Property(str, notify=projectFilterChanged)
    def projectFilter(self):
        return self._project_filter

    @projectFilter.setter
    def projectFilter(self, value):
        if self._project_filter != value:
            self._project_filter = value
            self._apply_filter()
            self._save_filters()
            self.projectFilterChanged.emit()

    @Property(str, notify=clientFilterChanged)
    def clientFilter(self):
        return self._client_filter

    @clientFilter.setter
    def clientFilter(self, value):
        if self._client_filter != value:
            self._client_filter = value
            if self._filter_by_client:
                self._apply_filter()
            self._save_filters()
            self.clientFilterChanged.emit()

    @Property(bool, notify=filterByClientChanged)
    def filterByClient(self):
        return self._filter_by_client

    @filterByClient.setter
    def filterByClient(self, value):
        if self._filter_by_client != value:
            self._filter_by_client = value
            self._apply_filter()
            self.filterByClientChanged.emit()

    @Property(bool, notify=showCommandsChanged)
    def showCommands(self):
        return self._show_commands

    @showCommands.setter
    def showCommands(self, value):
        if self._show_commands != value:
            self._show_commands = value
            self._apply_filter()
            self._save_filters()
            self.showCommandsChanged.emit()

    @Property(bool, notify=showStarredChanged)
    def showStarred(self):
        return self._show_starred

    @showStarred.setter
    def showStarred(self, value):
        if self._show_starred != value:
            self._show_starred = value
            self._apply_filter()
            self._save_filters()
            self.showStarredChanged.emit()

    @Property(Qt.CheckState, notify=isPackageOnlyChanged)
    def isPackageOnly(self):
        # Using CheckState to handle None (PartiallyChecked)
        if self._is_package_only is None:
            return Qt.PartiallyChecked
        return Qt.Checked if self._is_package_only else Qt.Unchecked

    @isPackageOnly.setter
    def isPackageOnly(self, value):
        # Convert QML/Qt values
        new_val = None
        if value == Qt.Checked or value is True:
            new_val = True
        elif value == Qt.Unchecked or value is False:
            new_val = False

        if self._is_package_only != new_val:
            self._is_package_only = new_val
            self._apply_filter()
            self._save_filters()
            self.isPackageOnlyChanged.emit()

    @Property(int, notify=selectedCountChanged)
    def selectedCount(self):
        count = 0
        for skill in self._all_filtered_skills:
            if skill.get("local_path") in self._selected_ids:
                count += 1
        return count

    @Slot(int)
    def toggleSelection(self, row):
        if 0 <= row < len(self._filtered_skills):
            skill = self._filtered_skills[row]
            path = skill.get("local_path")
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
            path = skill.get("local_path")
            if path:
                self._selected_ids.add(path)
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
        """
        Removes skills from the model given their local paths.
        Used after optimistic deletion.
        """
        path_set = set(paths)
        self._all_skills = [s for s in self._all_skills if s.get("local_path") not in path_set]
        self._selected_ids -= path_set
        self._apply_filter()
        self.selectedCountChanged.emit()

    def _apply_filter(self, reset=False):
        if reset:
            self.beginResetModel()
        else:
            self.layoutAboutToBeChanged.emit()

        if self._filter_text and self._search_engine:
            valid_skill_paths = self._valid_skill_paths_for_search()
            results = self._search_engine.query(self._filter_text, valid_paths=valid_skill_paths)
            skills = [result[0] for result in results]
        else:
            skills = self._filtered_source_skills()
            skills.sort(key=self._sort_key)

        self._all_filtered_skills = self._prepare_rows(skills)
        self._filtered_skills = self._build_visible_rows(self._all_filtered_skills)

        if reset:
            self.endResetModel()
        else:
            self.layoutChanged.emit()
        self.selectedCountChanged.emit()

    def _valid_skill_paths_for_search(self):
        return {s.get("local_path") for s in self._filtered_source_skills()}

    def _filtered_source_skills(self):
        project_filter = self._project_filter
        is_package_only = self._is_package_only
        client_filter = (
            self._client_filter.lower()
            if (self._client_filter and self._filter_by_client)
            else None
        )
        category_filter = self._category_filter
        show_archived = self._show_archived
        collection_filter = self._collection_filter
        show_commands = self._show_commands
        show_starred = self._show_starred

        skills = []
        for skill in self._all_skills:
            if not show_archived and skill.get("is_archived", False):
                continue
            if collection_filter and not skill.get("is_bundle", False):
                continue
            if category_filter and skill.get("category") != category_filter:
                continue

            is_starred = skill.get("is_starred", False)
            if (
                project_filter
                and is_package_only is not True
                and skill.get("project_label") != project_filter
            ):
                continue

            if not show_commands and skill.get("is_command", False):
                continue
            if not show_starred and is_starred:
                continue

            is_package = skill.get("is_package", skill.get("is_source", False))
            if is_package_only is True and not is_package:
                continue
            if is_package_only is False and is_package:
                continue

            if client_filter:
                client = skill.get("client")
                if client and client.lower() != client_filter:
                    continue

            skills.append(skill)
        return skills

    def _sort_key(self, skill):
        order_map = {
            "⚙️ System & Workflow": "1_⚙️ System & Workflow",
            "💻 Core Engineering & Technology": "2_💻 Core Engineering & Technology",
            "💼 Business & Operations": "3_💼 Business & Operations",
            "🧪 Quality & Data": "4_🧪 Quality & Data",
            "📚 Content & Knowledge": "5_📚 Content & Knowledge",
            "🎨 Specialized & Lifestyle": "6_🎨 Specialized & Lifestyle",
        }

        if skill.get("is_command", False):
            return (f"0_Special|{skill.get('category', 'General')}", skill.get("name", "").lower())
        if skill.get("is_starred", False):
            return (f"0_Special|{skill.get('category', 'General')}", skill.get("name", "").lower())
        if skill.get("is_bundle", False):
            return ("0_Special|Collections", skill.get("name", "").lower())

        main_cat = skill.get("main_category", "⚙️ System & Workflow")
        sub_cat = skill.get("category", "General")
        name = skill.get("name", "").lower()
        return (f"{order_map.get(main_cat, f'99_{main_cat}')}|{sub_cat}", name)

    def _main_category_for_skill(self, skill):
        if (
            skill.get("is_starred", False)
            or skill.get("is_bundle", False)
            or skill.get("is_command", False)
        ):
            return "Special"
        return skill.get("main_category", "⚙️ System & Workflow")

    def _sub_category_for_skill(self, skill):
        if skill.get("is_command", False):
            return skill.get("category", "Custom Commands") or "Custom Commands"
        if skill.get("is_starred", False):
            return skill.get("category", "General")
        if skill.get("is_bundle", False):
            return "Collections"
        return skill.get("category", "General")

    def _section_for_skill(self, skill):
        return f"{self._main_category_for_skill(skill)}|{self._sub_category_for_skill(skill)}"

    def _prepare_rows(self, skills):
        prepared = []
        previous_section = None
        for skill in skills:
            main_cat = self._main_category_for_skill(skill)
            sub_cat = self._sub_category_for_skill(skill)
            section = f"{main_cat}|{sub_cat}"
            row = dict(skill)
            row["_main_category_name"] = main_cat
            row["_sub_category_name"] = sub_cat
            row["_section_name"] = section
            row["_is_first_in_subcategory"] = section != previous_section
            prepared.append(row)
            previous_section = section
        return prepared

    def _is_main_collapsed(self, skill):
        main_cat = skill.get("_main_category_name", self._main_category_for_skill(skill))
        return main_cat in self._collapsed_categories

    def _is_sub_collapsed(self, skill):
        section = skill.get("_section_name", self._section_for_skill(skill))
        return section in self._collapsed_categories

    def _build_visible_rows(self, skills):
        visible = []
        seen_main = set()
        seen_section = set()
        for skill in skills:
            main_cat = skill.get("_main_category_name", self._main_category_for_skill(skill))
            section = skill.get("_section_name", self._section_for_skill(skill))

            if main_cat in self._collapsed_categories:
                if main_cat not in seen_main:
                    visible.append(skill)
                    seen_main.add(main_cat)
                continue

            seen_main.add(main_cat)
            if self._is_sub_collapsed(skill):
                if section not in seen_section:
                    visible.append(skill)
                    seen_section.add(section)
                continue

            visible.append(skill)
            seen_section.add(section)
        return visible

    def _rebuild_visible_rows(self):
        self.layoutAboutToBeChanged.emit()
        self._filtered_skills = self._build_visible_rows(self._all_filtered_skills)
        self.layoutChanged.emit()
        self.selectedCountChanged.emit()

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
            return self._filtered_skills[row]
        return {}

    @Slot(list)
    def setSkills(self, skills):
        self._all_skills = skills
        self._search_engine = SearchEngine(skills)
        self._apply_filter(reset=True)

    @Slot(list)
    def addOrUpdateSkills(self, new_skills):
        """Surgically adds or updates a list of skills in the model without a full reload."""
        skills_dict = {s["local_path"]: s for s in self._all_skills}
        for skill in new_skills:
            skills_dict[skill["local_path"]] = skill
        self._all_skills = list(skills_dict.values())
        self._search_engine = SearchEngine(self._all_skills)
        self._apply_filter(reset=True)

    @Slot(int, bool)
    def setSelected(self, row, selected):
        if 0 <= row < len(self._filtered_skills):
            skill = self._filtered_skills[row]
            path = skill.get("local_path")
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
        return list(self._collapsed_categories)

    @Property(bool, notify=collapsedCategoriesChanged)
    def isAllExpanded(self):
        return len(self._collapsed_categories) == 0

    @Slot()
    def toggleAll(self):
        if self.isAllExpanded:
            self.collapseAll()
        else:
            self.expandAll()

    @Slot(str)
    def toggleCategory(self, name):
        if name in self._collapsed_categories:
            self._collapsed_categories.remove(name)
        else:
            self._collapsed_categories.add(name)

        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    @Slot()
    def expandAll(self):
        self._collapsed_categories.clear()
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    @Slot()
    def collapseAll(self):
        sections = {
            skill.get("_main_category_name", self._main_category_for_skill(skill))
            for skill in self._all_filtered_skills
        }
        self._collapsed_categories.update(sections)
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self._rebuild_visible_rows()

    @Slot(str, result=bool)
    def isCategoryCollapsed(self, name):
        return name in self._collapsed_categories

    def _save_collapsed(self):
        if self._config:
            self._config.set("collapsed_categories", list(self._collapsed_categories))

    def _save_filters(self):
        if self._config:
            self._config.set("show_archived", self._show_archived)
            self._config.set("category_filter", self._category_filter)
            self._config.set("collection_filter", self._collection_filter)
            self._config.set("project_filter", self._project_filter)
            self._config.set("client_format", self._client_filter)
            self._config.set("show_commands", self._show_commands)
            self._config.set("show_starred", self._show_starred)
            self._config.set("is_package_only", self._is_package_only)
            self._config.set("is_source_only", self._is_package_only)
