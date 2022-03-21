import PySide2.QtWidgets as QtWidgets
from PySide2.QtCore import Signal

from simoji.lib.gui.parameter_container_widgets.ParameterContainerWidget import ParameterContainerWidget
from simoji.lib.ParameterContainer import ParameterContainer


class DatasetContainerWidget(ParameterContainerWidget):

    add_dataset_sig = Signal()
    delete_dataset_sig = Signal(QtWidgets.QWidget)
    duplicate_dataset_sig = Signal(ParameterContainer)
    remove_all_sig = Signal()

    def __init__(self):
        super().__init__()

        # create context menu actions
        self.add_action = QtWidgets.QAction("add data set", self)
        self.add_context_menu_action(self.add_action, self._add_dataset)

        self.delete_container_action = QtWidgets.QAction("delete data set")
        self.add_context_menu_action(self.delete_container_action, self._delete_dataset)

        self.remove_all_action = QtWidgets.QAction("remove all")
        self.add_context_menu_action(self.remove_all_action, self._remove_all)

        self.duplicate_container_action = QtWidgets.QAction("duplicate data set")
        self.add_context_menu_action(self.duplicate_container_action, self._duplicate_dataset)

    def _add_dataset(self):
        self.add_dataset_sig.emit()

    def _delete_dataset(self):
        self.delete_dataset_sig.emit(self)

    def _remove_all(self):
        self.remove_all_sig.emit()

    def _duplicate_dataset(self):
        self.duplicate_dataset_sig.emit(self.get_parameter_container())