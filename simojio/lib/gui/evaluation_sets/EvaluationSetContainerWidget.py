import PySide2.QtWidgets as QtWidgets
from PySide2.QtCore import Signal

from simojio.lib.gui.parameter_container_widgets.ParameterContainerWidget import ParameterContainerWidget
from simojio.lib.ParameterContainer import ParameterContainer


class EvaluationSetContainerWidget(ParameterContainerWidget):

    add_evaluation_set_sig = Signal()
    delete_evaluation_set_sig = Signal(QtWidgets.QWidget)
    duplicate_evaluation_set_sig = Signal(ParameterContainer)
    remove_all_sig = Signal()

    def __init__(self):
        super().__init__()

        # create context menu actions
        self.add_action = QtWidgets.QAction("add evaluation set", self)
        self.add_context_menu_action(self.add_action, self._add_evaluation_set)

        self.delete_container_action = QtWidgets.QAction("delete evaluation set")
        self.add_context_menu_action(self.delete_container_action, self._delete_evaluation_set)

        self.remove_all_action = QtWidgets.QAction("remove all")
        self.add_context_menu_action(self.remove_all_action, self._remove_all)

        self.duplicate_container_action = QtWidgets.QAction("duplicate evaluation set")
        self.add_context_menu_action(self.duplicate_container_action, self._duplicate_evaluation_set)

    def _add_evaluation_set(self):
        self.add_evaluation_set_sig.emit()

    def _delete_evaluation_set(self):
        self.delete_evaluation_set_sig.emit(self)

    def _remove_all(self):
        self.remove_all_sig.emit()

    def _duplicate_evaluation_set(self):
        self.duplicate_evaluation_set_sig.emit(self.get_parameter_container())
