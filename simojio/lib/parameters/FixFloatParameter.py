from simojio.lib.parameters.SingleParameter import SingleParameter
import numpy as np


class FixFloatParameter(SingleParameter):

    def __init__(self, name: str, value: float, description: str, bounds = None):

        super().__init__(name, value, description, bounds)

        if bounds is None:
            bounds = [-np.inf, np.inf]

        self.name = name
        self.value = value
        self.description = description
        self.bounds = bounds

    def set_value(self, value):
        """Value might be either a float or a free parameter name"""

        try:
            value = float(value)    # might be stored as int or something
        except:
            pass

        success = self._check_value(value)

        if success:
            self.value = value

        return self.value, True

    def _check_value(self, value: float) -> bool:
        """Check if value is of right type and within bounds."""

        if not isinstance(value, float):
            return False

        if (value < self.bounds[0]) or (value > self.bounds[1]):
            return False

        return True

