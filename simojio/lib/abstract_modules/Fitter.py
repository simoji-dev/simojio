import abc
from .AbstractModule import AbstractModule


class Fitter(AbstractModule, metaclass=abc.ABCMeta):
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
        return (hasattr(subclass, 'get_fit_name_and_value') and
                callable(subclass.get_fit_name_and_value) or
                NotImplemented)

    def get_results_dict(self):
        fit_name, fit_value = self.get_fit_name_and_value()
        return {fit_name: fit_value}

    @abc.abstractmethod
    def get_fit_name_and_value(self) -> (str, float):
        pass
