import json
import os
import copy

from simoji.lib.Sample import Sample
from simoji.lib.CompleteLayer import CompleteLayer
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.enums.ExecutionMode import ExecutionMode
from simoji.lib.enums.LayerType import LayerType
import simoji.lib.BasicFunctions as BasicFunctions
from simoji.lib.enums.ParameterCategory import ParameterCategory


class SettingManager:
    """Reads and writes simoji settings. Contains the definition of the keys to be used in the setting."""

    def __init__(self):

        self.simoji_version = json.load(open("product-info.json", 'r'))["version"]

        self._default_sample = Sample('sample name')

        # -- setting key definitions --

        # global
        self.global_settings_key = "global_settings"

        self.module_path_key = "module_path"
        self.execution_mode_key = "execution_mode"
        self.enable_global_optimization_settings_key = "enable_global_optimization_settings"
        self.coupled_optimization_key = "enable_coupled_optimization"
        self.global_variables_key = "global_variables"
        self.global_expressions_key = "global_expressions"

        self.optimization_settings_key = "optimization_settings"
        self.maximize_key = "maximize"
        self.name_of_value_to_be_optimized_key = "name_of_value_to_be_optimized"
        self.solver_key = "solver"

        # samples
        self.samples_key = "samples"

        self.sample_name_key = "name"
        self.sample_enable_key = "enable"
        self.generic_parameters_key = "generic_parameters"
        self.evaluation_set_parameters_key = "evaluation_set_parameters"
        self.variables_key = "variables"
        self.expressions_key = "expressions"

        self.layers_key = "layers"
        self.layer_name_key = "name"
        self.layer_type_key = "type"
        self.layer_enable_key = "enable"
        self.layer_color_key = "color"
        self.layer_parameters_key = "parameters"

    def read_setting(self, path: str) -> (GlobalSettingsContainer, list, bool):

        success = True
        module = None

        try:
            setting_dict = json.load(open(path, 'r'))
        except:
            setting_dict = {}

        # -- read global settings --
        global_settings = GlobalSettingsContainer()

        if self.global_settings_key in setting_dict:
            global_dict = setting_dict[self.global_settings_key]

            if self.module_path_key in global_dict:
                try:
                    global_settings.module_path = global_dict[self.module_path_key]
                    module_cls = BasicFunctions.get_module_class_from_path_given_as_list(global_settings.module_path)
                    module = module_cls()
                except:
                    pass

            if self.execution_mode_key in global_dict:
                try:
                    global_settings.execution_mode = ExecutionMode(global_dict[self.execution_mode_key])
                except:
                    global_settings.execution_mode = ExecutionMode.SINGLE

            if self.enable_global_optimization_settings_key in global_dict:
                val = global_dict[self.enable_global_optimization_settings_key]
                if isinstance(val, bool):
                    global_settings.use_global_optimization_settings = val

            if self.global_variables_key in global_dict:
                global_settings.set_variables_values(global_dict[self.global_variables_key])

            if self.global_expressions_key in global_dict:
                global_settings.set_expressions_values(global_dict[self.global_expressions_key])

            if self.optimization_settings_key in global_dict:
                global_settings.set_optimization_settings_values(global_dict[self.optimization_settings_key])

        # -- read samples --
        sample_list = []
        if self.samples_key in setting_dict:
            for sample_dict in setting_dict[self.samples_key]:

                new_sample = copy.deepcopy(self._default_sample)

                if self.sample_name_key in sample_dict:
                    new_sample.name = sample_dict[self.sample_name_key]
                if self.sample_enable_key in sample_dict:
                    new_sample.enable = sample_dict[self.sample_enable_key]

                if self.generic_parameters_key in sample_dict:
                    new_sample.set_generic_parameters(sample_dict[self.generic_parameters_key])
                if self.evaluation_set_parameters_key in sample_dict:
                    new_sample.set_evaluation_sets_values(sample_dict[self.evaluation_set_parameters_key])
                if self.variables_key in sample_dict:
                    new_sample.set_variables_values(sample_dict[self.variables_key])
                if self.expressions_key in sample_dict:
                    new_sample.set_expressions_values(sample_dict[self.expressions_key])
                if self.optimization_settings_key in sample_dict:
                    new_sample.set_optimization_settings_values(sample_dict[self.optimization_settings_key])

                # read layers
                if self.layers_key in sample_dict:
                    layer_list = []
                    for idx in range(len(sample_dict[self.layers_key])):
                        layer_obj = self._get_layer_obj_from_values_dict(sample_dict[self.layers_key][idx])
                        layer_list.append(layer_obj)
                    new_sample.set_layer_list(layer_list)

                if module is not None:
                    new_sample.set_module(module)

                sample_list.append(new_sample)

        return global_settings, sample_list, success

    def write_setting(self, path: str, global_settings: GlobalSettingsContainer, sample_list: list):

        global_dict = {
            "simoji_version": self.simoji_version,
            self.module_path_key: global_settings.module_path,
            self.execution_mode_key: global_settings.execution_mode,
            self.enable_global_optimization_settings_key: global_settings.use_global_optimization_settings,
            self.global_variables_key: global_settings.get_variables_values(),
            self.global_expressions_key: global_settings.get_expressions_values(),
            self.optimization_settings_key: global_settings.get_optimization_settings_values()
        }

        sample_values_list = []
        for sample in sample_list:
            sample_values_list.append(self._sample_obj_to_values_dict(sample))

        setting_dict = {
            self.global_settings_key: global_dict,
            self.samples_key: sample_values_list
        }

        os.makedirs(path[:path.rindex(os.path.sep)], exist_ok=True)
        json_file = open(path, 'w', encoding='utf-8')
        json.dump(setting_dict, json_file, sort_keys=True, indent=4)
        json_file.close()

    def _sample_obj_to_values_dict(self, sample: Sample):

        samples_dict = {
            self.sample_name_key: sample.name,
            self.sample_enable_key: sample.enable,

            self.generic_parameters_key: sample.get_parameters_values(ParameterCategory.GENERIC,
                                                                      global_free_parameters_values_dict=None,
                                                                      replace_free_parameters=False,
                                                                      ignore_expression_errors=True),
            self.evaluation_set_parameters_key: sample.get_parameters_values(ParameterCategory.EVALUATION_SET,
                                                                             global_free_parameters_values_dict=None,
                                                                             replace_free_parameters=False,
                                                                             ignore_expression_errors=True),
            self.variables_key: sample.get_parameters_values(ParameterCategory.VARIABLE,
                                                             global_free_parameters_values_dict=None,
                                                             replace_free_parameters=False,
                                                             ignore_expression_errors=True),
            self.expressions_key: sample.get_parameters_values(ParameterCategory.EXPRESSION,
                                                               global_free_parameters_values_dict=None,
                                                               replace_free_parameters=False,
                                                               ignore_expression_errors=True),
            self.optimization_settings_key: sample.get_optimization_settings_values(),
            self.layers_key: [self._get_layer_values_dict_from_layer_obj(layer) for layer in sample.get_layer_list()]
        }

        return samples_dict

    def _get_layer_obj_from_values_dict(self, values_dict: dict) -> CompleteLayer:

        layer_name = values_dict[self.layer_name_key]
        layer_type = LayerType(values_dict[self.layer_type_key])
        layer_enable = values_dict[self.layer_enable_key]
        layer_color = tuple(values_dict[self.layer_color_key])

        layer = CompleteLayer(name=layer_name, layer_type=layer_type, enabled=layer_enable, color=layer_color)
        layer.set_parameters(values_dict[self.layer_parameters_key])

        return layer

    def _get_layer_values_dict_from_layer_obj(self, layer: CompleteLayer) -> dict:

        layer_dict = {
            self.layer_name_key: layer.name,
            self.layer_type_key: layer.layer_type.value,
            self.layer_enable_key: layer.enabled,
            self.layer_color_key: list(layer.color),
            self.layer_parameters_key: layer.get_all_parameters_content()
        }

        return layer_dict
