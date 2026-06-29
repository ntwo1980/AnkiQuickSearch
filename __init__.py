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
        self._menu = _MultiSelectMenu(self, single_selection=single_selection, on_change=on_change)
        self.setMenu(self._menu)

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


cbSuspended: QCheckBox = None
cbDue: CheckableComboBox = None
cbStudied: CheckableComboBox = None
cbNew: QCheckBox = None
cbFlag: CheckableComboBox = None
cbRecent: QCheckBox = None

def setup_quick_search_in_browser(browser: Browser):
    global cbSuspended, cbDue, cbNew, cbFlag, cbRecent, cbStudied
    cbSuspended = QCheckBox("Show Suspended", browser)
    cbSuspended.setChecked(False)
    browser.form.gridLayout.addWidget(cbSuspended, 0, 2)
    cbSuspended.toggled.connect(partial(search, browser))

    cbNew = QCheckBox("New", browser)
    cbNew.setChecked(False)
    browser.form.gridLayout.addWidget(cbNew, 0, 3)
    cbNew.toggled.connect(partial(search, browser))

    cbDue = CheckableComboBox("Due", browser, on_change=partial(search, browser), single_selection=True)
    for i in [1, 3, 7, 14, 30]:
        cbDue.addCheckableItem(f"Due in {i} days")
    browser.form.gridLayout.addWidget(cbDue, 0, 4)

    cbStudied = CheckableComboBox("Studied", browser, on_change=partial(search, browser), single_selection=True)
    for i in [1, 3, 7, 14, 30]:
        cbStudied.addCheckableItem(f"Studied in {i} days")
    browser.form.gridLayout.addWidget(cbStudied, 0, 5)

    cbFlag = CheckableComboBox("Flag", browser, on_change=partial(search, browser))
    cbFlag.addClearItem("(no filter)")
    cbFlag.addCheckableItem("Any flag", exclusive=True)
    for label in ["flag 1", "flag 2", "flag 3", "flag 4", "flag 5", "flag 6", "flag 7"]:
        cbFlag.addCheckableItem(label)
    browser.form.gridLayout.addWidget(cbFlag, 0, 6)

    cbRecent = QCheckBox("Recent Added", browser)
    cbRecent.setChecked(False)
    browser.form.gridLayout.addWidget(cbRecent, 0, 7)
    cbRecent.toggled.connect(partial(search, browser))

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
            due_days_str = checked[0].split(" ")[2]
            due_days = int(due_days_str)
            due_query = " OR ".join(f"prop:due={i}" for i in range(due_days + 1))
            query = f"({query}) ({due_query})"

    if cbStudied is not None:
        checked = cbStudied.checkedItems()
        if checked:
            studied_days_str = checked[0].split(" ")[2]
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

    if cbRecent is not None and cbRecent.isChecked():
        config = mw.addonManager.getConfig(__name__)
        days = config.get("recent_added_days", 10) if config else 10
        query = f"({query}) added:{days} is:new"

    context.search = query

# Register the hook
gui_hooks.browser_will_show.append(setup_quick_search_in_browser)
gui_hooks.browser_will_search.append(setup_quick_search)
