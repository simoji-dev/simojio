import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore
from PySide2.QtCore import Signal

from typing import Callable


class CustomTabs(QtWidgets.QTabWidget):
    """
    Custom tab widget with '+' tab to create new tab.
    """
    add_tab_clicked_sig = Signal()

    def __init__(self):
        super().__init__()

        self.setTabsClosable(True)
        self._build_tabs()

        # set context menu policy
        self.tabBar().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self.on_context_menu)

        # create context menu
        self.popMenu = QtWidgets.QMenu(self)
        self.tab_idx_context_menu = -1

    def _build_tabs(self):
        """ create the "new tab" tab with button '+' """
        self.insertTab(0, QtWidgets.QWidget(), '')
        self.new_btn = QtWidgets.QToolButton()
        self.new_btn.setText("+")  # you could set an icon instead of text
        self.new_btn.setAutoRaise(True)
        self.new_btn.clicked.connect(self.add_tab)
        self.tabBar().setTabButton(0, QtWidgets.QTabBar.RightSide, self.new_btn)

    def add_tab(self):
        self.add_tab_clicked_sig.emit()

    def on_context_menu(self, point):
        self.tab_idx_context_menu = self.tabBar().tabAt(point)      # store index of tab at which the context opened
        self.popMenu.exec_(self.mapToGlobal(point))                 # show context menu

    def add_context_menu_action(self, action: QtWidgets.QAction, connected_method: Callable):
        action.triggered.connect(connected_method)
        self.popMenu.addAction(action)