import os, sys
import importlib
from pathlib import Path
import simoji.lib.BasicFunctions as BasicFunctions

from simoji.lib.abstract_modules import *
from simoji.lib.enums.ParameterCategory import ParameterCategory
from typing import *


class ModuleLoader:

    def __init__(self):

        self.module_root_path = os.path.join("modules")     # in this path all modules are stored (incl. sub-dirs)
        self.abstract_modules_root_path = os.path.join("lib", "abstract_modules")
        self.module_path_dict = {}                          # {'module_name': module_path}

    def get_available_modules(self, print_errors=True) -> list:

        self.module_path_dict = {}

        sub_dirs = [dir_name for dir_name in os.listdir(self.module_root_path)
                    if os.path.isdir(os.path.join(self.module_root_path, dir_name))]

        for module_name in sub_dirs:

            if module_name + ".py" in os.listdir(os.path.join(self.module_root_path, module_name)):
                path = Path(os.path.join(self.module_root_path, module_name, module_name + ".py"))
                try:
                    sys.path.append(os.path.join(*list(path.parts)[:-1]))
                    module = importlib.import_module(module_name)
                    module = importlib.reload(module)
                    module_cls = getattr(module, module_name)

                    if any([issubclass(module_cls, Plotter)]):
                        self.module_path_dict.update({module_name: path})
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

    @staticmethod
    def load_module_class(module_name: str, package: Optional[str] = None):
        module = importlib.import_module(module_name, package)
        module = importlib.reload(module)

        module_cls = getattr(module, module_name)
        return module_cls

    def get_parameter_categories(self, module_name: str):
        module_cls = self.load_module_class(module_name)
        categories = []
        if len(module_cls.generic_parameters) > 0:
            categories.append(ParameterCategory.GENERIC)
        if len(module_cls.evaluation_set_parameters) > 0:
            categories.append(ParameterCategory.EVALUATION_SET)
        for layer_type in [layer.layer_type for layer in module_cls.available_layers]:
            categories.append(layer_type)
        return categories




