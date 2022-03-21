from simoji.lib.ModuleParameterContainer import ModuleParameterContainer
from simoji.lib.PlotContainer import PlotContainer
import importlib
import abc
from typing import *


class AbstractModule(metaclass=abc.ABCMeta):
    """Abstract class that defines the basic methods and members of any simoji module"""

    module_path = None  # relative path to the module given as list
    module_parameters = ModuleParameterContainer()
    queue = None    # multiprocessing.Queue

    _simoji_save_dir = None

    def __init__(self):
        pass

    def configure_generic_parameters(self, generic_parameters: dict):
        pass

    def to_str(self):
        return self.__class__.__name__

    def get_optimization_dict(self) -> Optional[dict]:
        return {}

    def get_results_dict(self) -> dict:
        return self.get_optimization_dict()

    def plot_fig(self, fig, title: str, save=True):
        plot_container = PlotContainer(fig=fig, title=title, save=save)
        self.queue.put(plot_container)

    def get_save_dir(self) -> str:
        return self._simoji_save_dir

    def load_module(self, module_name: str, package: Optional[str] = None):
        module = importlib.import_module(module_name, package)
        module = importlib.reload(module)

        module_cls = getattr(module, module_name)
        module_obj = module_cls()

        return module_obj

