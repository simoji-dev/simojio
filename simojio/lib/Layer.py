from typing import List

from simojio.lib.enums.LayerType import LayerType
from simojio.lib.parameters import Parameter


class Layer:

    def __init__(self, layer_type: LayerType, parameters: List[Parameter]):

        self.layer_type = layer_type
        self.parameters = parameters
