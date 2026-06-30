from aqt import gui_hooks, mw
from aqt.qt import QCheckBox, QComboBox
from aqt.browser import Browser
from aqt.browser.table import SearchContext
from functools import partial
from aqt.errors import show_exception
from aqt.qt import *


class _MultiSelectMenu(QMenu):
    def __init__(self, parent=None, single_selection=False, on_change=None):
        super().__init__(parent)
        self._exclusive_action = None
        self._clear_action = None
        self._single_selection = single_selection
        self._on_change = on_change

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        if action and action.isCheckable():
            if action is self._clear_action:
                for a in self.actions():
                    a.setChecked(False)
            elif self._single_selection:
                # If the clicked action is already checked, uncheck it
                if action.isChecked():
                    action.setChecked(False)
                else:
                    # Uncheck all other actions
                    for a in self.actions():
                        if a is not action:
                            a.setChecked(False)
                    # Check the clicked action
                    action.setChecked(True)
            else:
                new_state = not action.isChecked()
                action.setChecked(new_state)
                if new_state:
                    if action is self._exclusive_action:
                        for a in self.actions():
                            if a is not action:
                                a.setChecked(False)
                    elif self._exclusive_action is not None:
                        self._exclusive_action.setChecked(False)

            if self._on_change:
                self._on_change()
        else:
            super().mouseReleaseEvent(event)


class CheckableComboBox(QPushButton):
    def __init__(self, placeholder, parent=None, on_change=None, single_selection=False):
        super().__init__(placeholder, parent)
        self._on_change = on_change
        self._menu = _MultiSelectMenu(self, single_selection=single_selection, on_change=self._internal_on_change)
        self.setMenu(self._menu)

    def _internal_on_change(self):
        if self._on_change:
            self._on_change(self.checkedItems())

    def addCheckableItem(self, text, exclusive=False):
        action = QAction(text, self._menu)
        action.setCheckable(True)
        self._menu.addAction(action)
        if exclusive:
            self._menu._exclusive_action = action

    def addClearItem(self, text):
        action = QAction(text, self._menu)
        action.setCheckable(True)
        self._menu.addAction(action)
        self._menu._clear_action = action

    def checkedItems(self):
        return [action.text() for action in self._menu.actions() if action.isChecked()]

    def setChecked(self, items):
        all_items = [a.text() for a in self._menu.actions()]
        for action in self._menu.actions():
            if action.isCheckable():
                action.setChecked(action.text() in items)
        self._internal_on_change()

    def clear(self):
        for action in self._menu.actions():
            if action.isCheckable():
                action.setChecked(False)
        self._internal_on_change()

    def select_first(self):
        self.clear()
        for action in self._menu.actions():
            if action.isCheckable() and action.text() != "(no filter)":
                action.setChecked(True)
                break
        self._internal_on_change()


cbSuspended: QCheckBox = None
cbDue: CheckableComboBox = None
cbStudied: CheckableComboBox = None
cbNew: QCheckBox = None
cbFlag: CheckableComboBox = None
cbRecent: CheckableComboBox = None

# --- Helper function to create a switchable combo box ---
def create_switchable_combobox(browser: Browser, name: str, single_selection: bool, items: list, exclusive_items: list = None, clear_item: str = None):
    # Layout
    container = QWidget(browser)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # CheckBox Switch
    switch = QCheckBox(name, browser)
    switch.setChecked(False)
    layout.addWidget(switch)

    # ComboBox
    combo = CheckableComboBox("", browser, single_selection=single_selection)
    if clear_item:
        combo.addClearItem(clear_item)
    if exclusive_items:
        for item in exclusive_items:
            combo.addCheckableItem(item, exclusive=True)
    for item in items:
        combo.addCheckableItem(item)
    layout.addWidget(combo)

    # --- Logic ---
    def on_combo_change(checked_items):
        switch.blockSignals(True)
        switch.setChecked(bool(checked_items))
        switch.blockSignals(False)
        search(browser)

    def on_switch_toggled(checked):
        if checked:
            if not combo.checkedItems():
                combo.select_first()
        else:
            combo.clear()

    combo._on_change = on_combo_change
    switch.toggled.connect(on_switch_toggled)

    return container, combo

