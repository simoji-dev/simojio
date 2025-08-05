import PySide6.QtWidgets as QtWidgets
from typing import List

from simojio.lib.gui.evaluation_sets.MultiEvaluationSetContainersWidget import MultiEvaluationSetContainersWidget
from simojio.lib.ParameterContainer import ParameterContainer


class EvaluationSetScrollWidget(QtWidgets.QScrollArea):

    def __init__(self):

        super().__init__()

        self._current_module = None

        self.evaluation_set_containers_widget = MultiEvaluationSetContainersWidget()
        self.setWidget(self.evaluation_set_containers_widget)
        self.setWidgetResizable(True)

    def set_parameter_container_list(self, parameter_container_list: List[ParameterContainer]):
        self.evaluation_set_containers_widget.set_parameter_container_list(parameter_container_list)

    def get_parameter_container_list(self) -> List[ParameterContainer]:
        return self.evaluation_set_containers_widget.get_parameter_container_list()

    def set_module(self, module):
        self._current_module = module
        self.evaluation_set_containers_widget.set_module(module)