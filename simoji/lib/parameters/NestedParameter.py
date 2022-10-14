from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.parameters.Parameter import Parameter


class NestedParameter(Parameter):
    """Parameter consisting of multiple sub-parameters that are all of type Parameter. They are saved as list of tuples
    such as [(name, value), ..]"""

    def __init__(self, name: str, parameters: list, description: str):
        """

        :param name:
        :param parameters: list of Parameter instances
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

    def set_parameter_values(self, value_list: list) -> (list, bool):
        """
        Try to set each parameter to the given values. If it isn't possible, set the parameter to its default value and
        return success=False.
        :param value_list:
        :return: (list of values that have been set, success)
        """

        success = True
        for idx, value in enumerate(value_list):
            set_value, successful_set = self.parameters[idx].set_value(value)
            if not successful_set:
                success = False

        current_values = [parameter.value for parameter in self.parameters]
        return current_values, success

    def get_parameter_values_list(self) -> list:
        return [parameter.value for parameter in self.parameters]








