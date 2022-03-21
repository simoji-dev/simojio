from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.enums.ParameterCategory import ParameterCategory
from simoji.lib.parameters.Parameter import Parameter
import copy
from typing import Optional


class MultivalueParameter(Parameter):
    """
    Parameter consisting of multiple sub-parameters of the same type. Their values are saved as list. Parameters can
    be added and removed.
    """

    def __init__(self, name: str, parameters: list, description: str, bounds: list):
        """

        :param name:
        :param parameters: list of Parameter instances (all of the same type)
        :param description:
        """

        super().__init__()

        self.name = name
        self.parameters = parameters
        self.description = description

        # check if all parameters are valid
        for parameter in self.parameters:
            if not isinstance(parameter, SingleParameter):
                raise ValueError("Parameter '" + str(parameter) + "is not a valid parameter!")

        self._check_all_multivalue_parameters()

    def set_parameter_values(self, value_list: list) -> (list, bool):
        """
        Try to set each parameter to the given values. If it isn't possible, set the parameter to its default value and
        return success=False.
        :param value_list:
        :return: (list of values that have been set, success)
        """

        while len(self.parameters) < len(value_list):
            self.add_multivalue_parameter(self.parameters[0].value)

        success = True
        for idx, value in enumerate(value_list):
            set_value, successful_set = self.parameters[idx].set_value(value)
            if not successful_set:
                success = False

        current_values = [parameter.value for parameter in self.parameters]
        return current_values, success

    def get_parameter_values_list(self) -> list:
        return [parameter.value for parameter in self.parameters]

    def add_multivalue_parameter(self, value):
        new_parameter = copy.deepcopy(self.parameters[0])
        new_parameter.value = value
        self._check_single_multivalue_parameter(new_parameter)
        self.parameters.append(new_parameter)

    def remove_multivalue_parameter(self, idx: int) -> bool:
        try:
            del self.parameters[idx]
            return True
        except Exception as e:
            print(e)
            return False

    def _check_all_multivalue_parameters(self):
        for parameter in self.parameters:
            self._check_single_multivalue_parameter(parameter)

    def _check_single_multivalue_parameter(self, parameter):
        if type(parameter) is not type(self.parameters[0]):
            raise ValueError("Warning: multivalue parameters are not of same type")