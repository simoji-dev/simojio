import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore
from PySide2.QtCore import Signal

from simoji.lib.gui.CustomTabs import CustomTabs
from simoji.lib.gui.SampleWidget import SampleWidget
from simoji.lib.gui.Dialogs import get_save_file_path

from simoji.lib.Sample import Sample
from simoji.lib.SettingManager import SettingManager
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.ModuleLoader import ModuleLoader
from simoji.lib.BasicFunctions import *
from simoji.lib.enums.ExecutionMode import ExecutionMode

import os
import copy
from typing import List


class SampleTabWidget(QtWidgets.QMainWindow):

    tab_added_sig = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("Tab widget")

        self.tabs = CustomTabs()
        self.tabs.add_tab_clicked_sig.connect(self.add_tab_clicked)
        self.tabs.tabCloseRequested.connect(self.delete_tab_clicked)

        self.current_module = None
        self.widget_list = []
        self.idx_last_clicked_tab = -1      # store index of last  clicked tab to assign context menu actions
        self.default_dir_save_setting = os.path.join("lib", "settings")
        self.is_parameters_tabified = False

        self.setCentralWidget(self.tabs)

        # -- context menu for right clicking tabs --
        self.enable_action = QtWidgets.QAction(QtGui.QIcon(icon_path("enable.svg")), "enable/disable")
        self.tabs.add_context_menu_action(self.enable_action, self.enable_tab_clicked)

        self.rename_action = QtWidgets.QAction(QtGui.QIcon(icon_path("edit.svg")), "rename")
        self.tabs.add_context_menu_action(self.rename_action, self.rename_tab_clicked)

        self.duplicate_action = QtWidgets.QAction(QtGui.QIcon(icon_path("duplicate.svg")), "duplicate")
        self.tabs.add_context_menu_action(self.duplicate_action, self.duplicate_tab_clicked)

        self.save_action = QtWidgets.QAction(QtGui.QIcon(icon_path("save.svg")), "save")
        self.tabs.add_context_menu_action(self.save_action, self.save_tab)

        self.tabs.tabBarClicked.connect(self.store_idx_of_clicked_tab)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def store_idx_of_clicked_tab(self, index):
        self.idx_last_clicked_tab = index

    def add_tab(self, widget: SampleWidget):
        self.tabs.insertTab(self.tabs.count() - 1, widget, widget.get_name())
        self.tabs.setCurrentIndex(self.tabs.count() - 2)
        self.enable_tab(self.tabs.count() - 2, widget.sample.enable)

        self.widget_list.append(widget)

        self.tab_added_sig.emit()

    def add_tab_clicked(self):

        existing_names = [widget.sample.name for widget in self.widget_list]
        new_name, success = self.get_unique_name_dialog(existing_names)

        if success:
            new_sample = Sample(new_name)
            new_sample.set_module(self.current_module)

            new_sample_widget = SampleWidget(new_sample)
            new_sample_widget.load_sample_values(new_sample)
            new_sample_widget.set_module(self.current_module)

            self.add_tab(new_sample_widget)

    def delete_tab_clicked(self, tab_idx: int):
        self.delete_tab(tab_idx, show_dialog=True)

    def delete_tab(self, tab_idx: int, show_dialog=False):
        """Dialog: really delete?"""

        widget = self.tabs.widget(tab_idx)
        sample_name = widget.sample.name

        # -- optionally open dialog: really delete tab? --
        close_bool = True
        if show_dialog:
            buttonReply = QtWidgets.QMessageBox.question(self, 'simoji message',
                                                         "Really delete the tab '" + sample_name + "'?",
                                                         QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                         QtWidgets.QMessageBox.No)
            if buttonReply == QtWidgets.QMessageBox.No:
                close_bool = False

        if close_bool:
            self.tabs.removeTab(tab_idx)
            del self.widget_list[tab_idx]
            widget.deleteLater()

            # if the last tab is closed, open the previous second last tab (to avoid showing the empty +tab)
            if tab_idx == self.tabs.count() - 1:
                self.tabs.setCurrentIndex(tab_idx - 1)

    def set_module(self, module):
        self.current_module = module
        for sample_widget in self.widget_list:
            sample_widget.set_module(module)

    def set_execution_mode(self, execution_mode: ExecutionMode):
        for sample_widget in self.widget_list:
            sample_widget.set_execution_mode(execution_mode)

    def rename_tab_clicked(self):
        existing_names = [widget.sample.name for widget in self.widget_list]
        own_name = self.tabs.widget(self.idx_last_clicked_tab).sample.name
        del existing_names[existing_names.index(own_name)]

        new_name, success = self.get_unique_name_dialog(existing_names, default_entry=own_name)

        if success:
            self.rename_tab(self.idx_last_clicked_tab, new_name)

    def rename_tab(self, idx: int, new_name: str):
        self.tabs.widget(idx).sample.name = new_name
        self.tabs.widget(idx).setWindowTitle(new_name)
        self.tabs.tabBar().setTabText(idx, new_name)

    def duplicate_tab_clicked(self):

        old_sample = self.tabs.widget(self.idx_last_clicked_tab).get_sample()

        existing_names = [widget.sample.name for widget in self.widget_list]
        new_name, success = self.get_unique_name_dialog(existing_names, default_entry=old_sample.name)

        if success:
            new_sample = copy.deepcopy(old_sample)
            new_sample.name = new_name
            new_widget = SampleWidget(new_sample)
            new_widget.set_module(self.current_module)
            self.add_tab(new_widget)

    def save_tab(self):
        sample_name = self.tabs.widget(self.idx_last_clicked_tab).sample.name
        path, success = get_save_file_path(parent=self,
                                           caption="Save setting of sample '" + sample_name + "'",
                                           default_dir=self.default_dir_save_setting,
                                           filter="simoji setting (*.json)")

        if success:
            global_settings = GlobalSettingsContainer()
            global_settings.module_path = ModuleLoader().get_module_path_as_list(self.current_module.to_str())

            sample = self.tabs.widget(self.idx_last_clicked_tab).get_sample()

            SettingManager().write_setting(path, global_settings=global_settings, sample_list=[sample])

    def enable_tab_clicked(self):
        enable = not self.tabs.widget(self.idx_last_clicked_tab).sample.enable
        self.enable_tab(self.idx_last_clicked_tab, enable)

    def enable_tab(self, idx: int, enable: bool):
        if enable:
            text_color = "black"
        else:
            text_color = "lightgrey"

        self.tabs.widget(idx).sample.enable = enable
        self.tabs.tabBar().setTabTextColor(idx, QtGui.QColor(text_color))
        self.tabs.widget(idx).setEnabled(enable)

    def get_samples(self) -> list:
        """Get list of sample objects with current values"""
        return [widget.get_sample() for widget in self.widget_list]

    def get_unique_name_dialog(self, existing_names: list, msg=None, default_entry=""):

        success = False
        if msg is None:
            msg = "New sample name:"
        while True:
            entered_name, okPressed = QtWidgets.QInputDialog.getText(self, "Enter sample name", msg,
                                                                        QtWidgets.QLineEdit.Normal, default_entry)

            if okPressed:
                if entered_name == "":
                    msg = "Sample name cannot be empty string. Enter new name:"
                elif entered_name in existing_names:
                    msg = "Sample name '" + entered_name + "' already exists. Enter new name:"
                else:
                    success = True
                    break
            else:
                break

        return entered_name, success

    def tabify_clicked(self):

        for idx in range(self.tabs.count() - 1):
            widget = self.tabs.widget(idx)
            if self.is_parameters_tabified:
                widget.un_tabify_widgets()
            else:
                widget.tabify_widgets()

        self.is_parameters_tabified = not self.is_parameters_tabified

    def sync_global_free_parameters(self, global_free_parameter_names: List[str]):
        for sample_widget in self.widget_list:
            sample_widget.sync_free_parameters(global_free_parameter_names)

    def enable_solver_settings(self, enable: bool):
        for sample_widget in self.widget_list:
            sample_widget.enable_solver_settings(enable)



