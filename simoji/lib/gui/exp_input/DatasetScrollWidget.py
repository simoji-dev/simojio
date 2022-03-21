import PySide2.QtWidgets as QtWidgets

from simoji.lib.gui.exp_input.MultiDatasetContainersWidget import MultiDatasetContainersWidget
from simoji.lib.ParameterContainer import ParameterContainer

from typing import List


class DatasetScrollWidget(QtWidgets.QScrollArea):

    def __init__(self):

        super().__init__()

        self._current_module = None

        self.dataset_containers_widget = MultiDatasetContainersWidget()
        self.setWidget(self.dataset_containers_widget)
        self.setWidgetResizable(True)

    def set_parameter_container_list(self, parameter_container_list: List[ParameterContainer]):
        self.dataset_containers_widget.set_parameter_container_list(parameter_container_list)

    def get_parameter_container_list(self) -> List[ParameterContainer]:
        return self.dataset_containers_widget.get_parameter_container_list()

    def set_module(self, module):
        self._current_module = module
        self.dataset_containers_widget.set_module(module)