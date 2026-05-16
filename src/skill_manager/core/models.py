from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, Qt, Signal, Slot

from skill_manager.core.search import SearchEngine


class SkillModel(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    CategoryRole = Qt.UserRole + 2
    DescriptionRole = Qt.UserRole + 3
    PathRole = Qt.UserRole + 4
    ProjectRole = Qt.UserRole + 5
    IsEssentialRole = Qt.UserRole + 6
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

    filterChanged = Signal()
    showArchivedChanged = Signal()
    categoryFilterChanged = Signal()
    collectionFilterChanged = Signal()
    projectFilterChanged = Signal()
    selectedCountChanged = Signal()
    collapsedCategoriesChanged = Signal()
    showCommandsChanged = Signal()
    showEssentialsChanged = Signal()
    isSourceOnlyChanged = Signal()
    clientFilterChanged = Signal()
    userSelectionChanged = Signal()

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self._all_skills = []
        self._filtered_skills = []
        self._filter_text = ""
        self._show_archived = False
        self._category_filter = ""
        self._collection_filter = False
        self._project_filter = ""
        self._client_filter = ""
        self._show_commands = True
        self._show_essentials = True
        self._is_source_only = None # None = All, True = Sources, False = Projects
        self._config = config
        self._collapsed_categories = set()
        self._search_engine = None
        self._selected_ids = set() # Store selected local_paths for isolation


        if self._config:
            self._collapsed_categories = set(self._config.get("collapsed_categories", []))
            self._show_archived = self._config.get("show_archived", False)
            self._category_filter = self._config.get("category_filter", "")
            self._collection_filter = self._config.get("collection_filter", False)
            self._project_filter = self._config.get("project_filter", "")
            self._client_filter = self._config.get("client_format", "")
            self._show_commands = self._config.get("show_commands", True)
            self._show_essentials = self._config.get("show_essentials", True)
            self._is_source_only = self._config.get("is_source_only", None)

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
        if role == self.IsEssentialRole:
            return skill.get("is_essential", False)
        if role == self.IsSelectedRole:
            return path in self._selected_ids
        if role == self.IsArchivedRole:
            return skill.get("is_archived", False)
        if role == self.IsCollectionRole:
            return skill.get("is_bundle", False)
        if role == self.SectionRole:
            if skill.get("is_command", False):
                return f"Special|{skill.get('category', 'Custom Commands') or 'Custom Commands'}"
            if skill.get("is_essential", False):
                return "Special|Essentials"
            if skill.get("is_bundle", False):
                return "Special|Collections"

            main_cat = skill.get("main_category", "⚙️ System & Workflow")
            sub_cat = skill.get("category", "General")
            return f"{main_cat}|{sub_cat}"
        if role == self.MainCategoryNameRole:
            return skill.get("main_category", "⚙️ System & Workflow")
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
            section = self.data(index, self.SectionRole)
            return section in self._collapsed_categories
        if role == self.IsCommandRole:
            return skill.get("is_command", False)
        if role == self.ClientRole:
            return skill.get("client", "")

        return None

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.CategoryRole: b"category",
            self.DescriptionRole: b"description",
            self.PathRole: b"path",
            self.ProjectRole: b"project",
            self.IsEssentialRole: b"isEssential",
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
            self.ClientRole: b"client"
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
            self._apply_filter()
            self._save_filters()
            self.clientFilterChanged.emit()

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

    @Property(bool, notify=showEssentialsChanged)
    def showEssentials(self):
        return self._show_essentials

    @showEssentials.setter
    def showEssentials(self, value):
        if self._show_essentials != value:
            self._show_essentials = value
            self._apply_filter()
            self._save_filters()
            self.showEssentialsChanged.emit()

    @Property(Qt.CheckState, notify=isSourceOnlyChanged)
    def isSourceOnly(self):
        # Using CheckState to handle None (PartiallyChecked)
        if self._is_source_only is None:
            return Qt.PartiallyChecked
        return Qt.Checked if self._is_source_only else Qt.Unchecked

    @isSourceOnly.setter
    def isSourceOnly(self, value):
        # Convert QML/Qt values
        new_val = None
        if value == Qt.Checked or value is True:
            new_val = True
        elif value == Qt.Unchecked or value is False:
            new_val = False

        if self._is_source_only != new_val:
            self._is_source_only = new_val
            self._apply_filter()
            self._save_filters()
            self.isSourceOnlyChanged.emit()

    @Property(int, notify=selectedCountChanged)
    def selectedCount(self):
        # We only count selected items that are currently visible in the filtered list
        count = 0
        for s in self._filtered_skills:
            if s.get("local_path") in self._selected_ids:
                count += 1
        return count

    @Slot(int)
    def toggleSelection(self, row):
        if 0 <= row < len(self._filtered_skills):
            skill = self._filtered_skills[row]
            path = skill.get("local_path")
            if not path:
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
        self.beginResetModel()
        self.endResetModel()
        self.selectedCountChanged.emit()
        self.userSelectionChanged.emit()

    @Slot()
    def selectAll(self):
        for s in self._filtered_skills:
            path = s.get("local_path")
            if path:
                self._selected_ids.add(path)
        self.beginResetModel()
        self.endResetModel()
        self.selectedCountChanged.emit()

    @Slot(result=list)
    def getSelectedPaths(self):
        return list(self._selected_ids)

    @Slot(list)
    def selectByPaths(self, paths):
        for path in paths:
            if path:
                self._selected_ids.add(path)
        self.beginResetModel()
        self.endResetModel()
        self.selectedCountChanged.emit()
        self.userSelectionChanged.emit()

    def removeSkillsByPath(self, paths: list):
        """
        Removes skills from the model given their local paths.
        Used after optimistic deletion.
        """
        path_set = set(paths)
        self._all_skills = [s for s in self._all_skills if s.get('local_path') not in path_set]
        self._selected_ids -= path_set
        self._apply_filter()
        self.selectedCountChanged.emit()

    def _apply_filter(self):
        self.beginResetModel()

        # Check if searching is active
        if self._filter_text and self._search_engine:
            # We defer filtering to the search engine.
            # But we must pass a set of valid paths that match all other filters.

            # Extract filters locally to avoid property lookups in the loop
            project_filter = self._project_filter
            is_source_only = self._is_source_only
            client_filter = self._client_filter.lower() if self._client_filter else None
            category_filter = self._category_filter
            show_archived = self._show_archived
            collection_filter = self._collection_filter
            show_commands = self._show_commands
            show_essentials = self._show_essentials

            valid_skill_paths = set()
            for s in self._all_skills:
                if not show_archived and s.get("is_archived", False):
                    continue
                if collection_filter and not s.get("is_bundle", False):
                    continue
                if category_filter and s.get("category") != category_filter:
                    continue

                is_essential = s.get("is_essential", False)

                if project_filter and is_source_only is not True and s.get("project_label") != project_filter and not (is_source_only is False and is_essential):
                    continue

                if not show_commands and s.get("is_command", False):
                    continue
                if not show_essentials and is_essential:
                    continue

                is_source = s.get("is_source", False)
                if is_source_only is True and not is_source:
                    continue
                if is_source_only is False and is_source and not is_essential:
                    continue

                if client_filter:
                    client = s.get("client")
                    if client and client.lower() != client_filter:
                        continue

                valid_skill_paths.add(s.get("local_path"))

            results = self._search_engine.query(self._filter_text, valid_paths=valid_skill_paths)

            # Results are already pre-filtered by valid_paths inside the query method
            self._filtered_skills = [r[0] for r in results]
            self.endResetModel()
            return

        # Optimization: Single-pass filtering instead of 7 multiple list comprehensions.
        # This speeds up filtering dramatically for large numbers of skills.

        project_filter = self._project_filter
        is_source_only = self._is_source_only
        client_filter = self._client_filter.lower() if self._client_filter else None
        category_filter = self._category_filter
        show_archived = self._show_archived
        collection_filter = self._collection_filter
        show_commands = self._show_commands
        show_essentials = self._show_essentials

        skills = []
        for s in self._all_skills:
            if not show_archived and s.get("is_archived", False):
                continue
            if collection_filter and not s.get("is_bundle", False):
                continue
            if category_filter and s.get("category") != category_filter:
                continue

            is_essential = s.get("is_essential", False)

            if project_filter and is_source_only is not True and s.get("project_label") != project_filter and not (is_source_only is False and is_essential):
                continue

            if not show_commands and s.get("is_command", False):
                continue
            if not show_essentials and is_essential:
                continue

            is_source = s.get("is_source", False)
            if is_source_only is True and not is_source:
                continue
            if is_source_only is False and is_source and not is_essential:
                continue

            if client_filter:
                client = s.get("client")
                if client and client.lower() != client_filter:
                    continue

            skills.append(s)

        # 5. Sorting: Essentials first, then by category, then by name
        def sort_key(s):
            is_essential = s.get("is_essential", False)
            is_command = s.get("is_command", False)
            is_bundle = s.get("is_bundle", False)

            main_cat = s.get("main_category", "⚙️ System & Workflow")
            sub_cat = s.get("category", "General")
            name = s.get("name", "").lower()

            if is_command:
                section_sort = f"0_Special|{sub_cat}"
            elif is_essential:
                section_sort = "0_Special|Essentials"
            elif is_bundle:
                section_sort = "0_Special|Collections"
            else:
                # Custom sorting for main categories as requested in docs
                order = {
                    "⚙️ System & Workflow": 1,
                    "🛠️ Core Engineering & Technology": 2,
                    "📈 Business & Operations": 3,
                    "🛡️ Quality & Data": 4,
                    "📚 Content & Knowledge": 5,
                    "🧘 Specialized & Lifestyle": 6
                }
                main_order = order.get(main_cat, 99)
                section_sort = f"{main_order}_{main_cat}|{sub_cat}"

            return (section_sort, name)

        skills.sort(key=sort_key)

        self._filtered_skills = skills
        self.endResetModel()
        self.selectedCountChanged.emit()

    @Slot(int, result=dict)
    def get_skill_at(self, row):
        if 0 <= row < len(self._filtered_skills):
            return self._filtered_skills[row]
        return {}

    @Slot(list)
    def setSkills(self, skills):
        self._all_skills = skills
        self._search_engine = SearchEngine(skills)
        self._apply_filter()

    @Slot(int, bool)
    def setSelected(self, row, selected):
        if 0 <= row < len(self._filtered_skills):
            skill = self._filtered_skills[row]
            path = skill.get("local_path")
            if selected:
                self._selected_ids.add(path)
            else:
                self._selected_ids.discard(path)

            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsSelectedRole])
            self.selectedCountChanged.emit()

    @Property(bool, notify=collapsedCategoriesChanged)
    def isAllExpanded(self):
        return len(self._collapsed_categories) == 0

    @Slot()
    def toggleAll(self):
        if self.isAllExpanded:
            self.collapseAll()
        else:
            self.expandAll()
        self.collapsedCategoriesChanged.emit()

    @Slot(str)
    def toggleCategory(self, name):
        if name in self._collapsed_categories:
            self._collapsed_categories.remove(name)
        else:
            self._collapsed_categories.add(name)

        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self.beginResetModel()
        self.endResetModel()

    @Slot()
    def expandAll(self):
        self._collapsed_categories.clear()
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self.beginResetModel()
        self.endResetModel()

    @Slot()
    def collapseAll(self):
        # Get all unique main categories from filtered skills
        sections = set()
        for skill in self._filtered_skills:
            if skill.get("is_essential", False) or skill.get("is_bundle", False) or skill.get("is_command", False):
                sections.add("Special")
            else:
                sections.add(skill.get("main_category", "⚙️ System & Workflow"))

        self._collapsed_categories.update(sections)
        self._save_collapsed()
        self.collapsedCategoriesChanged.emit()
        self.beginResetModel()
        self.endResetModel()

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
            self._config.set("show_essentials", self._show_essentials)
            self._config.set("is_source_only", self._is_source_only)

