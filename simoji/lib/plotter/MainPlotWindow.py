# PySide2 stuff
import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore
from PySide2.QtCore import Signal
import matplotlib

from .TabPlotWindow import TabPlotWindow
from simoji.lib.OptimizationResultsContainer import OptimizationResultsContainer
from simoji.lib.VariationResultsContainer import VariationResultsContainer
from simoji.lib.PlotContainer import PlotContainer
from simoji.lib.BasicFunctions import *
from simoji.lib.plotter.SaveDataFileFormats import SaveDataFileFormats
from simoji.lib.MyNode import MyNode
from simoji.lib.module_executor.LeaveNode import LeaveNode
import simoji.lib.BasicFunctions as BasicFunctions

matplotlib.use("Qt5Agg")        # Setting the back-end of the plotting library, use Qt5 since it is used for GUI


class MainPlotWindow(QtWidgets.QMainWindow):
    """
    Window that shows the plots and numerical results created during a module run of simoji. The plots are sorted into
    different tabs to relate them to a specific sample, variation set, and/or evaluation set.
    """

    closed_sig = Signal()
    save_results_sig = Signal()

    def __init__(self):
        super().__init__()

        self.plot_every_steps_list = None
        self.plot_every_steps = 1
        self.setWindowTitle("simoji plot window")

        # -- set simoji icon in window --
        simoji_icon = QtGui.QIcon(icon_path('simoji_logo.svg'))
        self.setWindowIcon(simoji_icon)

        # -- set system tray (icon in task bar) --
        tray = QtWidgets.QSystemTrayIcon(simoji_icon, self)
        tray.show()

        # toolbar
        spacer = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.addStretch(1)
        spacer.setLayout(layout)

        self.saveButton = QtWidgets.QToolButton()
        self.saveButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.saveAction = QtWidgets.QAction()
        self.saveAction.setIcon(QtGui.QIcon(BasicFunctions.icon_path('save_tick.svg')))
        self.saveAction.setText('Save results')
        self.saveAction.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self.saveAction.setToolTip('save results (Ctrl+S)')
        self.saveAction.triggered.connect(self.save_btn_clicked)
        self.saveButton.setDefaultAction(self.saveAction)

        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setObjectName("ToolbarResultsWindow")
        self.toolbar.setMovable(False)

        self.toolbar.addWidget(spacer)
        self.toolbar.addWidget(self.saveButton)

        self.major_tab_widget = QtWidgets.QTabWidget()
        self.major_tab_widget.setObjectName("Plot tab widget")
        self.setCentralWidget(self.major_tab_widget)
        self.sub_tab_widget_list = []  # list containing the sub QTabWidgets (one for each major tab)

        self.addToolBar(QtCore.Qt.BottomToolBarArea, self.toolbar)

        self.root_save_path = None
        self.save_path_list = []
        self.update_plots = True  # False, if execution-mode = variation
        self.is_coupled_evaluation = False  # If True: Evaluation sets as major tabs

        self.evaluation_set_prefix = "evaluation_set_"

        self.sample_names = []

        # store allocation of sample-index and evaluation-set-index to plot-window in a nested dictionary
        # {sample_1: {evaluation_set_1: widget, evaluation_set_2: widget}} -> 1st index sample, 2nd index evaluation set
        self.sample_evaluation_set_widget_dict = {}
        self.plot_window_list = []
        self.nested_tab_name_list = []

        self.leave_nodes = []

        self.tab_window_dict = {}

        self.id_counter = 0
        self.tab_window_dict = dict()   # {id: tab_window}

    def reset(self):

        self.major_tab_widget = QtWidgets.QTabWidget()
        self.major_tab_widget.setObjectName("Plot tab widget")
        self.setCentralWidget(self.major_tab_widget)
        self.sub_tab_widget_list = []       # list containing the sub QTabWidgets (one for each major tab)

        self.addToolBar(QtCore.Qt.BottomToolBarArea, self.toolbar)

        self.root_save_path = None
        self.save_path_list = []
        self.update_plots = True            # False, if execution-mode = variation
        self.is_coupled_evaluation = False  # If True: Evaluation sets as major tabs

        self.sample_names = []              # if the coupled mode is used: additional sample name 'global'

        # store allocation of sample-index and evaluation-set-index to plot-window in a nested dictionary
        # {sample_1: {evaluation_set_1: widget, evaluation_set_2: widget}} -> 1st index sample, 2nd index evaluation set
        self.sample_evaluation_set_widget_dict = {}
        self.plot_window_list = []
        self.nested_tab_name_list = []

        self.leave_nodes = []

        self.tab_window_dict = {}

    def initialize_tabs(self, root: MyNode):

        def create_sub_tabs(node: MyNode, parent_tab_widget: QtWidgets.QTabWidget, save_path: str):
            for sub_node in node.children:
                save_path_sub = os.path.join(save_path, sub_node.name)
                os.makedirs(save_path_sub, exist_ok=True)
                if sub_node.is_leaf:
                    tab_window = TabPlotWindow()
                    self.tab_window_dict.update({self.id_counter: tab_window})
                    sub_node.tab_window_id = self.id_counter
                    self.id_counter += 1
                    sub_node.save_path = save_path_sub
                    self.leave_nodes.append(sub_node)
                    parent_tab_widget.addTab(tab_window, sub_node.name)
                else:
                    tab_widget = QtWidgets.QTabWidget()
                    parent_tab_widget.addTab(tab_widget, sub_node.name)
                    create_sub_tabs(sub_node, tab_widget, save_path_sub)

        create_sub_tabs(root, self.major_tab_widget, self.root_save_path)

    def get_save_path_list(self, parent_path: str, list_to_be_evaluated: list):
        total_save_path_list = []

        for item in list_to_be_evaluated:
            if isinstance(item, tuple):
                total_save_path_list.append(self.get_save_path_list(os.path.join(parent_path, item[0]), item[1]))
            elif isinstance(item, str):
                save_path = os.path.join(parent_path, item)
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                total_save_path_list.append(save_path)
            else:
                raise ValueError("Unknown item (creation of save path list in MainPlotWindow): " + str(item))

        return total_save_path_list

    def process_result(self, result: Union[PlotContainer, OptimizationResultsContainer, VariationResultsContainer],
                       node: LeaveNode):

        tab_window = self.tab_window_dict[node.tab_window_id]

        if isinstance(result, PlotContainer):
            tab_window.plot(result.fig, result.title, result.save)
        elif isinstance(result, OptimizationResultsContainer):
            tab_window.add_optimization_results(result)
        elif isinstance(result, VariationResultsContainer):
            tab_window.update_variation_results(result)
        else:
            raise ValueError("Unknown result type:", result)

    def save_all(self, save_file_format: SaveDataFileFormats):

        for leave_node in self.leave_nodes:
            tab_window = self.tab_window_dict[leave_node.tab_window_id]
            tab_window.save(leave_node.save_path, save_file_format)

    def closeEvent(self, event):
        """Overwrite method of QMainWindow class"""

        # ignore original event (try/except because file menu action doesn't provide event object)
        try:
            event.ignore()
        except:
            pass

        self.closed_sig.emit()

    def save_btn_clicked(self):
        self.save_results_sig.emit()

    def set_save_icon(self, saved: bool):
        if saved:
            self.saveButton.setIcon(QtGui.QIcon(BasicFunctions.icon_path('save_tick_saved.svg')))
        else:
            self.saveButton.setIcon(QtGui.QIcon(BasicFunctions.icon_path('save_tick_unsaved.svg')))
