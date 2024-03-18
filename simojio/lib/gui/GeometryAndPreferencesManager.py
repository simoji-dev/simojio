import PySide6.QtWidgets as QtWidgets
import PySide6.QtCore as QtCore

import os


class GeometryAndPreferencesManager:

    def __init__(self):

        self.ini_path = os.path.join("gui.ini")
        self.settings = QtCore.QSettings(self.ini_path, QtCore.QSettings.IniFormat)

        self.main_window_category = "MainWindow"
        self.sample_window_category = "SampleWindow"
        self.side_window_category = "SideWindow"
        self.plot_window_category = "PlotWindow"
        self.geometry_key = "geometry"
        self.state_key = "state"
        self.tab_prefix = "tab"

        self.save_path_category = "SavePathPreferences"

    def ini_exists(self) -> bool:
        return os.path.isfile(self.ini_path)

    def _get_value(self, category: str, key: str, default_value):
        value = self.settings.value(category + "/" + key, default_value)
        if str(value).lower() == "true":
            value = True
        elif str(value).lower() == "false":
            value = False
        return value

    def save_geometry(self, main_window: QtWidgets.QMainWindow, plot_window: QtWidgets.QMainWindow):
        """
        Save GUI geometry and state. Dock widgets are identified via their objectName(). Hence, we need to set a unique
        name before saving. All sample tabs, plot window, and side window (global settings) have to be saved separately.
        """

        # save sample tabs
        tab_widget = main_window.sample_tab_widget.tabs
        for idx in range(tab_widget.count()):
            tab_name = self.tab_prefix + str(idx)
            tab_main_window = tab_widget.widget(idx)

            dock_list = tab_widget.widget(idx).findChildren(QtWidgets.QDockWidget)
            for dock_widget in dock_list:
                dock_widget.setObjectName(tab_name + dock_widget.windowTitle())     # set unique name

            if isinstance(tab_main_window, QtWidgets.QMainWindow):
                self.settings.setValue(tab_name + "/" + self.geometry_key, tab_main_window.saveGeometry())
                self.settings.setValue(tab_name + "/" + self.state_key, tab_main_window.saveState())

        # save main window
        self.settings.setValue(self.main_window_category + "/" + self.geometry_key, main_window.saveGeometry())
        self.settings.setValue(self.main_window_category + "/" + self.state_key, main_window.saveState())
        self.settings.setValue(self.main_window_category + "/" + self.tab_prefix, tab_widget.currentIndex())

        # save side window
        side_window = main_window.side_widget_global_settings
        for dock_widget in side_window.findChildren(QtWidgets.QDockWidget):
            dock_widget.setObjectName("side" + dock_widget.windowTitle())
        self.settings.setValue(self.side_window_category + "/" + self.geometry_key, side_window.saveGeometry())
        self.settings.setValue(self.side_window_category + "/" + self.state_key, side_window.saveState())

        # save plot window
        self.settings.setValue(self.plot_window_category + "/" + self.geometry_key, plot_window.saveGeometry())
        self.settings.setValue(self.plot_window_category + "/" + self.state_key, plot_window.saveState())

    def restore_geometry(self, main_window: QtWidgets.QMainWindow, plot_window: QtWidgets.QMainWindow):

        try:
            tab_widget = main_window.sample_tab_widget.tabs
            for idx in range(tab_widget.count()):
                tab_name = self.tab_prefix + str(idx)
                dock_list = tab_widget.widget(idx).findChildren(QtWidgets.QDockWidget)
                for dock_widget in dock_list:
                    dock_widget.setObjectName(tab_name + dock_widget.windowTitle())

            main_window.restoreGeometry(self.settings.value(self.main_window_category + "/" + self.geometry_key))
            main_window.restoreState(self.settings.value(self.main_window_category + "/" + self.state_key))

            for idx in range(tab_widget.count()):
                tab_name = self.tab_prefix + str(idx)
                tab_main_window = tab_widget.widget(idx)
                if isinstance(tab_main_window, QtWidgets.QMainWindow):
                    tab_main_window.restoreGeometry(self.settings.value(tab_name + "/" + self.geometry_key))
                    tab_main_window.restoreState(self.settings.value(tab_name + "/" + self.state_key))

            try:
                tab_idx = int(self.settings.value(self.main_window_category + "/" + self.tab_prefix, 0))
                if tab_idx == tab_widget.count() - 1:
                    tab_idx -= 1
                tab_widget.setCurrentIndex(tab_idx)
            except:
                tab_widget.setCurrentIndex(0)

            side_window = main_window.side_widget_global_settings
            for dock_widget in side_window.findChildren(QtWidgets.QDockWidget):
                dock_widget.setObjectName("side" + dock_widget.windowTitle())
            side_window.restoreGeometry(self.settings.value(self.side_window_category + "/" + self.geometry_key))
            side_window.restoreState(self.settings.value(self.side_window_category + "/" + self.state_key))

            plot_window.restoreGeometry(self.settings.value(self.plot_window_category + "/" + self.geometry_key))
            plot_window.restoreState(self.settings.value(self.plot_window_category + "/" + self.state_key))
        except:
            pass

    def store_save_path_preferences(self, preferences_dict: dict):
        for key in preferences_dict:
            self._set_value(self.save_path_category, key, preferences_dict[key])

    def get_save_path_preferences(self) -> dict:
        return self._get_category_items_as_dict(self.save_path_category)

    def _get_category_items_as_dict(self, category: str) -> dict:
        self.settings.beginGroup(category)
        keys = self.settings.allKeys()
        self.settings.endGroup()
        return {key: self._get_value(category, key, None) for key in keys}

    def _set_value(self, category: str, key: str, value):
        self.settings.setValue(category + "/" + key, value)