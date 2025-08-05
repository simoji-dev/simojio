import PySide6.QtWidgets as QtWidgets

from simojio.lib.parameters.BoolParameter import BoolParameter
from simojio.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget


class BoolParWidget(ParameterWidget):

    def __init__(self, parameter: BoolParameter, is_sub_parameter=False):

        super().__init__(parameter, is_sub_parameter)
        self.parameter = parameter

        self.value_widget = QtWidgets.QCheckBox("")
        self.add_value_widget(self.value_widget)
        self.set_content(parameter.value)

    def set_content(self, content: bool):
        self.value_widget.setChecked(content)

    def get_content(self):
        return self.value_widget.isChecked()