from simoji.lib.enums.LayerType import LayerType
from simoji.lib.ParameterContainer import ParameterContainer


class Layer(ParameterContainer):

    def __init__(self, name: str, layer_type: LayerType, enabled: bool, color: (int, int, int, int)):

        super().__init__(category=layer_type)

        self.name = name
        self.layer_type = layer_type
        self.enabled = enabled
        self.color = color

        self.parameters = {}        # {"parameter_name": parameter_values}

    def set_module_values_with_replaced_free_parameters(self, variables_and_expressions: dict):
        """Store the current values in the parameters dict to make them easily accessible within a module."""
        self.parameters = self.get_module_values(variables_and_expressions)


