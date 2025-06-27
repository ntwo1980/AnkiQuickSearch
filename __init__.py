from aqt import gui_hooks
from aqt.qt import QCheckBox
from aqt.browser import Browser
from aqt.browser.table import SearchContext
from functools import partial
from aqt.errors import show_exception
from aqt.qt import *

cbSuspended: QCheckBox = None
cbDue: QCheckBox = None
cbNew: QCheckBox = None

def setup_quick_search_in_browser(browser: Browser):
    global cbSuspended, cbDue, cbNew
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

def search(browser: Browser):
    browser.onSearchActivated()

def setup_quick_search(context: SearchContext):
    global cbSuspended, cbDue, cbNew
    query = context.search.strip()

    if cbSuspended is not None and not cbSuspended.isChecked():
        query = f"({query}) -is:suspended"

    if cbDue is not None and cbDue.isChecked():
        query = f"({query}) is:due"

    if cbNew is not None and cbNew.isChecked():
        query = f"({query}) is:new"

    context.search = query

# Register the hook
gui_hooks.browser_will_show.append(setup_quick_search_in_browser)
gui_hooks.browser_will_search.append(setup_quick_search)
