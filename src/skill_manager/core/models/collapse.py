"""Collapse/expansion subsystem for the SkillModel facade."""

from PySide6.QtCore import Property, Slot

from skill_manager.core.models.roles import RolesMixin

collapsedCategoriesChanged = RolesMixin.collapsedCategoriesChanged  # noqa: N816


class CollapseMixin:
    """Category collapse/expansion, visible-row rebuild, and persistence."""

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

    @Slot(str, result=int)
    def firstVisibleRowForCategory(self, name):
        """Index of the first visible row of a collapsed section.

        QML anchor for collapse/expand scroll preservation: after the
        layout pair rebuilds the rows, the view pins this index with
        ``positionViewAtIndex(idx, ListView.Contain)`` so the toggled
        section header stays visible instead of the viewport jumping.
        Matches both main-category names (``"Main"``) and section names
        (``"Main|Sub"``). Returns -1 when the section has no visible row.
        """
        for i, s in enumerate(self._filtered_skills):
            main = s.main_category_name or self._engine.get_main_category(s)
            if main == name:
                return i
            section = s.section_name or self._engine.get_section(s)
            if section == name:
                return i
        return -1

    @Slot(str, result=int)
    def visibleRowCountForCategory(self, name):
        """Number of visible rows belonging to a collapsed section.

        Companion to :meth:`firstVisibleRowForCategory` for QML scroll
        compensation: ``first + count - 1`` is the section's last row, so
        the view can measure the section's on-screen range geometrically
        (via ``itemAtIndex``) without assuming delegate heights.
        """
        n = 0
        for s in self._filtered_skills:
            main = s.main_category_name or self._engine.get_main_category(s)
            section = s.section_name or self._engine.get_section(s)
            if main == name or section == name:
                n += 1
        return n

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
