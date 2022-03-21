from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.enums.ParameterCategory import ParameterCategory
from typing import Optional


class AnyStringParameter(SingleParameter):

    def __init__(self, name: str, value: str, description: str, bounds = None):

        super().__init__(name, value, description, bounds)

    def set_value(self, value):
        """Value is a string"""

        success = self._check_value(value)

        if success:
            self.value = value

        return self.value, success

    def _check_value(self, value: str) -> bool:
        """Check if value is of right type and within bounds."""

        if not isinstance(value, str):
            return False

        return True

    def get_value(self) -> str:
        return self.value