def setup_quick_search_in_browser(browser: Browser):
    global cbSuspended, cbDue, cbNew, cbFlag, cbRecent, cbStudied

    # Find existing layout to remove it if it exists
    if browser.form.gridLayout.itemAtPosition(0, 2):
        item = browser.form.gridLayout.itemAtPosition(0, 2)
        if item.layout():
            # This is the grid layout we added before
            while item.layout().count():
                child = item.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            item.layout().deleteLater()

    # Grid layout for all filters
    grid = QGridLayout()
    grid.setSpacing(10)

    # Suspended
    cbSuspended = QCheckBox("Suspended", browser)
    cbSuspended.setChecked(False)
    grid.addWidget(cbSuspended, 0, 0)
    cbSuspended.toggled.connect(partial(search, browser))

    # New
    cbNew = QCheckBox("New", browser)
    cbNew.setChecked(False)
    grid.addWidget(cbNew, 0, 1)
    cbNew.toggled.connect(partial(search, browser))

    # Due
    due_container, cbDue = create_switchable_combobox(
        browser, "Due", True, [f"in {i} days" for i in [1, 3, 7, 14, 30]]
    )
    grid.addWidget(due_container, 0, 2)

    # Studied
    studied_container, cbStudied = create_switchable_combobox(
        browser, "Studied", True, [f"in {i} days" for i in [1, 3, 7, 14, 30]]
    )
    grid.addWidget(studied_container, 0, 3)

    # Flag
    flag_container, cbFlag = create_switchable_combobox(
        browser, "Flag", False,
        items=[f"flag {i}" for i in range(1, 8)],
        exclusive_items=["Any flag"]
    )
    grid.addWidget(flag_container, 0, 4)

    # Recently Added
    recent_container, cbRecent = create_switchable_combobox(
        browser, "Added", True, [f"in {i} days" for i in [1, 3, 7, 14, 30]]
    )
    grid.addWidget(recent_container, 0, 5)

    # Add the grid to the main layout
    browser.form.gridLayout.addLayout(grid, 0, 2, 1, 1) # Span 1 column, as it's a single layout item


def search(browser: Browser):
    browser.onSearchActivated()

def setup_quick_search(context: SearchContext):
    global cbSuspended, cbDue, cbNew, cbFlag, cbRecent, cbStudied

    query = context.search.strip()

    if "nid:" in query or "cid:" in query:
        return

    if cbSuspended is not None and not cbSuspended.isChecked():
        query = f"({query}) -is:suspended"

    if cbDue is not None:
        checked = cbDue.checkedItems()
        if checked:
            due_days_str = checked[0].split(" ")[1]
            due_days = int(due_days_str)
            due_query = " OR ".join(f"prop:due={i}" for i in range(due_days + 1))
            query = f"({query}) ({due_query})"

    if cbStudied is not None:
        checked = cbStudied.checkedItems()
        if checked:
            studied_days_str = checked[0].split(" ")[1]
            studied_days = int(studied_days_str)
            query = f"({query}) rated:{studied_days}"

    if cbNew is not None and cbNew.isChecked():
        query = f"({query}) is:new"

    if cbFlag is not None:
        checked = cbFlag.checkedItems()
        if "Any flag" in checked:
            query = f"({query}) -flag:0"
        else:
            flag_nums = [item.split(" ")[1] for item in checked if item.startswith("flag ")]
            if flag_nums:
                flag_query = " OR ".join(f"flag:{n}" for n in flag_nums)
                query = f"({query}) ({flag_query})"

    if cbRecent is not None:
        checked = cbRecent.checkedItems()
        if checked:
            added_days_str = checked[0].split(" ")[1]
            added_days = int(added_days_str)
            query = f"({query}) added:{added_days}"

    context.search = query

# Register the hook
gui_hooks.browser_will_show.append(setup_quick_search_in_browser)
gui_hooks.browser_will_search.append(setup_quick_search)
