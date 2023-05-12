import abc
from .AbstractModule import AbstractModule


class Calculator(AbstractModule, metaclass=abc.ABCMeta):
    """Abstract calculator module."""

    def __init__(self):
        super().__init__()

    @classmethod
    def __subclasshook__(cls, subclass):
        """
        This guarantees that issubclass() only returns True if all mandatory methods are implemented.
        :param subclass:
        :return:
        """
        return (hasattr(subclass, 'get_results_dict') and
                callable(subclass.get_results_dict) or
                NotImplemented)

    @abc.abstractmethod
    def get_results_dict(self) -> dict:
        return {}
