import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore

from PySide2.QtCore import Signal

from simoji.lib.ParameterContainer import ParameterContainer
from simoji.lib.parameters import *
from simoji.lib.gui.ParameterWidgetTranslator import parameter2widget
from simoji.lib.gui.parameter_widgets.FloatParWidget import FloatParWidget
from simoji.lib.gui.parameter_widgets.NestedParWidget import NestedParWidget
from simoji.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget
import copy
from typing import Union, Callable


class ParameterContainerWidget(QtWidgets.QGroupBox):
    """
    Contains widgets of parameters that are stored in a parameter container. Shows only the widgets that belong to
    current module.
    """

    parameter_added_sig = Signal()
    parameter_deleted_sig = Signal(Parameter)
    float_par_added_sig = Signal(QtWidgets.QWidget)

    delete_container_sig = Signal(QtWidgets.QWidget)

    def __init__(self, is_module_dependent=True):

        super().__init__()

        self.is_module_dependent = is_module_dependent

        self.current_module = None
        self.parameter_container = None
        self.widget_dict = {}               # {parameter_name: widget}

        # set layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setMargin(0)
        self.setLayout(self.layout)

        self.parameters_layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.parameters_layout)
        self.layout.addStretch(1)

        self.setStyleSheet("QGroupBox {border: None; background-color: lightgrey;}")

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.popMenu = QtWidgets.QMenu(self)

    def set_parameter_container(self, parameter_container: ParameterContainer):
        """Set container and update widgets (if module is already set)."""

        self.parameter_container = parameter_container

        if self.is_module_dependent:
            self.parameter_container.set_module(self.current_module)    # should also work if current_module=None
            for parameter_object in self.parameter_container.get_module_parameters():
                self._add_widget(parameter_object, is_deletable=False)
        else:
            for parameter_object in self.parameter_container.get_all_parameter_objects():
                self._add_widget(parameter_object, is_deletable=True)

    def get_parameter_container(self) -> ParameterContainer:
        """Update parameter container with gui values and return it."""

        for par_name in self.widget_dict:
            self.parameter_container.set_parameters({par_name: self.widget_dict[par_name].get_content()})

        return copy.deepcopy(self.parameter_container)  # copy of the container (protect changes from outside)

    def set_module(self, module):
        if self.is_module_dependent:
            self.parameter_container.set_module(module)

            module_parameters_list = self.parameter_container.get_module_parameters()
            module_parameters_dict = {parameter.name: parameter for parameter in module_parameters_list}

            # add missing widgets
            for parameter_object in module_parameters_list:
                if parameter_object.name in self.widget_dict:
                    widget = self.widget_dict[parameter_object.name]
                    if not isinstance(parameter_object, type(widget.parameter)):
                        self._delete_widget(widget)
                        self._add_widget(parameter_object)
                else:
                    self._add_widget(parameter_object)

            # hide all widgets that do not belong to the module
            for par_name in self.widget_dict:
                if par_name in module_parameters_dict:
                    par_obj = module_parameters_dict[par_name]
                    self.widget_dict[par_name].show()
                    if isinstance(par_obj, FloatParameter):
                        self.widget_dict[par_name].update_show()  # work around to avoid showing both input widgets
                else:
                    self.widget_dict[par_name].hide()

    def add_parameter(self, parameter: Union[SingleParameter, NestedParameter], is_deletable=False):
        self._add_widget(parameter, is_deletable)

    def _add_widget(self, parameter: Union[SingleParameter, NestedParameter], is_deletable=False):

        if isinstance(parameter, SingleParameter):
            widget = parameter2widget(parameter)
        elif isinstance(parameter, FloatParameter):
            widget = FloatParWidget(parameter)
        elif isinstance(parameter, NestedParameter):
            widget = NestedParWidget(parameter)
        else:
            raise ValueError("Couldn't translate parameter '" + str(parameter) + "' to widget.")

        try:
            widget.set_line_color(self.color)
        except:
            pass

        if is_deletable:
            widget.add_delete_btn()

        if isinstance(widget, FloatParWidget):
            self.float_par_added_sig.emit(widget)

        if len(self.widget_dict) == 0:
            widget.layout.setContentsMargins(10, 10, 10, 0)
        else:
            widget.layout.setContentsMargins(10, 0, 10, 0)

        self.parameters_layout.addWidget(widget)
        self.widget_dict.update({parameter.name: widget})

        if is_deletable:
            widget.widget_deleted_sig.connect(self._delete_widget)

        self.parameter_added_sig.emit()

    def _delete_widget(self, widget: ParameterWidget):
        self.parameters_layout.removeWidget(widget)
        del self.widget_dict[widget.parameter.name]
        widget.deleteLater()
        self.parameter_deleted_sig.emit(widget.parameter)

    def on_context_menu(self, point):
        # show context menu
        self.popMenu.exec_(self.mapToGlobal(point))

    def add_context_menu_action(self, action: QtWidgets.QAction, connected_method: Callable):
        action.triggered.connect(connected_method)
        self.popMenu.addAction(action)

    def _delete_container(self):
        self.delete_container_sig.emit(self)

