import PySide2.QtWidgets as QtWidgets

from simoji.lib.parameters.BoolParameter import BoolParameter
from simoji.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget


class BoolParWidget(ParameterWidget):
    """Widget that contains single float parameters."""

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