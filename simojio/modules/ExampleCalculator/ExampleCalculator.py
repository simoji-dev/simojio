import time
import os

from simojio.lib.abstract_modules import Calculator
from simojio.lib.parameters import FloatParameter, StartStopStepParameter, FileFromPathParameter
from simojio.lib.enums.LayerType import LayerType
from simojio.lib.Layer import Layer

import numpy as np
import matplotlib.pyplot as plt


class ExampleCalculator(Calculator):

    # Define simojio parameters
    x_parameter = StartStopStepParameter(name="x", start=0., stop=10., step=0.1, description="x")

    amplitude_parameter = FloatParameter(name="amplitude", value=1., description="Amplitude of Gaussian")
    position_parameter = FloatParameter(name="position", value=0., description="Position of Gaussian")
    width_parameter = FloatParameter(name="width", value=1., description="Width of Gaussian")

    # Add defined parameters to the container. Sort into respective parameter type (generic, evaluation set, layer)
    generic_parameters = [x_parameter, amplitude_parameter, position_parameter, width_parameter]

    material_par = FileFromPathParameter(name="material", path=os.path.join("modules", "shared_resources",
                                                                            "optical_constants"),
                                         extension_list=[".fmf"], description="Material data file")
    thickness_par = FloatParameter(name="thickness", value=50., bounds=(0., np.inf), description="layer thickness")

    available_layers = [Layer(LayerType.COHERENT, parameters=[material_par, thickness_par])]

    def __init__(self):
        super(ExampleCalculator, self).__init__()

        self.x = np.arange(*self.x_parameter.get_parameter_values_list())

        self.a = self.amplitude_parameter.value
        self.b = self.position_parameter.value
        self.c = self.width_parameter.value

        self.y = None

        self.data = None

    def update_generic_parameters(self):
        self.x = np.arange(*self.get_generic_parameter_value(self.x_parameter))
        self.a = self.get_generic_parameter_value(self.amplitude_parameter)
        self.b = self.get_generic_parameter_value(self.position_parameter)
        self.c = self.get_generic_parameter_value(self.width_parameter)

        # demonstration of how to check if a parameter was updated for the current module run
        position_is_updated = self.position_parameter.is_updated
        print(position_is_updated)

        # todo: In the first iteration, parameter.is_updated should be true
        if position_is_updated or (self.data is None):
            self.long_running_data_loading()

    def long_running_data_loading(self):
        print("----")
        print("start data loading")
        time.sleep(5)
        self.data = 1
        print("end data loading")

    def run(self):
        print("RUN")
        self.update_generic_parameters()

        thickness_parameters = [self.get_layer_parameter(self.thickness_par, layer) for layer in self.layer_list]


        self.y = self.gaussian(self.x, self.a, self.b, self.c)
        self.plot()

    @staticmethod
    def gaussian(x: np.array, a: float, b: float, c: float) -> np.array:
        return a * np.exp(-(x - b) ** 2 / (2 * c ** 2))

    def plot(self):
        fig, ax = plt.subplots()
        ax.plot(self.x, self.y, '.-', label="gaussian")

        ax.set_xlabel("position")
        ax.set_ylabel("amplitude")
        ax.legend()

        self.plot_fig(fig, title="gaussian_function")

    def get_results_dict(self) -> dict:
        results_dict = {
            self.amplitude_parameter.name: self.a,
            self.position_parameter.name: self.b,
            self.width_parameter.name: self.c
        }

        return results_dict
