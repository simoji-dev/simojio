from simojio.lib.ParameterContainer import ParameterContainer
from simojio.lib.VariablesValuesContainer import VariablesValuesContainer
from simojio.lib.ExpressionsValuesContainer import ExpressionsValuesContainer
from simojio.lib.OptimizationSettingsContainer import OptimizationSettingsContainer
from simojio.lib.enums.ParameterCategory import ParameterCategory
from simojio.lib.enums.LayerType import LayerType
from simojio.lib.parameters import *
from simojio.lib.BasicFunctions import check_expression
from simojio.lib.abstract_modules import AbstractModule

from typing import Union, List


class Sample:
    """
    Contains the values of the generic and evaluation set parameters and the parameters of the layer stack of every
    module that has been used during run.

    Separate between set_values and set_module

    Generic parameters:
    0) Input from setting {"test_float": [3.0, "VAR_1", true]}
    1a) No module set -> store it in 'unknown_pars' dict
    2a) Set module
        -> add all parameters of module to 'known_pars' dict
         -> try to update with values from 'unknown_pars'
    1b) Module is set -> if par in 'known_pars': try to update values, else: add to 'unknown_pars'
    3) save: merge 'unknown_pars' and dict of values created from 'known_pars'

    Variables:
    0) Copy default variable
    1) Input from setting {"variables_and_expressions": {"VAR_0": [11, 1, 100, 1, true]} -> set values
    """

    def __init__(self, name: str):

        self.name = name
        self.enable = True

        self.current_evaluation_set_index = 0
        self.current_variation_index = 0

        self.generic_parameters = ParameterContainer(ParameterCategory.GENERIC)
        self.evaluation_set_list = []      # list of parameter containers
        self.variables = VariablesValuesContainer()
        self.expressions = ExpressionsValuesContainer()
        self.optimization_settings = OptimizationSettingsContainer(include_sample_related_settings=True)
        self.layer_list = []
        self.layer_list_current_module = []

    def set_generic_parameters(self, parameters_dict: dict):
        self.generic_parameters.set_parameters(parameters_dict)

    def set_generic_parameter_container(self, parameter_container: ParameterContainer):
        self.generic_parameters = parameter_container

    def set_evaluation_sets_values(self, evaluation_set_list: list):
        """Translate list of values to list of objects"""

        self.evaluation_set_list = []
        for evaluation_set_values_dict in evaluation_set_list:
            evaluation_set_obj = ParameterContainer(ParameterCategory.EVALUATION_SET)
            evaluation_set_obj.set_parameters(evaluation_set_values_dict)
            self.evaluation_set_list.append(evaluation_set_obj)

    def set_evaluation_set_parameter_container_list(self, parameter_container_list: List[ParameterContainer]):
        self.evaluation_set_list = parameter_container_list

    def set_variables_values(self, value_dict: dict):
        self.variables.set_values(value_dict)

    def set_variables_parameter_container(self, parameter_container: ParameterContainer):
        self.variables.set_values(parameter_container.get_all_parameters_content())

    def set_expressions_values(self, value_dict: dict):
        self.expressions.set_values(value_dict)

    def set_expressions_parameter_container(self, parameter_container: ParameterContainer):
        self.expressions.set_values(parameter_container.get_all_parameters_content())

    def set_optimization_settings_container(self, opt_container: OptimizationSettingsContainer):
        self.optimization_settings = opt_container

    def set_optimization_settings_values(self, values_dict: dict):
        self.optimization_settings.set_properties_from_dict(values_dict)

    def get_optimization_settings_values(self) -> dict:
        return self.optimization_settings.get_properties_as_dict()

    def set_layer_list(self, layer_list: list):
        self.layer_list = layer_list

    def set_module(self, module: AbstractModule):
        self.generic_parameters.set_module(module)
        self.layer_list_current_module = []
        available_layer_types = [layer.layer_type for layer in module.available_layers]

        for idx in range(len(self.layer_list)):
            self.layer_list[idx].set_module(module)

            if self.layer_list[idx].layer_type in available_layer_types:
                self.layer_list_current_module.append(self.layer_list[idx])

    def get_parameter_values_current_module(self):

        parameter_values_dict = {}

        generic_parameters = self.generic_parameters.get_module_values(replace_free_parameters=False)
        parameter_values_dict.update({ParameterCategory.GENERIC: generic_parameters})

        if len(self.evaluation_set_list) > 0:
            evaluation_set_parameters = self.evaluation_set_list[self.current_evaluation_set_index].get_module_values(
                replace_free_parameters=False)
        else:
            evaluation_set_parameters = {}
        parameter_values_dict.update({ParameterCategory.EVALUATION_SET: evaluation_set_parameters})

        layer_list = self.get_layer_list_current_module()
        layer_types = [layer.layer_type for layer in layer_list]
        layer_parameters = [layer.get_module_values(replace_free_parameters=False) for layer in layer_list]
        parameter_values_dict.update({ParameterCategory.LAYER: [layer_parameters, layer_types]})

        return parameter_values_dict

    def get_parameter_objects_current_module(self) -> dict:
        parameter_objects_dict = {}
        generic_parameters_list = self.generic_parameters.get_module_parameters()
        if len(generic_parameters_list) > 0:
            parameter_objects_dict.update({
                ParameterCategory.GENERIC: generic_parameters_list
            })
        layer_list = self.get_layer_list_current_module()
        if len(layer_list) > 0:
            parameter_objects_dict.update({
                ParameterCategory.LAYER: layer_list
            })
        if len(self.evaluation_set_list) > 0:
            parameter_objects_dict.update({
                ParameterCategory.EVALUATION_SET: self.evaluation_set_list[
                    self.current_evaluation_set_index].get_module_parameters()
            })
        return parameter_objects_dict

    def get_parameters_values(self, category: Union[ParameterCategory, LayerType],
                              global_free_parameters_values_dict=None,
                              sample_variables_dict=None,
                              replace_free_parameters=True,
                              ignore_expression_errors=False) -> Union[dict, list]:

        if global_free_parameters_values_dict is None:
            global_free_parameters_values_dict = {}
        if sample_variables_dict is None:
            sample_variables_dict = {}

        all_variables = {}
        all_variables.update(self.variables.parameters)
        all_variables.update(self.expressions.parameters)
        all_variables_values_dict = self._get_current_values_of_variables_and_expressions(all_variables,
                                                                                          ignore_expression_errors)

        all_variables_values_dict.update(global_free_parameters_values_dict)
        all_variables_values_dict.update(sample_variables_dict)

        if category is ParameterCategory.GENERIC:
            if replace_free_parameters:
                return self.generic_parameters.get_module_values(all_variables_values_dict)
            else:
                return self.generic_parameters.get_all_parameters_content()
        elif category is ParameterCategory.EVALUATION_SET:
            evaluation_set_values_list = []
            for evaluation_set in self.evaluation_set_list:
                if replace_free_parameters:
                    evaluation_set_values_list.append(evaluation_set.get_module_values(all_variables_values_dict))
                else:
                    evaluation_set_values_list.append(evaluation_set.get_all_parameters_content())
            return evaluation_set_values_list
        elif category is ParameterCategory.VARIABLE:
            return self.variables.get_values()
        elif category is ParameterCategory.EXPRESSION:
            return self.expressions.get_values()
        elif category is ParameterCategory.LAYER:
            if replace_free_parameters:
                return self.get_layers_with_replaced_variables(all_variables_values_dict)
            else:
                return self.get_layer_list()

    def get_evaluation_sets(self) -> List[ParameterContainer]:
        return self.evaluation_set_list

    def get_evaluation_sets_with_replaced_variables(self, all_variables: dict) -> list:

        for evaluation_set_obj in self.evaluation_set_list:
            evaluation_set_obj.get_module_values(all_variables)
        return self.evaluation_set_list

    def get_layer_list(self) -> list:
        return self.layer_list

    def get_layer_list_current_module(self) -> list:
        return self.layer_list_current_module

    def get_layers_with_replaced_variables(self, all_variables: dict) -> list:

        module_layer_list = []
        for layer in self.layer_list:
            layer.set_module_values_with_replaced_free_parameters(all_variables)
            values_dict = layer.get_module_values(all_variables)
            if len(values_dict) > 0:
                module_layer_list.append(layer)

        return module_layer_list

    def get_used_free_parameters(self, evaluation_set_idx: int) -> (list, bool, bool, bool):
        """
        Iterate through all parameters (generic, evaluation set, layers). For each parameter, check if it is a FloatParameter
        and if yes, if it is set to the free parameter (variable or expression). If so, store the free parameter name
        and also the parameter name together with the free parameter name.
        """
        used_free_parameters = []   # list of free parameters that are use in the sample ["VAR_0", "EXPR_1"]
        varied_in_generic = []      # list of generic parameters set to a free parameter [("angle": "VAR_0")]
        varied_in_evaluation_set = []      # list of evaluation set parameters set to a free parameter [("boxcar": "VAR_0")]
        varied_in_layers = []   # list of list of layer parameters set to a free parameter [[("width": "VAR_0")], ..]

        used_free_parameters_generic, varied_in_generic = self.generic_parameters.get_used_free_parameters()
        used_free_parameters += used_free_parameters_generic

        for layer in self.layer_list:
            layer_free_parameters, varied_in_layer = layer.get_used_free_parameters()
            varied_in_layers.append(varied_in_layer)
            for parameter_name in layer_free_parameters:
                if parameter_name not in used_free_parameters:
                    used_free_parameters.append(parameter_name)

        try:
            evaluation_set_free_parameters, varied_in_evaluation_set = self.evaluation_set_list[evaluation_set_idx].get_used_free_parameters()
            for parameter_name in evaluation_set_free_parameters:
                if parameter_name not in used_free_parameters:
                    used_free_parameters.append(parameter_name)
        except:
            pass

        return used_free_parameters, varied_in_generic, varied_in_evaluation_set, varied_in_layers

    def _get_current_values_of_variables_and_expressions(self, variables_and_expressions_dict: dict,
                                                         ignore_expression_errors=False) -> dict:

        variables_dict = {}
        expressions_list = []
        values_dict = {}
        for par_name in variables_and_expressions_dict:
            par_obj = variables_and_expressions_dict[par_name]
            if isinstance(par_obj, Variable):
                variables_dict.update({par_name: par_obj.get_current_value()})
            elif isinstance(par_obj, Expression):
                expressions_list.append(par_obj)
        values_dict.update(variables_dict)

        for expression_obj in expressions_list:
            success, text_eval, used_parameters = check_expression(expression_obj.value, variables_dict)
            if (not ignore_expression_errors) and (not success):
                raise ValueError("Expression '" + str(expression_obj.value) + "' cannot be evaluated.")
            else:
                values_dict.update({expression_obj.name: text_eval})

        return values_dict








