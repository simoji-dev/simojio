from typing import Union, List, Optional

from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.parameters.NestedParameter import NestedParameter
from simoji.lib.parameters.MultivalueParameter import MultivalueParameter

from simoji.lib.enums.ParameterCategory import ParameterCategory
from simoji.lib.enums.LayerType import LayerType


class ModuleParameterContainer:
    """
    Stores all the parameters of a certain module. Needs to be initialized in the class body of each module and filled
    with the available parameters set to their default values.
    """

    def __init__(self):

        self._parameters = {}  # {"category": {"par1_name": par1, "par2_name": par2, ..}}

    def add_generic_parameter(self, parameter: Union[SingleParameter, NestedParameter, MultivalueParameter]):
        if ParameterCategory.GENERIC not in self._parameters:
            self._parameters.update({ParameterCategory.GENERIC: {}})

        self._parameters[ParameterCategory.GENERIC][parameter.name] = parameter

    def add_generic_parameters(self, parameters: List[Union[SingleParameter, NestedParameter, MultivalueParameter]]):
        for parameter in parameters:
            self.add_generic_parameter(parameter)

    def add_evaluation_set_parameter(self, parameter: Union[SingleParameter, NestedParameter, MultivalueParameter]):
        if ParameterCategory.EVALUATION_SET not in self._parameters:
            self._parameters.update({ParameterCategory.EVALUATION_SET: {}})

        self._parameters[ParameterCategory.EVALUATION_SET][parameter.name] = parameter

    def add_evaluation_set_parameters(self, parameters: List[Union[SingleParameter, NestedParameter,
                                                                   MultivalueParameter]]):
        for parameter in parameters:
            self.add_evaluation_set_parameter(parameter)

    def add_layer_parameters(self, parameters: List[Union[SingleParameter, NestedParameter, MultivalueParameter]],
                             layer_type: LayerType):

        if layer_type not in self._parameters:
            self._parameters.update({layer_type: {}})
        for parameter in parameters:
            self._parameters[layer_type][parameter.name] = parameter

    def add_submodule_parameters(self, module, exclude_parameters: Optional[List[
            Union[SingleParameter, NestedParameter, MultivalueParameter]]] = None):

        if exclude_parameters is None:
            exclude_parameters = []

        for category in module.module_parameters.get_categories():
            submodule_parameters = [parameter for parameter in
                                    module.module_parameters.get_parameters(category).values() if parameter not in
                                    exclude_parameters]

            if category is ParameterCategory.GENERIC:
                self.add_generic_parameters(submodule_parameters)
            elif category is ParameterCategory.EVALUATION_SET:
                self.add_evaluation_set_parameters(submodule_parameters)
            elif isinstance(category, LayerType):
                self.add_layer_parameters(submodule_parameters, layer_type=category)

    def add_submodule_generic_parameters(self, module, exclude_parameters: Optional[List[
            Union[SingleParameter, NestedParameter, MultivalueParameter]]] = None):

        if exclude_parameters is None:
            exclude_parameters = []

        submodule_parameters = [parameter for parameter in
                                module.module_parameters.get_parameters(ParameterCategory.GENERIC).values()
                                if parameter not in exclude_parameters]

        self.add_generic_parameters(submodule_parameters)

    def add_submodule_evaluation_set_parameters(self, module, exclude_parameters: Optional[List[
        Union[SingleParameter, NestedParameter, MultivalueParameter]]] = None):

        if exclude_parameters is None:
            exclude_parameters = []

        submodule_parameters = [parameter for parameter in
                                module.module_parameters.get_parameters(ParameterCategory.EVALUATION_SET).values()
                                if parameter not in exclude_parameters]

        self.add_evaluation_set_parameters(submodule_parameters)

    def add_submodule_layer_parameters(self, module, exclude_parameters: Optional[List[
            Union[SingleParameter, NestedParameter, MultivalueParameter]]] = None):

        if exclude_parameters is None:
            exclude_parameters = []

        layer_parameters_dict = module.module_parameters.get_layer_parameters_category_dict()

        for layer_type in layer_parameters_dict:
            submodule_parameters = [parameter for parameter in layer_parameters_dict[layer_type]
                                    if parameter not in exclude_parameters]
            self.add_layer_parameters(submodule_parameters, layer_type=layer_type)

    def get_parameters(self, category: Union[ParameterCategory, LayerType]) -> dict:
        if category in self._parameters:
            return self._parameters[category]
        else:
            return {}

    def get_layer_parameters(self) -> dict:
        layer_parameters = {}
        for category in self._parameters:
            if isinstance(category, LayerType):
                layer_parameters.update(self._parameters[category])
        return layer_parameters

    def get_layer_parameters_category_dict(self) -> dict:
        layer_parameters_category_dict = {}
        for category in self._parameters:
            if isinstance(category, LayerType):
                layer_parameters_category_dict.update({category: self._parameters[category].values()})
        return layer_parameters_category_dict

    def get_all_parameters_list(self) -> list:
        all_pars = []
        for category in self._parameters:
            all_pars += [self._parameters[category][key] for key in self._parameters[category]]
        return all_pars

    def get_categories(self) -> list:
        return list(self._parameters.keys())

    def has_evaluation_parameters(self) -> bool:
        return ParameterCategory.EVALUATION_SET in self.get_categories()