import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
from PySide2.QtCore import Signal

import simojio.lib.BasicFunctions as BasicFunctions
from simojio.lib.gui.Buttons import RotatedButton
from simojio.lib.gui.parameter_container_widgets.ParameterContainerScrollWidget import ParameterContainerScrollWidget
from simojio.lib.gui.optimization_settings.OptimizationSettingsScrollWidget import OptimizationSettingsScrollWidget
from simojio.lib.ParameterContainer import ParameterContainer
from simojio.lib.VariablesValuesContainer import VariablesValuesContainer
from simojio.lib.ExpressionsValuesContainer import ExpressionsValuesContainer
from simojio.lib.OptimizationSettingsContainer import OptimizationSettingsContainer
from simojio.lib.enums.ParameterCategory import ParameterCategory
from simojio.lib.parameters import *
from simojio.lib.enums.ExecutionMode import ExecutionMode
from simojio.lib.abstract_modules import AbstractModule

from typing import Union


class SideWidgetGlobalSettings(QtWidgets.QMainWindow):
    update_global_free_parameters_sig = Signal(list)

    def __init__(self):

        super().__init__()

        self.execution_mode = None
        self.all_widgets = []

        self._variables_label = "Global variables"
        self._variables_widget = ParameterContainerScrollWidget(is_module_dependent=False)
        self._variables_widget.parameter_container_widget.parameter_added_sig.connect(self.sync_free_parameters)
        self._variables_widget.parameter_container_widget.parameter_deleted_sig.connect(
            self._sync_free_parameter_deleted)
        self._variables_dock_widget = self._add_dockwidget(self._variables_label, self._variables_widget)
        self._variables_dock_widget.setObjectName("Global variables")
        self._variables_dock_widget.visibilityChanged.connect(
            lambda: self._show_variables(self._variables_dock_widget.isVisible()))
        self._is_variables_widget_shown = False

        self._expressions_label = "Global expressions"
        self._expressions_widget = ParameterContainerScrollWidget(is_module_dependent=False)
        self._expressions_widget.parameter_container_widget.parameter_added_sig.connect(self.sync_free_parameters)
        self._expressions_widget.parameter_container_widget.parameter_deleted_sig.connect(
            self._sync_free_parameter_deleted)
        self._expressions_dock_widget = self._add_dockwidget(self._expressions_label, self._expressions_widget)
        self._expressions_dock_widget.setObjectName("Global expressions")
        self._expressions_dock_widget.visibilityChanged.connect(
            lambda: self._show_expressions(self._expressions_dock_widget.isVisible()))
        self._is_expressions_widget_shown = False

        self._optimization_label = "Global optimization settings"
        self._optimization_widget = OptimizationSettingsScrollWidget(show_sample_related_settings=False)
        self._optimization_dock_widget = self._add_dockwidget(self._optimization_label, self._optimization_widget)
        self._optimization_dock_widget.setObjectName("Global optimization settings")
        self._optimization_dock_widget.visibilityChanged.connect(
            lambda: self._show_optimization_widget(self._optimization_dock_widget.isVisible()))
        self._is_optimization_widget_shown = False
        self._global_optimization_settings_enabled = False

        # -- toolbar and buttons --
        self._side_toolbar = QtWidgets.QToolBar(self)
        self._side_toolbar.setObjectName("side toolbar")

        self._global_variables_btn = self._get_button(label=self._variables_label,
                                                      icon=QtGui.QIcon(BasicFunctions.icon_path('variable.svg')),
                                                      is_shown=self._is_variables_widget_shown)
        self._global_variables_btn.clicked.connect(self._global_variables_button_clicked)

        self._global_expressions_btn = self._get_button(label=self._expressions_label,
                                                        icon=QtGui.QIcon(BasicFunctions.icon_path('variable.svg')),
                                                        is_shown=self._is_expressions_widget_shown)
        self._global_expressions_btn.clicked.connect(self._global_expressions_button_clicked)

        self._optimization_settings_btn = self._get_button(label=self._optimization_label,
                                                           icon=QtGui.QIcon(BasicFunctions.icon_path('settings.svg')),
                                                           is_shown=self._is_optimization_widget_shown)
        self._optimization_settings_btn.clicked.connect(self._optimization_button_clicked)

        self._init_ui()

        self._show_variables(self._is_variables_widget_shown)
        self._show_expressions(self._is_expressions_widget_shown)
        self._show_optimization_widget(self._is_optimization_widget_shown)

        self._global_variable_names = []
        self._global_variable_prefix = "G_" + Variable.prefix
        self._global_expression_names = []
        self._global_expression_prefix = "G_" + Expression.prefix

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def _init_ui(self):

        # style toolbar
        self._side_toolbar.setMovable(False)
        self._side_toolbar.setToolTip("Global settings")
        self._side_toolbar.setStyleSheet("QToolBar {padding: 0px;}")
        self.addToolBar(QtCore.Qt.LeftToolBarArea, self._side_toolbar)

        # fill toolbar
        self._side_toolbar.addWidget(self._global_variables_btn)
        self._side_toolbar.addSeparator()
        self._side_toolbar.addWidget(self._global_expressions_btn)
        self._side_toolbar.addSeparator()
        self._side_toolbar.addWidget(self._optimization_settings_btn)
        self._side_toolbar.addSeparator()

        # -- dock widgets --
        add_variable_action = QtWidgets.QAction("Add global variable", self)
        self._variables_widget.add_context_menu_action(add_variable_action, self._add_global_variable)
        self._variables_widget.set_parameter_container(ParameterContainer(ParameterCategory.VARIABLE))

        add_expression_action = QtWidgets.QAction("Add global expression", self)
        self._expressions_widget.add_context_menu_action(add_expression_action, self._add_global_expression)
        self._expressions_widget.set_parameter_container(ParameterContainer(ParameterCategory.EXPRESSION))

    def enable_global_optimization_settings(self, enable: bool):
        self._global_optimization_settings_enabled = enable
        self._show_optimization_widget(self._is_optimization_widget_shown)
        self._optimization_widget.enable_solver_settings(enable)

    def set_global_variables_container(self, variables_container: VariablesValuesContainer):
        for parameter in variables_container.get_parameters():
            self._add_global_variable(parameter)

    def set_global_expressions_container(self, expressions_container: ExpressionsValuesContainer):
        for parameter in expressions_container.get_parameters():
            self._add_global_expression(parameter)

    def get_global_variables_container(self) -> ParameterContainer:
        return self._variables_widget.get_parameter_container()

    def get_global_expressions_container(self) -> ParameterContainer:
        return self._expressions_widget.get_parameter_container()

    def set_optimization_settings_container(self, opt_container: OptimizationSettingsContainer):
        self._optimization_widget.set_settings_container(opt_container)

    def get_optimization_settings_container(self) -> OptimizationSettingsContainer:
        return self._optimization_widget.get_settings_container()

    def set_execution_mode(self, execution_mode: ExecutionMode):
        """Enable/disable widgets that are relevant/irrelevant for the given execution mode."""

        self.execution_mode = execution_mode

        variable_widgets = self._variables_widget.parameter_container_widget.widget_dict.values()

        if execution_mode is ExecutionMode.SINGLE:
            for variable_widget in variable_widgets:
                variable_widget.widget_list[0].setEnabled(True)
                for widget in variable_widget.widget_list[1:]:
                    widget.setEnabled(False)
        elif execution_mode is ExecutionMode.VARIATION:
            for variable_widget in variable_widgets:
                variable_widget.widget_list[-1].setEnabled(True)
        elif execution_mode in [ExecutionMode.OPTIMIZATION, ExecutionMode.COUPLED_OPTIMIZATION]:
            for variable_widget in variable_widgets:
                variable_widget.widget_list[0].setEnabled(True)
                variable_widget.widget_list[3].setEnabled(False)
                variable_widget.widget_list[-1].setEnabled(True)

        for variable_widget in variable_widgets:
            self._enable_variable_subwidgets(variable_widget)

    def set_module(self, module: AbstractModule):
        self._optimization_widget.set_module(module)

    def _get_button(self, label: str, icon: QtGui.QIcon, is_shown: bool) -> QtWidgets.QWidget:

        width = 25

        btn = RotatedButton(label, self, orientation='east')
        btn.setIcon(icon)
        btn.setToolTip("Show " + label)
        btn.setMaximumWidth(width)
        btn_style = self._get_side_toolbar_pushbutton_style(is_shown)
        btn.setStyleSheet(btn_style)
        btn.setChecked(False)

        return btn

    def _show_variables(self, show_bool: bool):

        self._is_variables_widget_shown = show_bool

        btn_style = self._get_side_toolbar_pushbutton_style(btn_is_checked=self._is_variables_widget_shown)
        self._global_variables_btn.setStyleSheet(btn_style)

        if self._is_variables_widget_shown:
            self._variables_dock_widget.show()
        else:
            self._variables_dock_widget.hide()

        self._resize_to_minimum()

    def _show_expressions(self, show_bool: bool):

        self._is_expressions_widget_shown = show_bool

        btn_style = self._get_side_toolbar_pushbutton_style(btn_is_checked=self._is_expressions_widget_shown)
        self._global_expressions_btn.setStyleSheet(btn_style)

        if self._is_expressions_widget_shown:
            self._expressions_dock_widget.show()
        else:
            self._expressions_dock_widget.hide()

        self._resize_to_minimum()

    def _show_optimization_widget(self, show_bool: bool):
        self._is_optimization_widget_shown = show_bool

        btn_style = self._get_side_toolbar_pushbutton_style(btn_is_checked=self._is_optimization_widget_shown,
                                                            enabled=self._global_optimization_settings_enabled)
        self._optimization_settings_btn.setStyleSheet(btn_style)

        if self._is_optimization_widget_shown:
            self._optimization_dock_widget.show()
        else:
            self._optimization_dock_widget.hide()

        self._resize_to_minimum()

    @staticmethod
    def _get_side_toolbar_pushbutton_style(btn_is_checked: bool, enabled=False) -> str:
        """set background grey if button is checked"""

        if enabled:
            if btn_is_checked:
                btn_style = "QPushButton {background-color: lightgreen; border: 0px; padding-left: 5px; padding-right: 5px;} \
                                                         QPushButton:hover {background-color: lightgreen;}"
            else:
                btn_style = "QPushButton {background-color: lightgreen; border: 0px; padding-left: 5px; padding-right: 5px;} \
                                                                         QPushButton:hover {background-color: lightgreen;}"
        else:
            if btn_is_checked:
                btn_style = "QPushButton {background-color: lightgrey; border: 0px; padding-left: 5px; padding-right: 5px;} \
                                             QPushButton:hover {background-color: lightgrey;}"
            else:
                btn_style = "QPushButton {background-color: None; border: 0px; padding-left: 5px; padding-right: 5px;} \
                                             QPushButton:hover {background-color: lightgrey;}"
        return btn_style

    def _add_dockwidget(self, name, widget):

        dockWidget = QtWidgets.QDockWidget(self)
        dockWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetClosable)
        dockWidget.setWindowTitle(name)
        dockWidget.setStyleSheet("QDockWidget {font: bold}")
        dockWidget.setWidget(widget)

        self.all_widgets.append(widget)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dockWidget)

        return dockWidget

    def _add_global_variable(self, variable=None):

        try:
            var_name = variable.name
            var_idx = int(var_name.replace(self._global_variable_prefix, ''))
        except:
            i = 0
            while (self._global_variable_prefix + str(i)) in self._global_variable_names:
                i += 1

            var_name = self._global_variable_prefix + str(i)
            variable = Variable(name=var_name, value=0.)

        self._global_variable_names.append(var_name)
        self._variables_widget.add_parameter(variable, is_deletable=True)

        variable_widget = self._variables_widget.parameter_container_widget.widget_dict[var_name]
        vary_checkbox = variable_widget.widget_list[-1].value_widget
        vary_checkbox.toggled.connect(lambda: self._enable_variable_subwidgets(variable_widget))

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

    def _add_global_expression(self, expression=None):

        try:
            expr_name = expression.name
            expr_idx = int(expr_name.replace(self._global_expression_prefix, ''))
        except:
            i = 0
            while (self._global_expression_prefix + str(i)) in self._global_expression_names:
                i += 1

            expr_name = self._global_expression_prefix + str(i)
            expression = Expression(name=expr_name, value="1.")

        self._global_expression_names.append(expr_name)
        self._expressions_widget.add_parameter(expression, is_deletable=True)

    def _global_variables_button_clicked(self):
        self._is_variables_widget_shown = not self._is_variables_widget_shown
        self._show_variables(self._is_variables_widget_shown)

    def _global_expressions_button_clicked(self):
        self._is_expressions_widget_shown = not self._is_expressions_widget_shown
        self._show_expressions(self._is_expressions_widget_shown)

    def _optimization_button_clicked(self):
        self._is_optimization_widget_shown = not self._is_optimization_widget_shown
        self._show_optimization_widget(self._is_optimization_widget_shown)

    def _get_free_parameter_names(self) -> list:
        return self._global_variable_names + self._global_expression_names

    def sync_free_parameters(self):
        """
        Update widgets that contain free parameters
        :param parameter:
        :return:
        """

        self.update_global_free_parameters_sig.emit(self._get_free_parameter_names())

    def _sync_free_parameter_deleted(self, parameter: Union[SingleParameter, NestedParameter, MultivalueParameter]):

        if parameter.name in self._global_variable_names:
            del self._global_variable_names[self._global_variable_names.index(parameter.name)]

        if parameter.name in self._global_expression_names:
            del self._global_expression_names[self._global_expression_names.index(parameter.name)]

        self.update_global_free_parameters_sig.emit(self._get_free_parameter_names())

    def _resize_to_minimum(self):

        if any([self._is_variables_widget_shown, self._is_expressions_widget_shown,
                self._is_optimization_widget_shown]):
            self.setMaximumWidth(self.parent().parent().width())
        else:
            self.setMaximumWidth(25)
