from simojio.lib.parameters.NestedParameter import NestedParameter
from simojio.lib.parameters.FixFloatParameter import FixFloatParameter
from simojio.lib.parameters.BoolParameter import BoolParameter

import numpy as np


class Variable(NestedParameter):
    """Parameter that acts as a variable for single float values."""

    prefix = "VAR_"

    def __init__(self, name: str, value: float, min = -np.inf, max = np.inf, step = 1.,
                 description="Free parameter that acts as a variable for single float values"):

        value_par = FixFloatParameter(name="value", value=value, description="Current value")
        min_par = FixFloatParameter(name="min", value=min, description="Minimum value")
        max_par = FixFloatParameter(name="max", value=max, description="Maximum value")
        step_par = FixFloatParameter(name="step", value=step, description="Step width")
        variation_bool_par = BoolParameter(name="vary", value=True,
                                           description="If checked, vary parameter ('variation' + 'optimization' mode)")

        self.parameters = [value_par, min_par, max_par, step_par, variation_bool_par]

        super().__init__(name=name, parameters=self.parameters,
                         description=description)

    def set_current_value(self, value):
        self.parameters[0].set_value(value)

    def get_current_value(self):
        return self.parameters[0].value

    def get_min_max_step(self) -> list:
        return [self.parameters[1].value, self.parameters[2].value, self.parameters[3].value]

    def get_variation_flag(self) -> bool:
        return self.parameters[4].value
