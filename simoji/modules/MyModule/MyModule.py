from simoji.lib.abstract_modules import Plotter
from simoji.lib.parameters import FloatParameter, StartStopStepParameter

import numpy as np
import matplotlib.pyplot as plt


class MyModule(Plotter):

    # Define simoji parameters
    a_parameter = FloatParameter(name="a", value=1., description="Parameter a")
    b_parameter = FloatParameter(name="b", value=1., description="Parameter b")
    c_parameter = FloatParameter(name="c", value=1., description="Parameter c")

    # Add defined parameters to the container. Sort into respective parameter type (generic, evaluation set, layer)
    generic_parameters = [a_parameter, b_parameter, c_parameter]

    def __init__(self):
        super(MyModule, self).__init__()

        self.a = 1.0
        self.b = 1.0
        self.c = 1.0

    def run(self):
        pass

