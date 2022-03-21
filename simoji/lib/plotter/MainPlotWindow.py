# PySide2 stuff
import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
from PySide2.QtCore import Signal
# from anytree import AnyNode

# Pyplot stuff
import matplotlib
matplotlib.use("Qt5Agg")

import os
from typing import List

from .TabPlotWindow import TabPlotWindow
from simoji.lib.enums.ExecutionMode import ExecutionMode
from simoji.lib.OptimizationResultsContainer import OptimizationResultsContainer
from simoji.lib.VariationResultsContainer import VariationResultsContainer
from simoji.lib.PlotContainer import PlotContainer
from simoji.lib.BasicFunctions import *
from simoji.lib.abstract_modules import *
from simoji.lib.BasicFunctions import flatten
from simoji.lib.plotter.SaveDataFileFormats import SaveDataFileFormats
from simoji.lib.MyNode import MyNode


class MainPlotWindow(QtWidgets.QMainWindow):
    """
    Window that shows the plots and numerical results created during a module run of simoji. The plots are sorted into
    different tabs to related them to a specific sample and (if given) data set.

    Depending on the module type and whether the "coupled" mode is selected there are 3 different ways how the tabs are
    organized. There are at maximum two tab hierarchy steps which are called "Major tabs" and "Sub tabs" in the following:

    1) Module type "Simulator":
    - Major tabs: Samples
    - Sub tabs: No (no data sets defined for Simulators by definition)

    2) Module types "DataSetReader", "Fitter" and de-coupled evaluation:
    - Major tabs: Samples
    - Sub tabs: Data sets

    3) Module types "DataSetReader", "Fitter" and coupled evaluation:
    - Major tabs: Data sets
    - Sub tabs: Samples

    Furthermore, it depends on the execution mode how the single plots are handled if the module is repeatedly executed:

    a) Variation mode:
        - Plots of each step are shown separately (variation step in plot title)
        (- Optional: Combine data of variation steps in one plot (works only for 1d and difficult to label))

    b) Optimization mode: Show only plots of current step.

    """

    closed_sig = Signal()  # emitted when window closed

    def __init__(self):
        super().__init__()

        self.plot_every_steps_list = None
        self.plot_every_steps = 1
        self.setWindowTitle("simoji results window")

        # -- set simoji icon in window --
        simoji_icon = QtGui.QIcon(icon_path('simoji_logo.svg'))
        self.setWindowIcon(simoji_icon)

        # -- set system tray (icon in task bar) --
        tray = QtWidgets.QSystemTrayIcon(simoji_icon, self)
        tray.show()

        self.reset()

        self.input_tree = None

    def reset(self):

        self.major_tab_widget = QtWidgets.QTabWidget()
        self.major_tab_widget.setObjectName("Plot tab widget")
        self.setCentralWidget(self.major_tab_widget)
        self.sub_tab_widget_list = []       # list containing the sub QTabWidgets (one for each major tab)

        self.root_save_path = None
        self.save_path_list = []
        self.update_plots = True            # False, if execution-mode = variation
        self.is_simulator_module = True     # If True: No sub-tabs for data sets
        self.is_coupled_evaluation = False  # If True: Data sets as major tabs (if not _is_simulator_module)
        self.is_simulator_module = True

        self.dataset_prefix = "data_set_"

        self.sample_names = []              # if the coupled mode is used: additional sample name 'global'

        # store allocation of sample-index and data-set-index to plot-window in a nested dictionary
        # {sample_1: {dataset_1: widget, dataset_2: widget}}    -> 1st index sampled, 2nd index data set
        self.sample_dataset_widget_dict = {}
        self.plot_window_list = []
        self.nested_tab_name_list = []

        self.leave_nodes = []

    def configure(self, save_path: str, plot_every_steps_list: List[int]):
        self.root_save_path = save_path
        self.plot_every_steps_list = plot_every_steps_list

    def initialize_tabs(self, root: MyNode):

        def create_sub_tabs(node: MyNode, parent_tab_widget: QtWidgets.QTabWidget, save_path: str):
            for sub_node in node.children:
                save_path_sub = os.path.join(save_path, sub_node.name)
                os.makedirs(save_path_sub, exist_ok=True)
                if sub_node.is_leaf:
                    tab_window = TabPlotWindow()
                    sub_node.tab_window = tab_window
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
                       node: MyNode):

        if isinstance(result, PlotContainer):
            node.tab_window.plot(result.fig, result.title, result.save)
        elif isinstance(result, OptimizationResultsContainer):
            node.tab_window.add_optimization_results(result)
        elif isinstance(result, VariationResultsContainer):
            node.tab_window.update_variation_results(result)
        else:
            raise ValueError("Unknown result type:", result)

    def save_all(self, save_file_format: SaveDataFileFormats):

        for leave_node in self.leave_nodes:
            leave_node.tab_window.save(leave_node.save_path, save_file_format)

    def closeEvent(self, event):
        """Overwrite method of QMainWindow class"""

        # ignore original event (try/except because file menu action doesn't provide event object)
        try:
            event.ignore()
        except:
            pass

        self.closed_sig.emit()
