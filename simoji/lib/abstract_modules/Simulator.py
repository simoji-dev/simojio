import abc
from .AbstractModule import AbstractModule


class Simulator(AbstractModule, metaclass=abc.ABCMeta):
    """Simulates/Calculates from given parameters and layer stack"""

    def __init__(self):
        super().__init__()

    @classmethod
    def __subclasshook__(cls, subclass):
        """
        This guarantees that issubclass() only returns True if all mandatory methods are implemented.
        :param subclass:
        :return:
        """
        return (hasattr(subclass, 'run_simulator') and
                callable(subclass.run_simulator) or
                NotImplemented)

    def configure_layers(self, layer_parameters_list: list, layer_type_list: list):
        pass

    @abc.abstractmethod
    def run_simulator(self):
        pass
