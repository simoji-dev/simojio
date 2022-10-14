from simoji.lib.parameters.MultiStringParameter import MultiStringParameter
from simoji.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget
from simoji.lib.gui.CustomCombo import CustomCombo


class MultiStringParWidget(ParameterWidget):

    def __init__(self, parameter: MultiStringParameter, is_sub_parameter=False):

        super().__init__(parameter, is_sub_parameter)

        self.value_widget = CustomCombo()
        self.value_widget.addItems(sorted(parameter.bounds, key=str.casefold))
        self.value_widget.setCurrentText(parameter.value)
        self.add_value_widget(self.value_widget)

    def set_content(self, content: str):
        self.value_widget.setCurrentText(content)

    def get_content(self):
        return self.value_widget.currentText()