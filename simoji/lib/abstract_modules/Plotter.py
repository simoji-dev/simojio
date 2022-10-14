import abc
from .AbstractModule import AbstractModule


class Plotter(AbstractModule, metaclass=abc.ABCMeta):
    """Abstract plotter module."""

    def __init__(self):
        super().__init__()

