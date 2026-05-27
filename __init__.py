from aqt import gui_hooks, mw
from aqt.qt import QCheckBox, QComboBox
from aqt.browser import Browser
from aqt.browser.table import SearchContext
from functools import partial
from aqt.errors import show_exception
from aqt.qt import *


class _MultiSelectMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._exclusive_action = None
        self._clear_action = None

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        if action and action.isCheckable():
            if action is self._clear_action:
                for a in self.actions():
                    a.setChecked(False)
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
        else:
            super().mouseReleaseEvent(event)


class CheckableComboBox(QPushButton):
    def __init__(self, placeholder, parent=None, on_change=None):
        super().__init__(placeholder, parent)
        self._menu = _MultiSelectMenu(self)
        self.setMenu(self._menu)
        if on_change:
            self._menu.aboutToHide.connect(on_change)

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
cbDue: QCheckBox = None
cbNew: QCheckBox = None
cbFlag: CheckableComboBox = None
cbRecent: QCheckBox = None

def setup_quick_search_in_browser(browser: Browser):
    global cbSuspended, cbDue, cbNew, cbFlag, cbRecent
    cbSuspended = QCheckBox("Show Suspended", browser)
    cbSuspended.setChecked(False)
    browser.form.gridLayout.addWidget(cbSuspended, 0, 2)
    cbSuspended.toggled.connect(partial(search, browser))

    cbDue = QCheckBox("Due", browser)
    cbDue.setChecked(False)
    browser.form.gridLayout.addWidget(cbDue, 0, 3)
    cbDue.toggled.connect(partial(search, browser))

    cbNew = QCheckBox("New", browser)
    cbNew.setChecked(False)
    browser.form.gridLayout.addWidget(cbNew, 0, 4)
    cbNew.toggled.connect(partial(search, browser))

    cbFlag = CheckableComboBox("Flag", browser, on_change=partial(search, browser))
    cbFlag.addClearItem("(no filter)")
    cbFlag.addCheckableItem("Any flag", exclusive=True)
    for label in ["flag 1", "flag 2", "flag 3", "flag 4", "flag 5", "flag 6", "flag 7"]:
        cbFlag.addCheckableItem(label)
    browser.form.gridLayout.addWidget(cbFlag, 0, 5)

    cbRecent = QCheckBox("Recent Added", browser)
    cbRecent.setChecked(False)
    browser.form.gridLayout.addWidget(cbRecent, 0, 6)
    cbRecent.toggled.connect(partial(search, browser))

def search(browser: Browser):
    browser.onSearchActivated()

def setup_quick_search(context: SearchContext):
    global cbSuspended, cbDue, cbNew, cbFlag, cbRecent

    query = context.search.strip()

    if "nid:" in query or "cid:" in query:
        return

    if cbSuspended is not None and not cbSuspended.isChecked():
        query = f"({query}) -is:suspended"

    if cbDue is not None and cbDue.isChecked():
        query = f"({query}) is:due"

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
