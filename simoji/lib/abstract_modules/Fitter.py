import abc
from . import *


class Fitter(AbstractModule, metaclass=abc.ABCMeta):
    """Determines the difference between data set and calculated values."""

    def __init__(self):
        super().__init__()

    @classmethod
    def __subclasshook__(cls, subclass):
        """
        This guarantees that issubclass() only returns True if all mandatory methods are implemented.
        :param subclass:
        :return:
        """
        return (hasattr(subclass, 'configure_experimental_parameters') and
                callable(subclass.configure_experimental_parameters) and
                hasattr(subclass, 'run_reader') and
                callable(subclass.run_reader) and
                hasattr(subclass, 'run_simulator') and
                callable(subclass.run_simulator) and
                hasattr(subclass, 'get_reader') and
                callable(subclass.get_reader) and
                hasattr(subclass, 'set_reader') and
                callable(subclass.set_reader) and
                hasattr(subclass, 'calc_optimization_value') and
                callable(subclass.calc_optimization_value) or
                NotImplemented)

    @abc.abstractmethod
    def configure_experimental_parameters(self, experimental_parameters: dict):
        pass

    def configure_layers(self, layer_parameters_list: list, layer_type_list: list):
        pass

    @abc.abstractmethod
    def run_reader(self):
        pass

    @abc.abstractmethod
    def run_simulator(self):
        pass

    @abc.abstractmethod
    def get_reader(self) -> Reader:
        pass

    # @abc.abstractmethod
    # def set_reader(self, reader: Reader):   # Don't need this??
    #     pass

    @abc.abstractmethod
    def get_simulator(self) -> Simulator:
        pass

    @abc.abstractmethod
    def calc_optimization_value(self):
        pass
