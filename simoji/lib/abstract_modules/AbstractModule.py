import abc
import matplotlib.pyplot as plt
from typing import Dict, List

from simoji.lib.parameters import Parameter, FloatParameter, NestedParameter, SingleParameter
from simoji.lib.PlotContainer import PlotContainer
from simoji.lib.CallbackContainer import CallbackContainer
from simoji.lib.Layer import Layer


class AbstractModule(metaclass=abc.ABCMeta):
    """Abstract class that defines the basic methods and members of any simoji module"""

    module_path = None                       # relative path to the module given as list
    queue = None                             # multiprocessing.Queue for communication of results
    simoji_save_dir = None                   # save directory of the specific module instance

    generic_parameters = list()              # list of defined generic parameters
    evaluation_set_parameters = list()       # list of defined evaluation set parameters
    available_layers = list()                # list of available layers (List[Layer])
    layer_list = list()                      # sequence of layers used for calculation

    def __init__(self):
        pass

    @classmethod
    def __subclasshook__(cls, subclass):
        """
        This guarantees that issubclass() only returns True if all mandatory methods are implemented.
        :param subclass:
        :return:
        """
        return (hasattr(subclass, 'run') and
                callable(subclass.run) or
                NotImplemented)

    @abc.abstractmethod
    def run(self):
        pass

    def has_evaluation_parameters(self) -> bool:
        return len(self.evaluation_set_parameters) > 0

    def has_layers(self) -> bool:
        return len(self.available_layers) > 0

    def to_str(self) -> str:
        return self.__class__.__name__

    def plot_fig(self, fig: plt.Figure, title: str, save=True):
        plot_container = PlotContainer(fig=fig, title=title, save=save)
        self.queue.put(plot_container)

    def get_save_dir(self) -> str:
        return self.simoji_save_dir

    def callback(self, title: str, message: str):
        self.queue.put(CallbackContainer(title, message))

    def get_generic_parameter(self, parameter: Parameter):
        return self._get_parameter(parameter, self.generic_parameters)

    def get_generic_parameter_value(self, parameter: Parameter):
        return self._get_parameter_value(parameter, self.generic_parameters)

    def is_generic_parameter_updated(self, parameter: Parameter) -> bool:
        return self._is_parameter_updated(parameter, self.generic_parameters)

    def get_evaluation_parameter(self, parameter: Parameter):
        return self._get_parameter(parameter, self.evaluation_set_parameters)

    def get_evaluation_parameter_value(self, parameter: Parameter):
        return self._get_parameter_value(parameter, self.evaluation_set_parameters)

    def is_evaluation_parameter_updated(self, parameter: Parameter) -> bool:
        return self._is_parameter_updated(parameter, self.evaluation_set_parameters)

    def get_layer_parameter(self, parameter: Parameter, layer: Layer) -> Parameter:
        return self._get_parameter(parameter, layer.parameters)

    def get_layer_parameter_value(self, parameter: Parameter, layer: Layer):
        return self._get_parameter_value(parameter, layer.parameters)

    def is_layer_parameter_updated(self, parameter: Parameter, layer: Layer) -> bool:
        return self._is_parameter_updated(parameter, layer.parameters)

    @staticmethod
    def _get_parameter(initial_parameter: Parameter, parameter_list: List[Parameter]):
        for parameter in parameter_list:
            if parameter.name == initial_parameter.name:
                return parameter
        raise ValueError("Parameter '" + initial_parameter.name + "' not found in parameter_list.")

    def _get_parameter_value(self, initial_parameter: Parameter, parameter_list: List[Parameter]):
        parameter = self._get_parameter(initial_parameter, parameter_list)
        if isinstance(parameter, FloatParameter):
            return parameter.get_current_value()
        elif isinstance(parameter, NestedParameter):
            return parameter.get_parameter_values_list()
        elif isinstance(parameter, SingleParameter):
            return parameter.value
        else:
            raise ValueError("Unknown parameter type" + str(parameter))

    def _is_parameter_updated(self, initial_parameter: Parameter, parameter_list: List[Parameter]) -> bool:
        parameter = self._get_parameter(initial_parameter, parameter_list)
        return parameter.is_updated
