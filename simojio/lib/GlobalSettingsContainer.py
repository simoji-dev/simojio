from simojio.lib.VariablesValuesContainer import VariablesValuesContainer
from simojio.lib.ExpressionsValuesContainer import ExpressionsValuesContainer
from simojio.lib.ParameterContainer import ParameterContainer
from simojio.lib.OptimizationSettingsContainer import OptimizationSettingsContainer


class GlobalSettingsContainer:

    def __init__(self):

        self.module_path = None
        self.execution_mode = None
        self.use_global_optimization_settings = False

        self.global_variables = VariablesValuesContainer()
        self.global_expressions = ExpressionsValuesContainer()

        self.optimization_settings = OptimizationSettingsContainer(include_sample_related_settings=False)

    def set_variables_parameter_container(self, parameter_container: ParameterContainer):
        self.global_variables.set_values(parameter_container.get_all_parameters_content())

    def set_variables_values(self, values_dict: dict):
        self.global_variables.set_values(values_dict)

    def get_variables_values(self) -> dict:
        return self.global_variables.get_values()

    def set_expressions_parameter_container(self, parameter_container: ParameterContainer):
        self.global_expressions.set_values(parameter_container.get_all_parameters_content())

    def set_expressions_values(self, values_dict: dict):
        self.global_expressions.set_values(values_dict)

    def get_expressions_values(self) -> dict:
        return self.global_expressions.get_values()

    def set_optimization_settings_container(self, opt_container: OptimizationSettingsContainer):
        self.optimization_settings = opt_container

    def set_optimization_settings_values(self, values_dict: dict):
        self.optimization_settings.set_properties_from_dict(values_dict)

    def get_optimization_settings_values(self) -> dict:
        return self.optimization_settings.get_properties_as_dict()



