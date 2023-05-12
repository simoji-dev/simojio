import PySide2.QtWidgets as QtWidgets
from typing import Union, Callable

from simojio.lib.gui.parameter_container_widgets.ParameterContainerWidget import ParameterContainerWidget

from simojio.lib.ParameterContainer import ParameterContainer
from simojio.lib.parameters.SingleParameter import SingleParameter
from simojio.lib.parameters.NestedParameter import NestedParameter
from simojio.lib.parameters.MultivalueParameter import MultivalueParameter


class ParameterContainerScrollWidget(QtWidgets.QScrollArea):

    def __init__(self, is_module_dependent=True):
        super().__init__()

        self.is_module_dependent = is_module_dependent

        self.parameter_container_widget = ParameterContainerWidget()
        self.setWidget(self.parameter_container_widget)
        self.setWidgetResizable(True)

    def set_module(self, module):
        if self.is_module_dependent:
            self.parameter_container_widget.set_module(module)

    def set_parameter_container(self, parameter_container: ParameterContainer):
        self.parameter_container_widget.set_parameter_container(parameter_container)

    def add_context_menu_action(self, action: QtWidgets.QAction, connected_method: Callable):
        self.parameter_container_widget.add_context_menu_action(action, connected_method)

    def add_parameter(self, parameter: Union[SingleParameter, NestedParameter, MultivalueParameter], is_deletable=False):
        self.parameter_container_widget.add_parameter(parameter, is_deletable)

    def get_parameter_container(self) -> ParameterContainer:
        return self.parameter_container_widget.get_parameter_container()




