import os, sys
import importlib
from pathlib import Path
import simoji.lib.BasicFunctions as BasicFunctions

from simoji.lib.abstract_modules import *
from typing import *


class ModuleLoader:
    """Identifies valid simoji modules"""

    def __init__(self):

        self.module_root_path = os.path.join("modules")  # in this path all modules are stored (incl. sub-dirs)
        self.abstract_modules_root_path = os.path.join("lib", "abstract_modules")
        self.module_path_dict = {}  # {'module_name': module_path}
        self.module_is_simulator_dict = {}      # {'module_name': is_simulator}

    def get_available_modules(self, print_errors=True) -> list:

        self.module_path_dict = {}

        for path in Path(self.module_root_path).rglob('*.py'):
            module_name = (path.name).rstrip('.py')

            # check if module is valid
            if module_name != "__init__":
                try:

                    sys.path.append(os.path.join(*list(path.parts)[:-1]))
                    module = importlib.import_module(module_name)
                    module = importlib.reload(module)
                    module_cls = getattr(module, module_name)

                    if any([issubclass(module_cls, Reader), issubclass(module_cls, Simulator),
                            issubclass(module_cls, Fitter)]):
                        self.module_path_dict.update({module_name: path})
                        if any([issubclass(module_cls, Reader), issubclass(module_cls, Fitter)]):
                            self.module_is_simulator_dict.update({module_name: False})
                        else:
                            self.module_is_simulator_dict.update({module_name: True})
                    else:
                        if print_errors:
                            print("INFO: File '" + module_name +
                                  ".py' not imported as module (no subclass of DataSetReader, Simulator, or Fitter)")
                except Exception as e:
                    if print_errors:
                        print("WARNING: Error during import of module '" + str(path) + "':")
                        print(e)

        return list(self.module_path_dict.keys())

    def get_module_path_as_list(self, module_name: str) -> list:
        module_path = self.module_path_dict[module_name]
        module_path_as_list = BasicFunctions.convert_path_str_to_list(str(module_path))
        return module_path_as_list

    def load_module(self, module_name: str, package: Optional[str] = None):
        module_cls = self.load_module_class(module_name, package)
        module_obj = module_cls()

        return module_obj

    def load_module_class(self, module_name: str, package: Optional[str] = None):
        module = importlib.import_module(module_name, package)
        module = importlib.reload(module)

        module_cls = getattr(module, module_name)
        return module_cls

    def is_simulator(self, module_name: str):
        if module_name in self.module_is_simulator_dict:
            return self.module_is_simulator_dict[module_name]
        else:
            raise ValueError("Module name '" + module_name + "' not in is_simulator_dict.")

    def get_parameter_categories(self, module_name: str):
        module_cls = self.load_module_class(module_name)
        categories = module_cls.module_parameters.get_categories()
        return categories




