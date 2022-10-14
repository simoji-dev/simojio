from simoji.lib.parameters.Parameter import Parameter


class SingleParameter(Parameter):
    """
    Abstract class for single parameters. Only save the value, everything else is loaded from the module anyway.
    """

    def __init__(self, name: str, value, description: str, bounds=None):

        super().__init__()

        self.name = name
        self.value = value
        self.description = description
        self.bounds = bounds

    def set_value(self, value):
        """
        Set value if possible. Otherwise keep the previous value.
        :param value:
        :return: (set value, success)
        """

        valid_value = False
        if self._check_value(value):
            self.value = value
            valid_value = True

        return self.value, valid_value

    def _check_value(self, value) -> bool:
        """Check if value is of right type and within bounds."""
        return True
