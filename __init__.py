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
        self._placeholder = placeholder
        self._on_change = on_change
        self._menu = _MultiSelectMenu(self, single_selection=single_selection, on_change=self._internal_on_change)
        self.setMenu(self._menu)
        self._update_button_text()

    def _display_text(self, raw_text: str) -> str:
        # Keep a small left inset even on styles where QPushButton padding is ignored.
        return f"  {raw_text}" if raw_text else raw_text

    def _update_button_text(self):
        items = self.checkedItems()
        if not items:
            self.setText(self._display_text(self._placeholder))
        elif len(items) == 1:
            self.setText(self._display_text(items[0]))
        else:
            self.setText(self._display_text(f"{len(items)} selected"))

    def _internal_on_change(self):
        self._update_button_text()
        if self._on_change:
            self._on_change(self.checkedItems())

    def lock_width_to_contents(self):
        metrics = self.fontMetrics()
        candidates = [self._display_text(self._placeholder), self._display_text("99 selected")]
        candidates.extend(self._display_text(action.text()) for action in self._menu.actions())
        text_width = max(metrics.horizontalAdvance(text) for text in candidates if text)
        # Extra room for left/right padding and the menu indicator arrow.
        self.setFixedWidth(max(text_width + 55, 100))

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
cbIntroduced: CheckableComboBox = None
cbAgain: CheckableComboBox = None

# --- Helper function to create a switchable combo box ---
def create_switchable_combobox(browser: Browser, name: str, single_selection: bool, items: list, exclusive_items: list = None, clear_item: str = None, default_item: str = None):
    # Layout
    container = QWidget(browser)
    container.setObjectName("aqsFilterItem")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    # CheckBox Switch
    switch = QCheckBox(name, browser)
    switch.setObjectName("aqsFilterSwitch")
    switch.setChecked(False)
    switch.setCursor(Qt.CursorShape.PointingHandCursor)
    switch.setFixedHeight(22)
    switch.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    layout.addWidget(switch)

    # ComboBox
    combo = CheckableComboBox("", browser, single_selection=single_selection)
    combo.setObjectName("aqsFilterCombo")
    combo.setCursor(Qt.CursorShape.PointingHandCursor)
    combo.setFixedHeight(22)
    combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    if clear_item:
        combo.addClearItem(clear_item)
    if exclusive_items:
        for item in exclusive_items:
            combo.addCheckableItem(item, exclusive=True)
    for item in items:
        combo.addCheckableItem(item)
    combo.lock_width_to_contents()
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
                if default_item:
                    combo.setChecked([default_item])
                else:
                    combo.select_first()
        else:
            combo.clear()

    combo._on_change = on_combo_change
    switch.toggled.connect(on_switch_toggled)
    return container, combo

