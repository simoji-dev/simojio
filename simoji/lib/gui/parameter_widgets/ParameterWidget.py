import PySide2.QtWidgets as QtWidgets
from PySide2.QtCore import Signal
import PySide2.QtGui as QtGui

from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.parameters.NestedParameter import NestedParameter
from simoji.lib.parameters.MultivalueParameter import MultivalueParameter

from simoji.lib.gui.decoration.QHLine import QHLine
from simoji.lib.BasicFunctions import *

from typing import Union


class ParameterWidget(QtWidgets.QWidget):
    """Abstract class for single parameter widgets"""

    widget_deleted_sig = Signal(QtWidgets.QWidget)

    def __init__(self, parameter: Union[SingleParameter, NestedParameter, MultivalueParameter], is_sub_parameter=False):
        super().__init__()

        self.parameter = parameter
        self.setToolTip(parameter.description)
        self.name_widget = QtWidgets.QLabel(parameter.name)

        self.layout = QtWidgets.QVBoxLayout()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.values_layout = QtWidgets.QHBoxLayout()

        self.value_widget_list = []

        self.header_layout.addWidget(self.name_widget)

        if is_sub_parameter:
            self.setStyleSheet("QLabel {font-size: 8pt; color: grey}")
            self.layout.setContentsMargins(0, 0, 0, 0)

        self.hline = QHLine()

        if is_sub_parameter:
            self.layout.addLayout(self.values_layout)
        else:
            self.layout.addLayout(self.header_layout)
            self.layout.addLayout(self.values_layout)
            self.layout.addWidget(self.hline)

        self.setLayout(self.layout)

    def get_content(self):
        pass

    def set_content(self, content):
        pass

    def add_value_widget(self, widget: QtWidgets.QWidget):
        self.values_layout.addWidget(widget)
        self.value_widget_list.append(widget)

    def add_delete_btn(self):

        del_btn = QtWidgets.QPushButton(QtGui.QIcon(icon_path("delete.svg")), "")
        del_btn.setMaximumWidth(22)
        del_btn.clicked.connect(self.emit_delete_signal)
        self.header_layout.addWidget(del_btn)

    def emit_delete_signal(self):
        self.widget_deleted_sig.emit(self)

