from simoji.lib.Sample import Sample
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.VariablesValuesContainer import VariablesValuesContainer
from simoji.lib.ExpressionsValuesContainer import ExpressionsValuesContainer
from simoji.lib.parameters.Variable import Variable
from simoji.lib.enums.ParameterCategory import ParameterCategory
from simoji.lib.parameters.FloatParameter import FloatParameter
from simoji.lib.ModuleInputContainer import ModuleInputContainer
from simoji.lib.BasicFunctions import check_expression, start_stop_step_to_list

from typing import *
import numpy as np


class VariationContainerDataset:
    """Variation container for a single dataset index."""

    def __init__(self, sample: Sample, global_settings: GlobalSettingsContainer, dataset_idx: int):

        self.fix_parameters = dict()            # {ParameterCategory.GENERIC: {'wavelength': [400, 800, 2]}}
        self.varied_parameters = dict()         # {ParameterCategory.GENERIC: {'amplitude': 'EXPR_0'}}
        self.layer_types_list = list()          # [LayerType.SEMI, ..]

        self.varied_variables = list()          # [Variable]    -> checked if actually used in sample
        self.fix_variables_dict = dict()        # {"VAR_2": 15}
        self.expressions_dict = dict()          # {'EXPR_0': '2*VAR_0 + VAR_2'}

        sample.current_dataset_index = dataset_idx
        self._evaluate_input(sample, global_settings.global_variables, global_settings.global_expressions)
        self.variation_grid = self._construct_variation_grid()      # List[List[float]]

    def _evaluate_input(self, sample: Sample, global_variables: VariablesValuesContainer,
                        global_expressions: ExpressionsValuesContainer):
        """
        # What we need:
        # varied_variable_names = ["VAR_0", "VAR_1", "G_VAR_0"]     -> check, if actually used in the sample
        # fix_variables_dict = {"VAR_2": 15}
        # varied_parameters = {ParameterCategory.GENERIC: {'amplitude': 'EXPR_0'}}
        # expressions_dict = {'EXPR_0': '2*VAR_0 + VAR_2'}
        :param sample:
        :param global_variables:
        :param global_expressions:
        :return:
        """

        # (1) read all variables and expressions
        all_variables = sample.variables.get_parameters() + global_variables.get_parameters()
        all_variables_dict = {var.name: var for var in all_variables}
        all_variables_values_dict = {var.name: var.get_current_value() for var in all_variables}

        self.expressions_dict.update(sample.expressions.get_values())
        self.expressions_dict.update(global_expressions.get_values())

        # (2) get sample parameters (parameters as objects)
        # all_parameters = {ParameterCategory.GENERIC: {'amplitude': FloatParameter, 'wavelength': [400, 800, 2]}}
        # -> Note: Non-FloatParameters (and FloatParameters set to float) are directly replaced by their current values
        all_parameters = sample.get_parameter_values_current_module()

        # (3) split in 2 dicts and check which variables are actually used:
        # fix_parameters = {ParameterCategory.GENERIC: {'wavelength': [400, 800, 2]}}
        #   -> replace all Non-FloatParameters and Not-varied FloatParameters by values
        #   -> e.g. 'amplitude': 'EXPR_0' and 'EXPR_0'='2*VAR_0' and 'VAR_0'=2 not varied -> 'amplitude': 4
        #
        # varied_parameters = {ParameterCategory.GENERIC: {'amplitude': 'EXPR_0'}

        for category in all_parameters:
            if category in [ParameterCategory.GENERIC, ParameterCategory.DATASET]:
                fix_parameters, varied_parameters = self._split_in_fix_and_varied(all_parameters[category],
                                                                                  all_variables_dict,
                                                                                  all_variables_values_dict)
                self.fix_parameters.update({category: fix_parameters})
                self.varied_parameters.update({category: varied_parameters})
            elif category is ParameterCategory.LAYER:
                layer_parameters_list = all_parameters[ParameterCategory.LAYER][0]
                self.layer_types_list = all_parameters[ParameterCategory.LAYER][1]

                fix_parameters_layers_list = []
                varied_parameters_layers_list = []
                for layer_parameters in layer_parameters_list:
                    fix_parameters, varied_parameters = self._split_in_fix_and_varied(layer_parameters,
                                                                                      all_variables_dict,
                                                                                      all_variables_values_dict)
                    fix_parameters_layers_list.append(fix_parameters)
                    varied_parameters_layers_list.append(varied_parameters)

                self.fix_parameters.update({ParameterCategory.LAYER: fix_parameters_layers_list})
                self.varied_parameters.update({ParameterCategory.LAYER: varied_parameters_layers_list})

    def _split_in_fix_and_varied(self, parameter_dict: dict, all_variables_dict: dict,
                                 all_variables_values_dict: dict) -> (dict, dict):
        """
        Replace variables that are not varied by their current values (fix_parameters)
        :param parameter_dict:
        :param all_variables_dict:
        :return: fix_parameters, varied_parameters
        """

        fix_parameters = {}
        varied_parameters = {}

        for par_name in parameter_dict:
            par_value = parameter_dict[par_name]
            if isinstance(par_value, FloatParameter):
                value_str = par_value.get_current_value()   # e.g. "VAR_0" or "G_EXPR_0"

                # directly given variable
                if value_str in all_variables_dict:
                    variable = all_variables_dict[value_str]
                    is_varied = variable.get_variation_flag()
                    if is_varied:
                        if value_str not in self.get_varied_variables_names():
                            self.varied_variables.append(variable)

                        varied_parameters.update({par_name: value_str})
                    else:
                        fix_parameters.update({par_name: variable.get_current_value()})
                        self.fix_variables_dict.update({variable.name: variable.get_current_value()})
                # expression
                elif value_str in self.expressions_dict:
                    success, eval_str, used_variables = check_expression(self.expressions_dict[value_str],
                                                                          all_variables_values_dict,
                                                                          return_used_parameters=True)
                    if success:
                        if any([all_variables_dict[var_name].get_variation_flag() for var_name in used_variables]):
                            # any variable in expression is varied -> put it to varied_parameters
                            varied_parameters.update({par_name: value_str})
                        else:
                            fix_parameters.update({par_name: eval_str})
                        for var_name in used_variables:
                            variable = all_variables_dict[var_name]
                            if not variable.get_variation_flag():
                                self.fix_variables_dict.update({var_name: variable.get_current_value()})
                    else:
                        raise ValueError("Could not evaluate '" + value_str + "' = " + self.expressions_dict[value_str])
                else:
                    raise ValueError("FloatParameter value not found in variables or expressions")
            else:
                fix_parameters.update({par_name: par_value})   # Non-FloatParameter already converted to value

        return fix_parameters, varied_parameters

    def get_varied_variables_names(self) -> List[str]:
        return [variable.name for variable in self.varied_variables]

    def get_varied_variables_values(self) -> List[float]:
        return [variable.get_current_value() for variable in self.varied_variables]

    def get_varied_variables_bounds(self) -> List[Tuple[float]]:
        return [tuple(variable.get_min_max_step()[:2]) for variable in self.varied_variables]

    def _construct_variation_grid(self):

        variable_arrays = []
        for variable in self.varied_variables:
            variable_arrays.append(start_stop_step_to_list(variable.get_min_max_step()))

        variation_grid = []
        if len(variable_arrays) > 0:
            variation_grid = np.stack(np.meshgrid(*variable_arrays), -1).reshape(-1, len(variable_arrays))

        return variation_grid

    def get_variation_grid(self) -> List[List[float]]:
        return self.variation_grid

    def get_varied_module_parameters(self, varied_variables_values: List[float]) -> dict:
        """
        varied_variables_values = [0.2, 1, 20]
        varied_variable_names = ["VAR_0", "VAR_1", "G_VAR_0"]
        -> Note: We need to know which variables are actually used in the sample

        fix_variables_dict = {"VAR_2": 15}

        varied_parameters = {ParameterCategory.GENERIC: {'amplitude': 'EXPR_0'}}

        expressions_dict = {'EXPR_0': '2*VAR_0 + VAR_2'}
        -> Note: expressions might contain fix variables (that's why we need to store them)

        varied_parameters_replaced = {ParameterCategory.GENERIC: {'amplitude': 15.4}}

        :param varied_variables_values: e.g. [0.2, 1, 20]
        :return:
        """

        varied_variables_dict = {self.get_varied_variables_names()[i]: varied_variables_values[i]
                                 for i in range(len(varied_variables_values))}

        all_variables_values_dict = {}
        all_variables_values_dict.update(self.fix_variables_dict)
        all_variables_values_dict.update(varied_variables_dict)

        varied_variables_replaced = {}

        for category in self.varied_parameters:
            if category in [ParameterCategory.GENERIC, ParameterCategory.DATASET]:
                category_dict = self._get_varied_variables_replaced_category(self.varied_parameters[category],
                                                                             all_variables_values_dict)
                varied_variables_replaced.update({category: category_dict})
            elif category is ParameterCategory.LAYER:
                variables_replaced_layer = []
                for layer_dict in self.varied_parameters[ParameterCategory.LAYER]:
                    layer_dict_replaced = self._get_varied_variables_replaced_category(layer_dict,
                                                                                       all_variables_values_dict)
                    variables_replaced_layer.append(layer_dict_replaced)
                varied_variables_replaced.update({ParameterCategory.LAYER: variables_replaced_layer})

        return varied_variables_replaced

    def _get_varied_variables_replaced_category(self, varied_parameters_category: dict,
                                                all_variables_values_dict: dict) -> dict:
        category_dict = {}
        for par_name in varied_parameters_category:
            value_str = varied_parameters_category[par_name]
            if value_str in self.expressions_dict:
                success, value, used_variables = check_expression(self.expressions_dict[value_str],
                                                                  all_variables_values_dict)
            else:
                value = all_variables_values_dict[value_str]
            category_dict.update({par_name: value})

        return category_dict

    def _fill_module_input_container(self, varied_parameters: dict, include_fix_parameters=True) -> ModuleInputContainer:

        module_input_container = ModuleInputContainer()

        if include_fix_parameters:
            module_input_container.generic_parameters.update(self.fix_parameters[ParameterCategory.GENERIC])
        module_input_container.generic_parameters.update(varied_parameters[ParameterCategory.GENERIC])

        if include_fix_parameters:
            module_input_container.dataset_parameters.update(self.fix_parameters[ParameterCategory.DATASET])
        module_input_container.dataset_parameters.update(varied_parameters[ParameterCategory.DATASET])

        module_input_container.layer_type_list = self.layer_types_list
        layers_parameters_list = []
        for i, fix_layer_parameters in enumerate(self.fix_parameters[ParameterCategory.LAYER]):
            all_layer_parameters = {}
            if include_fix_parameters:
                all_layer_parameters.update(fix_layer_parameters)
            all_layer_parameters.update(varied_parameters[ParameterCategory.LAYER][i])
            layers_parameters_list.append(all_layer_parameters)
        module_input_container.layer_parameters_list = layers_parameters_list

        return module_input_container

    def get_input_container_for_single(self) -> ModuleInputContainer:

        varied_variables = self.get_varied_module_parameters(self.get_varied_variables_values())
        return self._fill_module_input_container(varied_variables)

    def get_input_container_for_variation(self, variation_idx: int) -> ModuleInputContainer:

        varied_parameters = self.get_varied_module_parameters(self.variation_grid[variation_idx])
        return self._fill_module_input_container(varied_parameters)

    def get_input_container_for_optimization(self, variable_values: List[float]) -> ModuleInputContainer:
        varied_parameters = self.get_varied_module_parameters(variable_values)
        return self._fill_module_input_container(varied_parameters, include_fix_parameters=False)


