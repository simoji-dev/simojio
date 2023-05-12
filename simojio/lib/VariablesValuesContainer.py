from simojio.lib.parameters.Variable import Variable
import copy


class VariablesValuesContainer:

    def __init__(self):

        self.parameters = {}
        self.default_variable = Variable(name="default variable", value=0.)

    def set_values(self, value_dict: dict):

        for par_name in value_dict:
            try:
                parameter = copy.deepcopy(self.default_variable)
                parameter.name = par_name
                values, success = parameter.set_parameter_values(value_dict[par_name])
                value_dict.update({par_name: parameter})
            except:
                pass

        self.parameters.update(value_dict)

        # delete parameters that are not in value_dict
        del_pars = []
        for par_name in self.parameters:
            if par_name not in value_dict:
                del_pars.append(par_name)

        for par_name in del_pars:
            del self.parameters[par_name]

    def set_current_values(self, current_values_dict: dict):
        for par_name in current_values_dict:
            if par_name in self.parameters:
                self.parameters[par_name].set_current_value(current_values_dict[par_name])

    def get_values(self) -> dict:
        return {par_name: self.parameters[par_name].get_parameter_values_list() for par_name in self.parameters}

    def get_parameters(self) -> list:
        return [self.parameters[name] for name in self.parameters]
