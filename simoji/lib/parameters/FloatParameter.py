from simoji.lib.parameters.NestedParameter import NestedParameter
from simoji.lib.parameters.FixFloatParameter import FixFloatParameter
from simoji.lib.parameters.MultiStringParameter import MultiStringParameter
from simoji.lib.parameters.BoolParameter import BoolParameter
from simoji.lib.enums.ParameterCategory import ParameterCategory
import numpy as np

from typing import Optional


class FloatParameter(NestedParameter):
    """Float value that can also be set to free parameter. If the latter option is not wanted use FixFloatParameter"""

    def __init__(self, name: str, value: float, description: str, bounds=None):

        if bounds is None:
            bounds = [-np.inf, np.inf]

        self.name = name
        self.value = value
        self.description = description
        self.bounds = bounds

        self.float_par = FixFloatParameter(name="float value", value=value, description="Float value", bounds=bounds)
        self.free_par = MultiStringParameter(name="free parameter", value="", description="Free parameter", bounds=[""])
        self.is_set_to_free_parameter = BoolParameter(name="is set to free parameter", value=False,
                                                      description="check when enabling free parameter drop down")

        self.parameters = [self.float_par, self.free_par, self.is_set_to_free_parameter]

        super().__init__(name, self.parameters, description)

    def set_parameter_values(self, value_list: list) -> (list, bool):
        """
        Try to set each parameter to the given values. If it isn't possible, set the parameter to its default value and
        return success=False.
        :param value_list:
        :return: (list of values that have been set, success)
        """

        if not value_list[1] in self.parameters[1].bounds:
            self.parameters[1].bounds.append(value_list[1])

        success = True
        for idx, value in enumerate(value_list):
            set_value, successful_set = self.parameters[idx].set_value(value)
            if not successful_set:
                success = False

        self.value = self.parameters[0].value
        self.float_par.value = self.value
        self.free_par.value = self.parameters[1].value
        self.is_set_to_free_parameter.value = self.parameters[2].value

        current_values = [parameter.value for parameter in self.parameters]
        return current_values, success

    def get_current_value(self):
        if self.is_set_to_free_parameter.value:
            return self.free_par.value
        else:
            return self.float_par.value