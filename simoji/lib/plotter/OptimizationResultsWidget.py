import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
from simoji.lib.OptimizationResultsContainer import OptimizationResultsContainer
from simoji.lib.BasicFunctions import *


class OptimizationResultsWidget(QtWidgets.QWidget):

    def __init__(self, optimization_results_container: OptimizationResultsContainer):
        super().__init__()

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.optimization_results_container = optimization_results_container

        self.basic_optimization_results_widget = None
        self.basic_optimization_results_header_list = []
        self.complete_optimization_results_widget = None
        self.complete_optimization_results_header_list = []

        self.add_optimization_results_widget(optimization_results_container)

    def add_optimization_results_widget(self, optimization_results_container: OptimizationResultsContainer):
        """
        Separate the optimization results in two tables:
        (1) Basic results: final value, final variables_and_expressions, which solver, success
        (2) All results: complete result dict returned by the solver (Note: variables_and_expressions are given as list 'x')
        :param optimization_results_container
        :return:
        """

        # -- create tab widget as container for multiple tables --
        tab_widget = QtWidgets.QTabWidget()

        # -- create basic results table --
        # -> include: final value, final variables_and_expressions, solver name, success, maximize of optimization
        nb_rows = len(optimization_results_container.variable_dict) + 4
        nb_cols = 1

        self.basic_optimization_results_widget = QtWidgets.QTableWidget(nb_rows, nb_cols, self)

        # create headers
        solver_label = 'solver'
        success_label = 'success'
        maximize_label = 'maximize'

        optimization_value_name = optimization_results_container.optimized_value_name
        variable_list = list(optimization_results_container.variable_dict.keys())
        self.basic_optimization_results_header_list = [optimization_value_name] + variable_list + \
                                                      [solver_label, success_label, maximize_label]
        self.basic_optimization_results_widget.setHorizontalHeaderLabels(['value'])
        self.basic_optimization_results_widget.setVerticalHeaderLabels(self.basic_optimization_results_header_list)

        # fill in values
        optimization_value_item = QtWidgets.QTableWidgetItem(str(optimization_results_container.optimized_value))
        self.basic_optimization_results_widget.setItem(
            self.basic_optimization_results_header_list.index(optimization_value_name), 0, optimization_value_item)

        for idx, var_name in enumerate(variable_list):
            var_value = optimization_results_container.variable_dict[var_name]
            var_item = QtWidgets.QTableWidgetItem(str(var_value))
            if var_name in optimization_results_container.variables_out_of_bounds_dict:
                var_item.setBackgroundColor(QtGui.QColor(255, 107, 16, 200))
                var_item.setToolTip(var_name + " out of bounds")
            self.basic_optimization_results_widget.setItem(self.basic_optimization_results_header_list.index(var_name),
                                                           0, var_item)

        solver_item = QtWidgets.QTableWidgetItem(str(optimization_results_container.solver_name))
        self.basic_optimization_results_widget.setItem(
            self.basic_optimization_results_header_list.index(solver_label), 0, solver_item)

        success_item = QtWidgets.QTableWidgetItem(str(optimization_results_container.success))
        self.basic_optimization_results_widget.setItem(
            self.basic_optimization_results_header_list.index(success_label), 0, success_item)

        maximize_item = QtWidgets.QTableWidgetItem(str(optimization_results_container.maximize))
        self.basic_optimization_results_widget.setItem(
            self.basic_optimization_results_header_list.index(maximize_label), 0, maximize_item)

        # -- create all results table --
        optimization_results_dict = optimization_results_container.results_dict

        nb_rows = len(optimization_results_dict)
        nb_cols = 1

        self.complete_optimization_results_widget = QtWidgets.QTableWidget(nb_rows, nb_cols, self)

        # create headers
        self.complete_optimization_results_header_list = [header_str for header_str in optimization_results_dict]
        self.complete_optimization_results_widget.setHorizontalHeaderLabels(['value'])
        self.complete_optimization_results_widget.setVerticalHeaderLabels(self.complete_optimization_results_header_list)

        # fill in values
        for result_key in optimization_results_dict:
            tab_item = QtWidgets.QTableWidgetItem(str(optimization_results_dict[result_key]))
            self.complete_optimization_results_widget.setItem(self.complete_optimization_results_header_list.index(result_key), 0,
                                                              tab_item)

        # make text being displayed even if it is to large to fit in cell (default would show dots in this case)
        self.basic_optimization_results_widget.resizeRowsToContents()
        self.basic_optimization_results_widget.setWordWrap(False)

        self.complete_optimization_results_widget.resizeRowsToContents()
        self.complete_optimization_results_widget.setWordWrap(False)

        # -- add tables to tab_widget --
        tab_widget.addTab(self.basic_optimization_results_widget, 'basic results')
        tab_widget.addTab(self.complete_optimization_results_widget, 'complete solver output')

        self.layout.addWidget(tab_widget)

    def save_data(self, save_path: str):

        base_path, filename = os.path.split(save_path)
        filename += ".json"

        results_json = {}
        for key in self.optimization_results_container.results_dict:
            if is_jsonable(self.optimization_results_container.results_dict[key]):
                results_json.update({key: self.optimization_results_container.results_dict[key]})
            else:
                results_json.update({key: str(self.optimization_results_container.results_dict[key])})

        save_dict = {
            "optimized_value_name": self.optimization_results_container.optimized_value_name,
            "optimized_value": self.optimization_results_container.optimized_value,
            "variable_dict": self.optimization_results_container.variable_dict,
            "solver_name": self.optimization_results_container.solver_name,
            "success": self.optimization_results_container.success,
            "maximize": self.optimization_results_container.maximize,
            "results_dict": results_json
        }

        json_file = open(os.path.join(base_path, filename), 'w', encoding='utf-8')
        json.dump(save_dict, json_file, sort_keys=True, indent=4)
        json_file.close()
