import shutil
import sys
import tempfile
import webbrowser
import PySide6.QtGui as QtGui
import PySide6.QtCore as QtCore
from typing import List

import simojio.lib.BasicFunctions as BasicFunctions
from simojio.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simojio.lib.ModuleLoader import ModuleLoader
from simojio.lib.Sample import Sample
from simojio.lib.SettingManager import SettingManager
from simojio.lib.abstract_modules import Calculator, Fitter
from simojio.lib.enums.ExecutionMode import ExecutionMode
from simojio.lib.gui.CustomCombo import CustomCombo
from simojio.lib.gui.Dialogs import *
from simojio.lib.gui.GeometryAndPreferencesManager import GeometryAndPreferencesManager
from simojio.lib.gui.SampleTabWidget import SampleTabWidget
from simojio.lib.gui.SampleWidget import SampleWidget
from simojio.lib.gui.SavePathDialog import SavePathDialog
from simojio.lib.gui.global_side_window.SideWidgetGlobalSettings import SideWidgetGlobalSettings
from simojio.lib.module_executor.ModuleExecutor import ModuleExecutor
from simojio.lib.plotter.MainPlotWindow import MainPlotWindow
from simojio.lib.plotter.SaveDataFileFormats import SaveDataFileFormats


class MainWindow(QtWidgets.QMainWindow):
    """Main application window"""

    def __init__(self, setting_path, app: QtWidgets.QApplication):
        super().__init__()

        self.app = app
        self.module_loader = ModuleLoader()

        self.plot_window = MainPlotWindow()
        self.plot_window.closed_sig.connect(self.show_plot_window_clicked)
        self.plot_window.save_results_sig.connect(self.save_btn_clicked)
        self.plot_window.hide()

        self.module_executor = ModuleExecutor(self.plot_window, self.module_loader)

        self.geometry_manager = GeometryAndPreferencesManager()
        self.plot_window_geometry = None

        self._is_global_optimization_settings_enabled = False
        self.execution_mode = None

        self.settings_path = os.path.join("settings")
        self.default_setting_save_path = os.path.join(self.settings_path, "latest_setting.json")

        # -- toolbar --
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setObjectName("simojio toolbar")
        self.module_combo = CustomCombo()
        self.execution_mode_combo = CustomCombo()
        self.global_button = QtWidgets.QPushButton(QtGui.QIcon(BasicFunctions.icon_path('global.svg')), '')
        self.nb_processes_edit = QtWidgets.QLineEdit()

        # -- widgets --
        self.sample_tab_widget = SampleTabWidget()
        self.sample_tab_widget.tab_added_sig.connect(self.sync_global_parameters)
        self.side_widget_global_settings = SideWidgetGlobalSettings()
        self.side_widget_global_settings.update_global_free_parameters_sig.connect(
            self.sync_global_parameters_with_values_send_from_side_widget)
        self.dock_widget_global = QtWidgets.QDockWidget(self)
        self.dock_widget_global.setObjectName("Side dock widget")
        self.save_path_dialog = SavePathDialog()

        # -- actions --
        self.runAction = QtGui.QAction(QtGui.QIcon(BasicFunctions.icon_path('run.svg')), 'Run', self)
        # self.saveButton = QtGui.QAction(QtGui.QIcon(BasicFunctions.icon_path('save_tick.svg')), 'Save results',
        #                                     self)
        self.tabifyAction = QtGui.QAction("tabify parameter widgets")
        self.showPlotWindowAction = QtGui.QAction("show plot window")

        self.init_ui()
        self.load_setting(setting_path)
        self.restore_gui()

        self.temp_dir = None
        self.running = False
        self.start_time = 0.

    def init_ui(self):

        self.setWindowTitle('simojio')

        self.setCentralWidget(self.sample_tab_widget)

        self.init_toolbar()
        self.init_menu_bar()
        self.init_side_widget_global_settings()

        # -- set simojio icon in window --
        simoji_icon = QtGui.QIcon(BasicFunctions.icon_path('simojio_logo.svg'))
        self.setWindowIcon(simoji_icon)

        # -- set system tray (icon in task bar) --
        tray = QtWidgets.QSystemTrayIcon(simoji_icon, self)
        tray.show()

    def init_toolbar(self):

        self.addToolBar(self.toolbar)

        # -- run & stop action --
        self.runAction.setShortcut(QtGui.QKeySequence('F5'))
        self.runAction.setToolTip('run (F5)')
        self.runAction.triggered.connect(self.start_btn_clicked)

        stopAction = QtGui.QAction(QtGui.QIcon(BasicFunctions.icon_path('stop.svg')), 'Stop', self)
        stopAction.setToolTip('stop')
        stopAction.triggered.connect(self.stop_btn_clicked)

        # -- module combo, execution mode combo --
        self.module_combo.activated.connect(self.module_combo_on_activated)
        self.populate_module_combo()

        self.execution_mode_combo.addItems([ExecutionMode.SINGLE, ExecutionMode.VARIATION, ExecutionMode.OPTIMIZATION,
                                            ExecutionMode.COUPLED_OPTIMIZATION])
        self.execution_mode_combo.setToolTip("execution mode")
        self.execution_mode_combo.activated.connect(self.execution_mode_combo_on_activated)

        # -- global button --
        self.global_button.setToolTip("Use global optimization settings")
        self.global_button.clicked.connect(self.global_button_clicked)

        # -- Line edit number of processes --
        nb_processes_label = "processes:"
        nb_processes_label_widget = QtWidgets.QLabel(nb_processes_label)
        positive_int_validator = QtGui.QIntValidator()
        positive_int_validator.setBottom(1)
        self.nb_processes_edit.setValidator(positive_int_validator)
        self.nb_processes_edit.setFixedWidth(30)
        nb_physical_cores = self.module_executor.process_manager.get_nb_physical_cores()
        self.nb_processes_edit.setToolTip(
            "Number of parallel executed processes. Available physical cores: " + str(nb_physical_cores))
        self.nb_processes_edit.setText(str(nb_physical_cores))

        spacer = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.addStretch(1)
        spacer.setLayout(layout)

        # -- fill toolbar --
        self.toolbar.setMovable(False)
        self.toolbar.addAction(self.runAction)
        self.toolbar.addAction(stopAction)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.module_combo)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.execution_mode_combo)
        self.toolbar.addWidget(self.global_button)
        self.toolbar.addWidget(spacer)
        self.toolbar.addWidget(nb_processes_label_widget)
        self.toolbar.addWidget(self.nb_processes_edit)

    def init_menu_bar(self):

        menubar = self.menuBar()

        fileMenu = menubar.addMenu('&File')
        viewMenu = menubar.addMenu('&View')
        helpMenu = menubar.addMenu('&Help')

        # -- File menu --
        NewSettingAct = QtGui.QAction('New setting', self)
        NewSettingAct.triggered.connect(self.new_setting)

        impMenu = QtWidgets.QMenu('Open', self)
        impMenu.setIcon(QtGui.QIcon(BasicFunctions.icon_path('open.svg')))
        impAct = QtGui.QAction('Open setting', self)
        impAct.triggered.connect(self.import_setting)
        impMenu.addAction(impAct)

        loadAct = QtGui.QAction('Add setting', self)
        loadAct.triggered.connect(self.add_setting)
        impMenu.addAction(loadAct)

        expMenu = QtWidgets.QMenu('Save', self)
        expMenu.setIcon(QtGui.QIcon(BasicFunctions.icon_path('save.svg')))
        SaveSettingAct = QtGui.QAction('Save setting', self)
        SaveSettingAct.triggered.connect(self.save_setting_clicked)
        expMenu.addAction(SaveSettingAct)

        exitAction = QtGui.QAction(QtGui.QIcon(BasicFunctions.icon_path('exit.svg')), 'Exit', self)
        exitAction.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        exitAction.triggered.connect(self.closeEvent)

        fileMenu.addAction(NewSettingAct)
        fileMenu.addMenu(impMenu)
        fileMenu.addMenu(expMenu)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)

        # -- View menu --
        self.tabifyAction.triggered.connect(self.tabify_clicked)
        viewMenu.addAction(self.tabifyAction)

        self.showPlotWindowAction.triggered.connect(self.show_plot_window_clicked)
        viewMenu.addAction(self.showPlotWindowAction)

        # -- Help menu --
        wikiAction = QtGui.QAction('Open wiki in webbrowser', self)
        wikiAction.triggered.connect(self.open_wiki)

        helpMenu.addAction(wikiAction)

    def init_side_widget_global_settings(self):

        # -- add the widgets to the window --
        self.dock_widget_global.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        self.dock_widget_global.setWidget(self.side_widget_global_settings)
        self.dock_widget_global.setTitleBarWidget(QtWidgets.QWidget(self.dock_widget_global))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dock_widget_global)

    def restore_gui(self):
        """Restore geometry of main and plot window (try to load from gui.ini) """

        if self.geometry_manager.ini_exists():
            self.restore_geometry()
            self.restore_preferences()
            self.show()
        else:
            self.showMaximized()
            self.plot_window.showMaximized()
            self.show_plot_window(False)
            # self.module_executor.show_plot_window(False)

    def load_setting(self, path: str, delete_previous=True):

        if delete_previous:
            self.new_setting()

        # read setting file
        setting_manager = SettingManager()
        global_settings, sample_list, success = setting_manager.read_setting(path)

        if global_settings.module_path is None:
            global_settings.module_path = self.module_loader.get_module_path_as_list(self.module_combo.currentText())

        # set global settings
        try:
            module = self.module_loader.load_module(global_settings.module_path[-1].rstrip(".py"))
        except:
            module = self.module_loader.load_module(self.module_combo.currentText())

        self.module_combo.setCurrentText(module.to_str())
        self.set_module(self.get_current_module())

        # set sample settings
        for sample in sample_list:
            success = True
            if not delete_previous:
                existing_names = [widget.sample.name for widget in self.sample_tab_widget.widget_list]
                if sample.name in existing_names:
                    msg = "Sample name '" + sample.name + "' already exists. Enter new name:"
                    new_name, success = self.sample_tab_widget.get_unique_name_dialog(existing_names, msg,
                                                                                      default_entry=sample.name)
                    if success:
                        sample.name = new_name
            if success:
                sample_widget = SampleWidget(sample)
                self.sample_tab_widget.add_tab(sample_widget)

        self.execution_mode_combo.setCurrentText(global_settings.execution_mode)

        self._enable_global_optimization_settings(global_settings.use_global_optimization_settings)

        self.side_widget_global_settings.set_global_variables_container(global_settings.global_variables)
        self.side_widget_global_settings.set_global_expressions_container(global_settings.global_expressions)
        self.side_widget_global_settings.set_optimization_settings_container(global_settings.optimization_settings)

        self.side_widget_global_settings.sync_free_parameters()  # needs to be done after the samples are created
        self.execution_mode_combo_on_activated()
        self.sample_tab_widget.set_module(module)

    def save_setting(self, save_path: str):
        global_settings, sample_list = self.get_current_setting()
        SettingManager().write_setting(save_path, global_settings, sample_list)

    def save_setting_clicked(self):
        save_path, success = get_save_file_path(self, caption="Select save path", default_dir=self.settings_path,
                                                filter="simojio settings (*.json)")
        if success:
            self.save_setting(save_path)

    def new_setting(self):
        for idx in range(self.sample_tab_widget.tabs.count() - 1):
            self.sample_tab_widget.delete_tab(tab_idx=0, show_dialog=False)

    def import_setting(self):
        fname = self.get_setting_path_dialog()
        if fname != "":
            self.load_setting(fname, delete_previous=True)

    def add_setting(self):
        fname = self.get_setting_path_dialog()
        if fname != "":
            self.load_setting(fname, delete_previous=False)

    def get_setting_path_dialog(self) -> str:

        fname, type = QtWidgets.QFileDialog.getOpenFileName(self, "Open settings file", self.settings_path,
                                                            "simojio settings (*.json)")
        return fname

    def start_btn_clicked(self):

        self.runAction.setEnabled(False)
        self.temp_dir = tempfile.TemporaryDirectory()   # use temporary directory as default save path (for custom save)

        self.set_module(self.get_current_module())
        self.module_combo_on_activated()    # set the current module

        global_settings, sample_list = self.get_current_setting()
        nb_parallel_processes = int(self.nb_processes_edit.text())
        self.module_executor = ModuleExecutor(self.plot_window, self.module_loader, nb_parallel_processes)
        self.module_executor.configure(global_settings, sample_list, self.temp_dir.name)
        self.module_executor.execution_stopped_sig.connect(self.module_execution_stopped)
        self.module_executor.plot_window_visibility_changed_sig.connect(self.show_plot_window)

        self.module_executor.run()

        self.plot_window.set_save_icon(saved=False)
        self.running = True

    def stop_btn_clicked(self):
        self.module_executor.terminate_execution()
        self.running = False

    def save_btn_clicked(self):

        save_path, save_file_format, zip_results, ok = self.save_dialog()

        if ok:
            global_settings, sample_list = self.get_current_setting()
            self.save_results(global_settings, sample_list, save_path, save_file_format, zip_results, self.app)
            self.plot_window.set_save_icon(saved=True)

    def save_results(self, global_settings: GlobalSettingsContainer, sample_list: List[Sample],
                     save_path: str, save_file_format: SaveDataFileFormats, zip_results: bool,
                     app: QtWidgets.QApplication):

        self.plot_window.save_file_format = save_file_format
        self.plot_window.save_all(save_file_format)

        if os.path.exists(save_path):   # dst must not exist when doing shutil.copytree
            shutil.rmtree(save_path)
        shutil.copytree(src=self.temp_dir.name, dst=save_path)

        setting_path = os.path.join(save_path, "setting.json")

        setting_manager = SettingManager()
        setting_manager.write_setting(setting_path, global_settings=global_settings, sample_list=sample_list)

        # write readme
        self._write_readme(save_path, app, global_settings)

        if zip_results:
            shutil.make_archive(save_path, 'zip', save_path)
            shutil.rmtree(save_path)

    def _write_readme(self, save_path: str, app: QtWidgets.QApplication, global_settings: GlobalSettingsContainer):
        """Write README file with basic information about the origin of the results and the folder content."""

        readme_file = open(os.path.join(save_path, "README.txt"), 'w')
        title_str = "# Title:\tREADME for folder '" + os.path.split(save_path)[1] + "'\n"
        date_str = "# Created:\t" + BasicFunctions.get_time_stamp() + "\n"
        author_str = "# Author:\tsimoji_v" + app.applicationVersion() + "\n"

        module_name = global_settings.module_path[-1]
        execution_mode = global_settings.execution_mode
        description_str = "# Description:\tContains results of simojio module '" + module_name \
                          + "' for execution mode '" + execution_mode + "'\n"

        readme_file.write(title_str)
        readme_file.write(date_str)
        readme_file.write(author_str)
        readme_file.write(description_str)
        readme_file.close()

    def save_dialog(self) -> (str, str, bool, bool):
        """
        Execute save path dialog.
        :return: save_path, save_file_format, ok-bool
        """

        self.save_path_dialog.set_module_name(self.module_combo.currentText())
        self.save_path_dialog.set_execution_mode(self.execution_mode_combo.currentText())

        save_path = None
        save_file_format = None
        zip_results = True
        ok = False

        if self.save_path_dialog.exec():  # ok clicked
            save_path = self.save_path_dialog.get_current_save_path()
            save_file_format = self.save_path_dialog.get_file_format()
            zip_results = self.save_path_dialog.get_zip_results()

            if os.path.exists(save_path):
                ok = warning(self, "Save path already exists. Overwrite?")
                if ok:
                    shutil.rmtree(save_path)
            else:
                ok = True

        return save_path, save_file_format, zip_results, ok

    def module_execution_stopped(self):
        self.runAction.setEnabled(True)
        self.running = False

    def closeEvent(self, event):
        """Overwrite method of QMainWindow class"""

        reply = QtWidgets.QMessageBox.question(self, 'Really quit?',
                                               "Are you sure to quit?", QtWidgets.QMessageBox.Yes |
                                               QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            # -- save gui and settings --
            self.save_gui_geometry()
            self.store_preferences()
            self.save_setting(self.default_setting_save_path)

            # -- quit the app --
            self.module_executor.terminate_execution()
            
            # Accept the close event to allow the window to close
            event.accept()
            self.app.quit()
        else:
            # Ignore the close event to prevent the window from closing
            event.ignore()

    def save_gui_geometry(self):
        self.geometry_manager.save_geometry(self, self.plot_window)

    def store_preferences(self):
        self.geometry_manager.store_save_path_preferences(self.save_path_dialog.get_preferences())

    def restore_geometry(self):
        self.geometry_manager.restore_geometry(self, self.plot_window)
        self.set_plot_window_geometry()     # store geometry

    def set_plot_window_geometry(self):
        self.plot_window_geometry = self.plot_window.geometry()

    def restore_preferences(self):
        self.save_path_dialog.set_preferences(self.geometry_manager.get_save_path_preferences())

    def get_current_setting(self) -> (GlobalSettingsContainer, list):

        global_settings = GlobalSettingsContainer()
        global_settings.module_path = self.module_loader.get_module_path_as_list(self.module_combo.currentText())
        global_settings.execution_mode = ExecutionMode(self.execution_mode_combo.currentText())
        global_settings.use_global_optimization_settings = self._is_global_optimization_settings_enabled

        global_settings.set_variables_parameter_container(
            self.side_widget_global_settings.get_global_variables_container())
        global_settings.set_expressions_parameter_container(
            self.side_widget_global_settings.get_global_expressions_container())

        global_settings.set_optimization_settings_container(
            self.side_widget_global_settings.get_optimization_settings_container()
        )

        sample_list = self.sample_tab_widget.get_samples()

        return global_settings, sample_list

    def populate_module_combo(self):
        """Add all modules as found by the InputReader to the module combo"""
        available_modules = self.module_loader.get_available_modules()
        self.module_combo.addItems(sorted(available_modules, key=lambda v: v.upper()))

    def module_combo_on_activated(self):
        self.set_module(self.get_current_module())

    def set_module(self, module):

        # if module has no value to be optimized, disable optimization-modes in execution mode combo
        optimization_indices = [self.execution_mode_combo.findText(ExecutionMode(item)) for item in
                                [ExecutionMode.OPTIMIZATION, ExecutionMode.COUPLED_OPTIMIZATION]]

        enable_optimization_mode = isinstance(module, Calculator) or isinstance(module, Fitter)

        for optimization_idx in optimization_indices:
            self.execution_mode_combo.model().item(optimization_idx).setEnabled(enable_optimization_mode)

        if not enable_optimization_mode:
            if self.execution_mode_combo.currentIndex() in optimization_indices:
                variation_idx = self.execution_mode_combo.findText(ExecutionMode(ExecutionMode.VARIATION))
                self.execution_mode_combo.setCurrentIndex(variation_idx)
                self.execution_mode_combo_on_activated()

        self.sample_tab_widget.set_module(module)
        self.side_widget_global_settings.set_module(module)

    def execution_mode_combo_on_activated(self):
        self.execution_mode = ExecutionMode(self.execution_mode_combo.currentText())
        self.sample_tab_widget.set_execution_mode(self.execution_mode)
        self.side_widget_global_settings.set_execution_mode(self.execution_mode)
        if self.execution_mode is ExecutionMode.COUPLED_OPTIMIZATION:
            self._enable_global_optimization_settings(True)

    def get_current_module(self):
        return self.module_loader.load_module(self.module_combo.currentText())

    def global_button_clicked(self):

        if self.execution_mode is ExecutionMode.COUPLED_OPTIMIZATION:
            warning(self, "Global optimization settings cannot be disabled if coupled mode is enabled.")
        else:
            self._is_global_optimization_settings_enabled = not self._is_global_optimization_settings_enabled
            self._enable_global_optimization_settings(self._is_global_optimization_settings_enabled)

    def tabify_clicked(self):
        if self.sample_tab_widget.is_parameters_tabified:
            self.tabifyAction.setIcon(QtGui.QIcon())
        else:
            self.tabifyAction.setIcon(QtGui.QIcon(BasicFunctions.icon_path("tick_mark.svg")))
        self.sample_tab_widget.tabify_clicked()

    def show_plot_window(self, is_visible: bool):
        if is_visible:
            self.plot_window.show()
            self.showPlotWindowAction.setIcon(QtGui.QIcon(BasicFunctions.icon_path("tick_mark.svg")))
        else:
            self.plot_window.hide()
            self.showPlotWindowAction.setIcon(QtGui.QIcon())

    def show_plot_window_clicked(self):
        show = not self.plot_window.isVisible() #self.module_executor.is_plot_window_visible()
        self.show_plot_window(show)

    @staticmethod
    def open_wiki():
        webbrowser.open_new_tab("https://git.iap.phy.tu-dresden.de/simoji-dev/simoji/-/wikis/simoji")

    def _enable_global_optimization_settings(self, enable: bool):
        self._is_global_optimization_settings_enabled = enable
        self.side_widget_global_settings.enable_global_optimization_settings(enable)
        if self._is_global_optimization_settings_enabled:
            self.global_button.setStyleSheet("QPushButton {background-color: lightgreen;}")
        else:
            self.global_button.setStyleSheet("QPushButton {background-color: None;}")

        self.sample_tab_widget.enable_solver_settings(not enable)

    def sync_global_parameters_with_values_send_from_side_widget(self, global_parameters_names: List[str]):
        self.sample_tab_widget.sync_global_free_parameters(global_parameters_names)

    def sync_global_parameters(self):
        self.side_widget_global_settings.sync_free_parameters()