def setup_quick_search_in_browser(browser: Browser):
    global cbSuspended, cbDue, cbNew, cbFlag, cbRecent, cbStudied, cbIntroduced, cbAgain

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

    # Use a single horizontal row so spacing between each condition is uniform.
    filter_row_host = QWidget(browser)
    filter_row_host.setObjectName("aqsFilterRow")
    filter_row = QHBoxLayout(filter_row_host)
    filter_row.setSpacing(6)
    filter_row.setContentsMargins(8, 4, 8, 4)

    # Scoped style for the second-row quick filter controls.
    filter_row_host.setStyleSheet("""
        QWidget#aqsFilterRow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f7f9fc, stop:1 #eef2f7);
            border: 1px solid #d9e1ec;
            border-radius: 8px;
        }
        QWidget#aqsFilterRow QCheckBox#aqsFilterSwitch,
        QWidget#aqsFilterRow QCheckBox#aqsFilterSimple {
            spacing: 4px;
            padding: 0 2px;
            color: #2e3a4a;
            font-weight: 500;
        }
        QWidget#aqsFilterRow QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #9eacbf;
            border-radius: 4px;
            background: #ffffff;
        }
        QWidget#aqsFilterRow QCheckBox::indicator:checked {
            border: 1px solid #2d6cdf;
            background: #2d6cdf;
        }
        QWidget#aqsFilterRow QPushButton#aqsFilterCombo {
            padding: 0 8px 0 12px;
            border: 1px solid #b7c5d8;
            border-radius: 6px;
            background: #ffffff;
            color: #233145;
            text-align: left;
        }
        QWidget#aqsFilterRow QPushButton#aqsFilterCombo:hover {
            border: 1px solid #7f95b3;
            background: #f6f9ff;
        }
        QWidget#aqsFilterRow QPushButton#aqsFilterCombo:pressed {
            background: #edf3ff;
        }
        QWidget#aqsFilterRow QPushButton#aqsFilterCombo::menu-indicator {
            width: 12px;
            subcontrol-origin: padding;
            subcontrol-position: right center;
        }
    """)

    # Due
    due_container, cbDue = create_switchable_combobox(
        browser, "Due", True,
        [f"in {i} days" for i in [0, 1, 3, 7, 14, 30]],
        default_item="in 0 days"
    )
    filter_row.addWidget(due_container)

    # New
    cbNew = QCheckBox("New", browser)
    cbNew.setObjectName("aqsFilterSimple")
    cbNew.setCursor(Qt.CursorShape.PointingHandCursor)
    cbNew.setFixedHeight(22)
    cbNew.setChecked(False)
    filter_row.addWidget(cbNew)
    cbNew.toggled.connect(partial(search, browser))

    # Studied
    studied_container, cbStudied = create_switchable_combobox(
        browser, "Studied", True,
        [f"in {i} days" for i in [1, 3, 7, 14, 30]],
        default_item="in 1 days"
    )
    filter_row.addWidget(studied_container)

    # Recently Added
    recent_container, cbRecent = create_switchable_combobox(
        browser, "Added", True,
        [f"in {i} days" for i in [1, 3, 7, 14, 30]],
        default_item="in 1 days"
    )
    filter_row.addWidget(recent_container)

    # Introduced
    introduced_container, cbIntroduced = create_switchable_combobox(
        browser, "Introduced", True,
        [f"in {i} days" for i in [1, 3, 7, 14, 30]],
        default_item="in 1 days"
    )
    filter_row.addWidget(introduced_container)

    # Again
    again_container, cbAgain = create_switchable_combobox(
        browser, "Again", True,
        [f"in {i} days" for i in [1, 3, 7, 14, 30]],
        default_item="in 1 days"
    )
    filter_row.addWidget(again_container)

    # Flag
    flag_container, cbFlag = create_switchable_combobox(
        browser, "Flag", False,
        items=[f"flag {i}" for i in range(1, 8)],
        exclusive_items=["Any flag"]
    )
    filter_row.addWidget(flag_container)

    # Suspended
    cbSuspended = QCheckBox("Suspended", browser)
    cbSuspended.setObjectName("aqsFilterSimple")
    cbSuspended.setCursor(Qt.CursorShape.PointingHandCursor)
    cbSuspended.setFixedHeight(22)
    cbSuspended.setChecked(False)
    filter_row.addWidget(cbSuspended)
    cbSuspended.toggled.connect(partial(search, browser))

    filter_row.addStretch(1)

    browser.form.gridLayout.addWidget(filter_row_host, 1, 1, 1, 8)
    #browser.form.gridLayout.setColumnMinimumWidth(0, 150)

def search(browser: Browser):
    browser.onSearchActivated()

def setup_quick_search(context: SearchContext):
    global cbSuspended, cbDue, cbNew, cbFlag, cbRecent, cbStudied, cbIntroduced, cbAgain
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

    if cbIntroduced is not None:
        checked = cbIntroduced.checkedItems()
        if checked:
            introduced_days_str = checked[0].split(" ")[1]
            introduced_days = int(introduced_days_str)
            query = f"({query}) introduced:{introduced_days}"

    if cbAgain is not None:
        checked = cbAgain.checkedItems()
        if checked:
            again_days_str = checked[0].split(" ")[1]
            again_days = int(again_days_str)
            query = f"({query}) rated:{again_days}:1"

    context.search = query

# Register the hook
gui_hooks.browser_will_show.append(setup_quick_search_in_browser)
gui_hooks.browser_will_search.append(setup_quick_search)
