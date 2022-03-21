from simoji.lib.parameters.NestedParameter import NestedParameter
from simoji.lib.gui.ParameterWidgetTranslator import parameter2widget
from simoji.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget


class NestedParWidget(ParameterWidget):

    def __init__(self, parameter: NestedParameter, enable_fit_parameters=True):
        super().__init__(parameter)

        self.widget_list = []

        for nested_par in parameter.parameters:
            widget = parameter2widget(nested_par, is_sub_parameter=True)
            self.widget_list.append(widget)
            self.add_value_widget(widget)

    def set_content(self, content):
        for idx, widget in enumerate(self.value_widget_list):
            if isinstance(content, list):
                if idx < len(content):
                    widget.set_content(content[idx])

    def get_content(self):
        return [widget.get_content() for widget in self.widget_list]
