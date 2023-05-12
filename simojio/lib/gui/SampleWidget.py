import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore

from simojio.lib.gui.evaluation_sets.EvaluationSetScrollWidget import EvaluationSetScrollWidget
from simojio.lib.gui.parameter_widgets.FloatParWidget import FloatParWidget
from simojio.lib.gui.layers.LayerStackScrollWidget import LayerStackScrollWidget
from simojio.lib.gui.parameter_container_widgets.ParameterContainerScrollWidget import ParameterContainerScrollWidget
from simojio.lib.gui.optimization_settings.OptimizationSettingsScrollWidget import OptimizationSettingsScrollWidget
from simojio.lib.enums.ParameterCategory import ParameterCategory
from simojio.lib.Sample import Sample
from simojio.lib.parameters import *
from simojio.lib.ParameterContainer import ParameterContainer
from simojio.lib.abstract_modules import *
from simojio.lib.enums.ExecutionMode import ExecutionMode

from typing import Union, List


class SampleWidget(QtWidgets.QMainWindow):
    """
    Dockwidget that contains
    (1) generic module parameters
    (2) evaluation set parameters
    (3) variables_and_expressions, expressions, (functions)
    (4) optimization settings
    (5) layer structure
    """

    def __init__(self, sample: Sample):
        super().__init__()

        self.sample = sample
        self.execution_mode = None

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks|QtWidgets.QMainWindow.AllowTabbedDocks)

        self.float_parameter_widgets = []

        self.generic_parameters_widget_name = "generic parameters"
        self.generic_parameters_widget = ParameterContainerScrollWidget()

        self.evaluation_sets_widget_name = "evaluation sets"
        self.evaluation_sets_widget = EvaluationSetScrollWidget()

        self.variables_widget_name = "variables"
        self.variables_widget = ParameterContainerScrollWidget(is_module_dependent=False)
        self.variables_widget.set_parameter_container(ParameterContainer(ParameterCategory.VARIABLE))

        self.expressions_widget_name = "expressions"
        self.expressions_widget = ParameterContainerScrollWidget(is_module_dependent=False)
        self.expressions_widget.set_parameter_container(ParameterContainer(ParameterCategory.EXPRESSION))

        self.optimization_widget_name = "optimization settings"
        self.optimization_widget = OptimizationSettingsScrollWidget(show_sample_related_settings=True)

        self.layer_stack_widget_name = "layer stack"
        self.layer_stack_widget = LayerStackScrollWidget()

        self.dockwidget_list = []
        self.dockwidget_name_dict = {}
        self.name_dockwidget_dict = {}

        self.variable_names = []
        self.variable_prefix = Variable.prefix
        self.expression_names = []
        self.expression_prefix = Expression.prefix
        self.global_free_parameters_names = []

        self.init_ui()

        self.load_sample_values(self.sample)

    def init_ui(self):

        self.generic_parameters_widget.parameter_container_widget.float_par_added_sig.connect(self.add_float_par_widget)
        self.layer_stack_widget.layer_stack_widget.float_par_added_sig.connect(self.add_float_par_widget)
        self.evaluation_sets_widget.evaluation_set_containers_widget.float_par_added_sig.connect(self.add_float_par_widget)

        add_variable_action = QtWidgets.QAction("Add variable", self)
        self.variables_widget.add_context_menu_action(add_variable_action, self.add_variable)
        self.variables_widget.parameter_container_widget.parameter_added_sig.connect(self.sync_free_parameter_added)
        self.variables_widget.parameter_container_widget.parameter_deleted_sig.connect(self.sync_free_parameter_deleted)

        add_expression_action = QtWidgets.QAction("Add expression", self)
        self.expressions_widget.add_context_menu_action(add_expression_action, self.add_expression)
        self.expressions_widget.parameter_container_widget.parameter_added_sig.connect(self.sync_free_parameter_added)
        self.expressions_widget.parameter_container_widget.parameter_deleted_sig.connect(self.sync_free_parameter_deleted)

        self.add_dockwidget(self.generic_parameters_widget_name, self.generic_parameters_widget)
        self.add_dockwidget(self.evaluation_sets_widget_name, self.evaluation_sets_widget)
        self.add_dockwidget(self.variables_widget_name, self.variables_widget)
        self.add_dockwidget(self.expressions_widget_name, self.expressions_widget)
        self.add_dockwidget(self.optimization_widget_name, self.optimization_widget)
        self.add_dockwidget(self.layer_stack_widget_name, self.layer_stack_widget)

        self.setTabPosition(QtCore.Qt.TopDockWidgetArea, QtWidgets.QTabWidget.North)

    def set_module(self, module: AbstractModule):
        self.generic_parameters_widget.set_module(module)
        self.evaluation_sets_widget.set_module(module)
        self.optimization_widget.set_module(module)
        self.layer_stack_widget.set_module(module)

        # disable evaluation sets widget for modules without evaluation set parameters
        evaluation_set_dock_widget = self.name_dockwidget_dict[self.evaluation_sets_widget_name]
        enable_evaluation_set_widget = module.has_evaluation_parameters()
        self._enable_dockwidget(enable_evaluation_set_widget, evaluation_set_dock_widget)

        # disable layer widget if no layer parameters given
        layer_dock_widget = self.name_dockwidget_dict[self.layer_stack_widget_name]
        enable_layers = (len(module.available_layers) > 0)
        self._enable_dockwidget(enable_layers, layer_dock_widget)

    def set_execution_mode(self, execution_mode: ExecutionMode):
        """Enable/disable widgets that are relevant/irrelevant for the given execution mode."""

        self.execution_mode = execution_mode

        optimization_dockwidget = self.name_dockwidget_dict[self.optimization_widget_name]
        variable_widgets = self.variables_widget.parameter_container_widget.widget_dict.values()

        if execution_mode is ExecutionMode.SINGLE:
            self._enable_dockwidget(False, optimization_dockwidget)
            for variable_widget in variable_widgets:
                variable_widget.widget_list[0].setEnabled(True)
                for widget in variable_widget.widget_list[1:]:
                    widget.setEnabled(False)
        elif execution_mode is ExecutionMode.VARIATION:
            self._enable_dockwidget(False, optimization_dockwidget)
            for variable_widget in variable_widgets:
                variable_widget.widget_list[-1].setEnabled(True)
        elif execution_mode in [ExecutionMode.OPTIMIZATION, ExecutionMode.COUPLED_OPTIMIZATION]:
            self._enable_dockwidget(True, optimization_dockwidget)
            for variable_widget in variable_widgets:
                variable_widget.widget_list[0].setEnabled(True)
                variable_widget.widget_list[3].setEnabled(False)
                variable_widget.widget_list[-1].setEnabled(True)

        for variable_widget in variable_widgets:
            self._enable_variable_subwidgets(variable_widget)

    def _enable_dockwidget(self, enable: bool, dockwidget: QtWidgets.QDockWidget):
        if enable:
            dockwidget.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable| QtWidgets.QDockWidget.DockWidgetClosable)
            dockwidget.show()
        else:
            dockwidget.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable)
            dockwidget.hide()

    def load_sample_values(self, sample: Sample):
        """Set the values stored in sample to the widgets"""

        for parameter in sample.variables.get_parameters():
            self.add_variable(parameter)

        for parameter in sample.expressions.get_parameters():
            self.add_expression(parameter)

        self.generic_parameters_widget.set_parameter_container(sample.generic_parameters)
        self.evaluation_sets_widget.set_parameter_container_list(sample.get_evaluation_sets())
        self.optimization_widget.set_settings_container(sample.optimization_settings)

        self.layer_stack_widget.set_layer_list(sample.layer_list)

    def get_sample(self) -> Sample:

        self.sample.set_variables_parameter_container(self.variables_widget.get_parameter_container())
        self.sample.set_expressions_parameter_container(self.expressions_widget.get_parameter_container())
        self.sample.set_generic_parameter_container(self.generic_parameters_widget.get_parameter_container())
        self.sample.set_evaluation_set_parameter_container_list(
            self.evaluation_sets_widget.get_parameter_container_list())
        self.sample.set_optimization_settings_container(self.optimization_widget.get_settings_container())
        self.sample.set_layer_list(self.layer_stack_widget.get_layer_list())

        return self.sample

    def set_name(self, name: str):
        self.sample.name = name

    def get_name(self) -> str:
        return self.sample.name

    def add_dockwidget(self, name, widget):

        dockWidget = QtWidgets.QDockWidget(self)
        dockWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable| QtWidgets.QDockWidget.DockWidgetClosable)
        dockWidget.setWindowTitle(name)
        dockWidget.setStyleSheet("QDockWidget {font: bold}")
        dockWidget.setWidget(widget)

        # dockWidget.topLevelChanged.connect(lambda: self.set_title_bar(dockWidget))

        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockWidget)

        self.dockwidget_list.append(dockWidget)
        self.dockwidget_name_dict.update({dockWidget: name})
        self.name_dockwidget_dict.update({name: dockWidget})

        return dockWidget

    def add_variable(self, variable=None):

        try:
            var_name = variable.name
        except:
            i = 0
            while (self.variable_prefix + str(i)) in self.variable_names:
                i += 1

            var_name = self.variable_prefix + str(i)
            variable = Variable(name=var_name, value=0.)

        self.variable_names.append(var_name)
        self.variables_widget.add_parameter(variable, is_deletable=True)

        variable_widget = self.variables_widget.parameter_container_widget.widget_dict[var_name]
        vary_checkbox = variable_widget.widget_list[-1].value_widget
        vary_checkbox.toggled.connect(lambda: self._enable_variable_subwidgets(variable_widget))

        self.set_execution_mode(self.execution_mode)

    def _enable_variable_subwidgets(self, variable_widget):
        vary_checkbox = variable_widget.widget_list[-1].value_widget
        do_vary = vary_checkbox.isChecked()

        if self.execution_mode is ExecutionMode.VARIATION:
            variable_widget.widget_list[0].setEnabled(not do_vary)
            variable_widget.widget_list[1].setEnabled(do_vary)
            variable_widget.widget_list[2].setEnabled(do_vary)
            variable_widget.widget_list[3].setEnabled(do_vary)
        elif self.execution_mode is ExecutionMode.OPTIMIZATION:
            variable_widget.widget_list[1].setEnabled(do_vary)
            variable_widget.widget_list[2].setEnabled(do_vary)

    def add_expression(self, expression=None):

        try:
            expr_name = expression.name
        except:
            i = 0
            while (self.expression_prefix + str(i)) in self.expression_names:
                i += 1

            expr_name = self.expression_prefix + str(i)
            expression = Expression(name=expr_name, value="1.")

        self.expression_names.append(expr_name)
        self.expressions_widget.add_parameter(expression, is_deletable=True)

    def sync_free_parameter_added(self):
        """
        Update widgets that contain free parameters
        :param parameter:
        :return:
        """
        self.sync_free_parameters(global_free_parameters_names=None)

    def sync_free_parameter_deleted(self, parameter: Union[SingleParameter, NestedParameter, MultivalueParameter]):

        if parameter.name in self.variable_names:
            del self.variable_names[self.variable_names.index(parameter.name)]

        if parameter.name in self.expression_names:
            del self.expression_names[self.expression_names.index(parameter.name)]

        self.sync_free_parameters(global_free_parameters_names=None)

    def sync_free_parameters(self, global_free_parameters_names=Union[None, List[str]]):

        if global_free_parameters_names is not None:
            self.global_free_parameters_names = global_free_parameters_names

        free_par_names = self.get_free_parameter_names()
        existing_widgets = []
        for idx, widget in enumerate(self.float_parameter_widgets):
            try:
                widget.update_free_parameters(free_par_names)
                if len(free_par_names) == 0:
                    widget.set_fit_parameter_off()
                existing_widgets.append(widget)
            except:  # might be that witget is deleted already
                pass

        self.float_parameter_widgets = existing_widgets

    def get_free_parameter_names(self) -> list:
        return self.variable_names + self.expression_names + self.global_free_parameters_names

    def add_float_par_widget(self, widget: FloatParWidget):

        free_par_names = self.get_free_parameter_names()
        widget.update_free_parameters(free_par_names)
        self.float_parameter_widgets.append(widget)

    def enable_solver_settings(self, enable: bool):
        self.optimization_widget.enable_solver_settings(enable)

    def tabify_widgets(self):

        for idx in range(len(self.dockwidget_list) - 1):
            dockwidget_first = self.dockwidget_list[idx]
            dockwidget_second = self.dockwidget_list[idx + 1]
            self.tabifyDockWidget(dockwidget_first, dockwidget_second)

    def un_tabify_widgets(self):

        show_list = []
        for dockwidget in self.dockwidget_list:
            show_list.append(dockwidget.isVisible())
            self.removeDockWidget(dockwidget)
        for idx, dockwidget in enumerate(self.dockwidget_list):
            self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            if show_list[idx]:
                dockwidget.show()
            else:
                dockwidget.hide()
