from simojio.lib.enums.LayerType import LayerType
from simojio.lib.ParameterContainer import ParameterContainer


class CompleteLayer(ParameterContainer):

    def __init__(self, name: str, layer_type: LayerType, enabled: bool, color: (int, int, int, int)):

        super().__init__(category=layer_type)

        self.name = name
        self.layer_type = layer_type
        self.enabled = enabled
        self.color = color

        self.parameters = []

    def set_parameters(self, parameters_dict: dict):
        super(CompleteLayer, self).set_parameters(parameters_dict)
        self.parameters = self.get_all_parameter_objects()

    def set_module_values_with_replaced_free_parameters(self, variables_and_expressions: dict):
        """Store the current values in the parameters dict to make them easily accessible within a module."""
        self.parameters = self.get_module_values(variables_and_expressions)


