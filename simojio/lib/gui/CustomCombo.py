import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore


class CustomCombo(QtWidgets.QComboBox):
    """
    Custom combo box for all Combos
    """

    def __init__(self):
        super().__init__()

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        if self.hasFocus():
            QtWidgets.QComboBox.wheelEvent(self, e)