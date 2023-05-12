import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
from simojio.lib.gui.decoration.QHLine import QHLine

from simojio.lib.parameters.FloatParameter import FloatParameter
from simojio.lib.BasicFunctions import *


class FloatParWidget(QtWidgets.QWidget):

    def __init__(self, parameter: FloatParameter):

        super().__init__()

        self.parameter = parameter
        self.setToolTip(parameter.description)
        self.name_widget = QtWidgets.QLabel(parameter.name)

        self.is_set_as_fit_parameter = parameter.is_set_to_free_parameter.value

        self.layout = QtWidgets.QVBoxLayout()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.values_layout = QtWidgets.QHBoxLayout()

        self.value_widget_list = []

        self.float_line_edit = QtWidgets.QLineEdit()

        self.free_par_combo = QtWidgets.QComboBox()
        self.free_par_combo.setStyleSheet("QComboBox {background-color: lightgreen}")

        self.set_to_free_par_btn = QtWidgets.QPushButton(QtGui.QIcon(icon_path("set_as_fitparameter.svg")), "")
        self.set_to_free_par_btn.clicked.connect(self.set_as_fit_parameter_clicked)
        self.set_to_free_par_btn.setMaximumWidth(22)

        self.add_value_widget(self.float_line_edit)
        self.add_value_widget(self.free_par_combo)
        self.add_value_widget(self.set_to_free_par_btn)

        self.header_layout.addWidget(self.name_widget)

        self.layout.addLayout(self.header_layout)
        self.layout.addLayout(self.values_layout)
        self.layout.addWidget(QHLine())

        self.setLayout(self.layout)

        self.set_content(self.parameter.get_parameter_values_list())

    def get_content(self):
        return [float(self.float_line_edit.text()), self.free_par_combo.currentText(), self.is_set_as_fit_parameter]

    def set_content(self, content: list):

        self.float_line_edit.setText(str(content[0]))

        if content[2]:
            self.set_fit_parameter_on()
        else:
            self.set_fit_parameter_off()

        all_items = [self.free_par_combo.itemText(idx) for idx in range(self.free_par_combo.count())]
        if content[1] not in all_items:
            self.free_par_combo.addItem(content[1])
        self.free_par_combo.setCurrentText(content[1])

    def add_value_widget(self, widget: QtWidgets.QWidget):
        self.values_layout.addWidget(widget)
        self.value_widget_list.append(widget)

    def set_as_fit_parameter_clicked(self):

        if self.free_par_combo.count() > 0:
            if self.is_set_as_fit_parameter:
                self.set_fit_parameter_off()
            else:
                self.set_fit_parameter_on()
        else:
            QtWidgets.QMessageBox.warning(self, "No free parameter defined",
                                          "Add free parameter by right click in free parameters widget",
                                          QtWidgets.QMessageBox.Ok)

    def set_fit_parameter_on(self):
        self.float_line_edit.hide()
        self.free_par_combo.show()
        self.set_to_free_par_btn.setStyleSheet("QPushButton {background-color: lightgreen}")
        self.set_to_free_par_btn.setToolTip("Unset fit parameter")
        self.is_set_as_fit_parameter = True

        if self.free_par_combo.currentText() == "":
            names = [self.free_par_combo.itemText(idx) for idx in range(self.free_par_combo.count())]
            names_without_empty_str = [name for name in names if name != ""]
            self.free_par_combo.clear()
            self.free_par_combo.addItems(names_without_empty_str)

    def set_fit_parameter_off(self):
        self.float_line_edit.show()
        self.free_par_combo.hide()
        self.set_to_free_par_btn.setStyleSheet("QPushButton {background-color: None}")
        self.set_to_free_par_btn.setToolTip("Set as fit parameter")
        self.is_set_as_fit_parameter = False

    def update_free_parameters(self, free_parameter_names: list):

        previous_value = self.free_par_combo.currentText()
        self.free_par_combo.clear()
        self.free_par_combo.addItems(free_parameter_names)
        if previous_value in free_parameter_names:
            self.free_par_combo.setCurrentText(previous_value)

    def update_show(self):
        if self.is_set_as_fit_parameter:
            self.set_fit_parameter_on()
        else:
            self.set_fit_parameter_off()


