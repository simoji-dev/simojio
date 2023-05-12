from simojio.lib.enums.ParameterCategory import ParameterCategory

from simojio.lib.parameters.SingleParameter import SingleParameter
from simojio.lib.parameters.NestedParameter import NestedParameter
from simojio.lib.parameters.MultivalueParameter import MultivalueParameter

import copy


class ParameterValuesContainer:
    """Contains the current values of all parameters that have occurred while running this module configuration."""

    def __init__(self, category: ParameterCategory):

        self.category = category
        self.parameter_values = {}      # {name1: value, name2: value_list}

    def set_values(self, value_dict: dict, module):

        default_module_parameters = module.module_parameters.get_parameters(self.category)

        for par_name in value_dict:
            if par_name in default_module_parameters:
                default_parameter = copy.deepcopy(default_module_parameters[par_name])
                if isinstance(default_parameter, SingleParameter):
                    value, success = default_parameter.set_value(value_dict[par_name])
                    value_dict.update({par_name: value})
                elif isinstance(default_parameter, NestedParameter) or isinstance(default_parameter,
                                                                                      MultivalueParameter):
                    values, success = default_parameter.set_parameter_values(value_dict[par_name])
                    value_dict.update({par_name: values})

        self.parameter_values.update(value_dict)

    def get_values(self) -> dict:
        return self.parameter_values

