import abc
from .AbstractModule import AbstractModule


class Reader(AbstractModule, metaclass=abc.ABCMeta):
    """Reads and processes (experimental) data sets."""

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
                callable(subclass.run_reader) or
                NotImplemented)

    @abc.abstractmethod
    def configure_experimental_parameters(self, experimental_parameters: dict):
        pass

    @abc.abstractmethod
    def run_reader(self):
        pass
