import PySide2.QtWidgets as QtWidgets

from simojio.lib.parameters.AnyStringParameter import AnyStringParameter
from simojio.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget


class AnyStringParWidget(ParameterWidget):

    def __init__(self, parameter: AnyStringParameter, is_sub_parameter=False):

        super().__init__(parameter, is_sub_parameter)

        self.value_widget = QtWidgets.QTextEdit()
        self.value_widget.setPlainText(parameter.value)
        self.value_widget.setMaximumHeight(50)
        self.add_value_widget(self.value_widget)

    def set_content(self, content: str):
        content, success = self.parameter.set_value(content)
        self.value_widget.setPlainText(content)

    def get_content(self):
        return self.value_widget.toPlainText()