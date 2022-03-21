from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.enums.ParameterCategory import ParameterCategory
from typing import Optional


class MultiStringParameter(SingleParameter):
    """Choose one string contained in bounds."""

    def __init__(self, name: str, value: str, description: str, bounds: list):

        super().__init__(name, value, description)

        if value not in bounds:
            bounds.append(value)

        self.name = name
        self.value = value
        self.description = description
        self.bounds = bounds

    def _check_value(self, value: str) -> bool:
        """Check if value is of right type and within bounds."""

        if not isinstance(value, str):
            return False

        if value not in self.bounds:
            return False

        return True

