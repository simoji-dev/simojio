import PySide6.QtWidgets as QtWidgets

from simojio.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget
from simojio.lib.parameters.FixFloatParameter import FixFloatParameter


class FixFloatParWidget(ParameterWidget):

    def __init__(self, parameter: FixFloatParameter, is_sub_parameter=False):

        super().__init__(parameter, is_sub_parameter)

        self.value_widget = QtWidgets.QLineEdit(str(parameter.value))
        self.add_value_widget(self.value_widget)

    def set_content(self, content):
        content, success = self.parameter.set_value(content)
        self.value_widget.setText(str(content))

    def get_content(self):
        return float(self.value_widget.text())