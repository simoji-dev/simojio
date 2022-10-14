import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
from PySide2.QtCore import Signal
from simoji.lib.CompleteLayer import CompleteLayer
from simoji.lib.BasicFunctions import *


class LayerHeaderWidget(QtWidgets.QGroupBox):

    minimize_sig = Signal(QtWidgets.QGroupBox)

    def __init__(self, layer: CompleteLayer):

        super().__init__()

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        # use slightly different transparency for header to make it visible
        color = list(layer.color)
        color[3] += 50
        if color[3] >= 200:
            color[3] -= 100
        color = tuple(color)

        self.setStyleSheet("QGroupBox { border: 0px solid silver; background-color: rgba" + str(color)
                           + "; font: bold; padding: 5px;} QLabel {font: bold}")
        self.setMaximumHeight(25)
        self.layout.setMargin(0)
        self.name_label = QtWidgets.QLabel(layer.name + " (" + layer.layer_type.value + ")")

        self.layout.addWidget(self.name_label)
        self.layout.addStretch(1)

        self.arrow_button = QtWidgets.QPushButton(QtGui.QIcon(icon_path("arrow_up.svg")), "", self)
        self.arrow_button.clicked.connect(self.arrow_button_clicked)
        self.layout.addWidget(self.arrow_button)

    def set_parameters_minimized(self, minimize: bool):
        if minimize:
            self.arrow_button.setIcon(QtGui.QIcon(icon_path("arrow_down.svg")))
        else:
            self.arrow_button.setIcon(QtGui.QIcon(icon_path("arrow_up.svg")))

    def arrow_button_clicked(self):
        self.minimize_sig.emit(self)